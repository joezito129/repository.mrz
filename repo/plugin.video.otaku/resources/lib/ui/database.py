import ast
import hashlib
import pickle
import re
import time
import xbmcvfs
import threading

from resources.lib.ui import control
from sqlite3 import OperationalError, dbapi2


cache_table = 'cache'
lock = threading.Lock()


def get_(function, duration, *args, **kwargs):
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result
    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
    :param args: Optional arguments for the provided function
    """
    sources = False
    reload = False
    if 'animepahe_reload' in kwargs:
        reload = kwargs['otaku_reload']
        kwargs.pop('otaku_reload')

    if 'animepahe_sources' in kwargs:
        sources = True
        kwargs.pop('otaku_sources')

    key = _hash_function(function, args, kwargs)
    cache_result = cache_get(key)
    if not reload:
        if cache_result:
            if _is_cache_valid(cache_result['date'], duration):
                try:
                    return_data = ast.literal_eval(cache_result['value'])
                    return return_data
                except Exception:
                    return ast.literal_eval(cache_result['value'])

    fresh_result = repr(function(*args, **kwargs))

    if fresh_result is None or fresh_result == 'None':
        # If the cache is old, but we didn't get fresh result, return the old cache
        return cache_result if cache_result else None

    data = ast.literal_eval(fresh_result)

    # Because I'm lazy, I've added this crap code so sources won't cache if there are no results
    if not sources:
        cache_insert(key, fresh_result)
    elif len(data[1]) > 0:
        cache_insert(key, fresh_result)
    else:
        return None
    return data


def _hash_function(function_instance, *args):
    return _get_function_name(function_instance) + generate_md5(args)


def _get_function_name(function_instance):
    return re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))


def generate_md5(*args):
    md5_hash = hashlib.md5()
    [md5_hash.update(str(arg).encode('utf-8')) for arg in args]
    return str(md5_hash.hexdigest())


def cache_get(key):
    lock.acquire()
    cursor = _get_connection_cursor(control.cacheFile)
    try:
        cursor.execute(f'SELECT * FROM {cache_table} WHERE key=?', (key,))
        results = cursor.fetchone()
        cursor.close()
        return results
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def cache_insert(key, value):
    lock.acquire()
    cursor = _get_connection_cursor(control.cacheFile)
    now = int(time.time())
    try:
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {cache_table} (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
        cursor.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_{cache_table} ON {cache_table} (key)')
        cursor.execute(f'REPLACE INTO {cache_table} (key, value, date) VALUES (?, ?, ?)', (key, value, now))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def cache_clear():
    lock.acquire()
    cursor = _get_connection_cursor(control.cacheFile)
    try:
        for t in [cache_table, 'rel_list', 'rel_lib']:
            cursor.execute("DROP TABLE IF EXISTS %s" % t)
            cursor.execute("VACUUM")
            cursor.connection.commit()
        control.notify(f'{control.ADDON_NAME}: {control.lang(30200)}', control.lang(30201), time=5000, sound=False)
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff


def _get_connection_cursor(filepath):
    conn = _get_connection(filepath)
    return conn.cursor()


def _get_connection(filepath):
    xbmcvfs.mkdir(control.dataPath)
    conn = dbapi2.connect(filepath)
    conn.row_factory = _dict_factory
    return conn


def _get_db_connection():
    xbmcvfs.mkdir(control.dataPath)
    conn = dbapi2.connect(control.anilistSyncDB, timeout=60.0)
    conn.row_factory = _dict_factory
    return conn


def _get_cursor():
    conn = _get_db_connection()
    conn.execute("PRAGMA FOREIGN_KEYS=1")
    cursor = conn.cursor()
    return cursor


def update_show(anilist_id, mal_id, kodi_meta, anime_schedule_route=''):
    lock.acquire()
    cursor = _get_cursor()
    if isinstance(kodi_meta, dict):
        kodi_meta = pickle.dumps(kodi_meta)
    try:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute('REPLACE INTO shows (anilist_id, mal_id, kodi_meta, anime_schedule_route) VALUES (?, ?, ?, ?)', (anilist_id, mal_id, kodi_meta, anime_schedule_route))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def update_show_meta(anilist_id, meta_ids, art):
    lock.acquire()
    cursor = _get_cursor()
    if isinstance(meta_ids, dict):
        meta_ids = pickle.dumps(meta_ids)
    if isinstance(art, dict):
        art = pickle.dumps(art)
    try:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute("REPLACE INTO shows_meta (anilist_id, meta_ids, art) VALUES (?, ?, ?)", (anilist_id, meta_ids, art))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def add_mapping_id_meta(anilist_id, anime_id, id_type):
    show_meta = get_show_meta(anilist_id)
    meta_ids = pickle.loads(show_meta.get('meta_ids'))
    meta_ids[id_type] = anime_id
    meta_ids = pickle.dumps(meta_ids)
    lock.acquire()
    cursor = _get_cursor()
    cursor.execute('UPDATE shows_meta SET meta_ids=? WHERE anilist_id=?', (meta_ids, anilist_id))
    cursor.connection.commit()
    cursor.close()
    control.try_release_lock(lock)


def add_mapping_id(anilist_id, column, value):
    lock.acquire()
    cursor = _get_cursor()
    cursor.execute('UPDATE shows SET %s=? WHERE anilist_id=?' % column, (value, anilist_id))
    cursor.connection.commit()
    cursor.close()
    control.try_release_lock(lock)


def update_kodi_meta(anilist_id, kodi_meta):
    lock.acquire()
    cursor = _get_cursor()
    kodi_meta = pickle.dumps(kodi_meta)
    cursor.execute('UPDATE shows SET kodi_meta=? WHERE anilist_id=?', (kodi_meta, anilist_id))
    cursor.connection.commit()
    cursor.close()
    control.try_release_lock(lock)


def update_show_data(anilist_id, data, last_updated=''):
    lock.acquire()
    cursor = _get_cursor()
    data = pickle.dumps(data)
    try:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute("REPLACE INTO show_data (anilist_id, data, last_updated) VALUES (?, ?, ?)", (anilist_id, data, last_updated))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def update_episode(show_id, season, number, update_time, kodi_meta, filler=''):
    lock.acquire()
    cursor = _get_cursor()
    try:
        cursor.execute('REPLACE INTO episodes (anilist_id, season, kodi_meta, last_updated, number, filler) VALUES (?, ?, ?, ?, ?, ?)', (show_id, season, kodi_meta, update_time, number, filler))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def get_show_data(anilist_id):
    lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM show_data WHERE anilist_id IN (%s)' % anilist_id
    cursor.execute(db_query)
    show_data = cursor.fetchone()
    cursor.close()
    control.try_release_lock(lock)
    return show_data


def get_episode_list(show_id):
    lock.acquire()
    cursor = _get_cursor()
    cursor.execute('SELECT* FROM episodes WHERE anilist_id=?', (show_id,))
    episodes = cursor.fetchall()
    cursor.close()
    control.try_release_lock(lock)
    return episodes


def get_episode(show_id):
    lock.acquire()
    cursor = _get_cursor()
    cursor.execute('SELECT* FROM episodes WHERE anilist_id=?', (show_id,))
    episode = cursor.fetchone()
    cursor.close()
    control.try_release_lock(lock)
    return episode


def get_show(anilist_id):
    lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM shows WHERE anilist_id IN (%s)' % anilist_id
    cursor.execute(db_query)
    shows = cursor.fetchone()
    cursor.close()
    control.try_release_lock(lock)
    return shows


def get_show_meta(anilist_id):
    lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM shows_meta WHERE anilist_id IN (%s)' % anilist_id
    cursor.execute(db_query)
    shows = cursor.fetchone()
    cursor.close()
    control.try_release_lock(lock)
    return shows


def get_show_mal(mal_id):
    lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM shows WHERE mal_id IN (%s)' % mal_id
    cursor.execute(db_query)
    shows = cursor.fetchone()
    cursor.close()
    control.try_release_lock(lock)
    return shows


def remove_episodes(anilist_id):
    lock.acquire()
    cursor = _get_cursor()
    try:
        cursor.execute("DELETE FROM episodes WHERE anilist_id=?", (anilist_id,))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def remove_show_data(anilist_id):
    lock.acquire()
    cursor = _get_cursor()
    try:
        cursor.execute("DELETE FROM show_data WHERE anilist_id=?", (anilist_id,))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def get_mappings(anime_id, send_id):
    lock.acquire()
    cursor = _get_connection_cursor(control.mappingDB)
    cursor.execute(f'SELECT * FROM anime WHERE {send_id}=?', (anime_id,))
    mappings = cursor.fetchall()
    cursor.close()
    control.try_release_lock(lock)
    return mappings[0] if mappings else {}


def getSearchHistory(media_type='show'):
    lock.acquire()
    cursor = _get_connection_cursor(control.searchHistoryDB)
    try:
        cursor.execute('CREATE TABLE IF NOT EXISTS show (value TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS movie (value TEXT)')
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON movie (value)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON show (value)")
        cursor.execute("SELECT * FROM %s" % media_type)

        history = cursor.fetchall()
        cursor.close()
        history.reverse()
        history = history[:50]
        filter_ = []
        for i in history:
            if i['value'] not in filter_:
                filter_.append(i['value'])
        return filter_
    except OperationalError:
        cursor.close()
        return []
    finally:
        control.try_release_lock(lock)


def addSearchHistory(search_string, media_type):
    lock.acquire()
    cursor = _get_connection_cursor(control.searchHistoryDB)
    try:
        cursor.execute('CREATE TABLE IF NOT EXISTS show (value TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS movie (value TEXT)')
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON movie (value)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON show (value)")
        cursor.execute("REPLACE INTO %s Values (?)" % media_type, (search_string,))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
        return []
    finally:
        control.try_release_lock(lock)


def clearSearchHistory():
    lock.acquire()
    confirmation = control.yesno_dialog(control.ADDON_NAME, "Clear search history?")
    if not confirmation:
        return
    cursor = _get_connection_cursor(control.searchHistoryDB)
    try:
        cursor.execute("DROP TABLE IF EXISTS movie")
        cursor.execute("DROP TABLE IF EXISTS show")
        cursor.execute("VACCUM")
        cursor.connection.commit()
        cursor.close()
        control.refresh()
        control.notify(control.ADDON_NAME, "Search History has been cleared", time=5000)
    except OperationalError:
        cursor.close()
        return []
    finally:
        control.try_release_lock(lock)


def remove_search(table, value):
    lock.acquire()
    cursor = _get_connection_cursor(control.searchHistoryDB)
    try:
        cursor.execute(f'DELETE FROM {table} WHERE value=?', (value,))
        cursor.connection.commit()
        cursor.close()
        control.refresh()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(lock)


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
