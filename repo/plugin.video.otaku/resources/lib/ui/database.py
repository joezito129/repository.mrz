import ast
import hashlib
import pickle
import re
import time
import xbmcvfs

from resources.lib.ui import control
from sqlite3 import OperationalError, dbapi2


cache_table = 'cache'


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
                except:
                    return ast.literal_eval(cache_result['value'])

    fresh_result = repr(function(*args, **kwargs))

    if fresh_result is None or fresh_result == 'None':
        # If the cache is old, but we didn't get fresh result, return the old cache
        if cache_result:
            return cache_result
        return None

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
    control.cacheFile_lock.acquire()
    cursor = _get_connection_cursor(control.cacheFile)
    try:
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
        results = cursor.fetchone()
        cursor.close()
        return results
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.cacheFile_lock)


def cache_insert(key, value):
    control.cacheFile_lock.acquire()
    cursor = _get_connection_cursor(control.cacheFile)
    now = int(time.time())
    try:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))"
            % cache_table
        )
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_%s ON %s (key)" % (cache_table, cache_table))
        cursor.execute("REPLACE INTO %s (key, value, date) VALUES (?, ?, ?)" % cache_table, (key, value, now))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.cacheFile_lock)


def cache_clear():
    control.cacheFile_lock.acquire()
    cursor = _get_connection_cursor(control.cacheFile)
    try:
        for t in [cache_table, 'rel_list', 'rel_lib']:
            cursor.execute("DROP TABLE IF EXISTS %s" % t)
            cursor.execute("VACUUM")
            cursor.connection.commit()
        control.showDialog.notification('{}: {}'.format(control.ADDON_NAME, control.lang(30200)), control.lang(30201), time=5000, sound=False)
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.cacheFile_lock)


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff


def makeFile(path):
    xbmcvfs.mkdir(path)


def _get_connection_cursor(filepath):
    conn = _get_connection(filepath)
    return conn.cursor()


def _get_connection(filepath):
    makeFile(control.dataPath)
    conn = dbapi2.connect(filepath)
    conn.row_factory = _dict_factory
    return conn


def _get_db_connection():
    makeFile(control.dataPath)
    conn = dbapi2.connect(control.anilistSyncDB, timeout=60.0)
    conn.row_factory = _dict_factory
    return conn


def _get_cursor():
    conn = _get_db_connection()
    conn.execute("PRAGMA FOREIGN_KEYS = 1")
    cursor = conn.cursor()
    return cursor


def update_show(anilist_id, mal_id, kodi_meta, last_updated='', anime_schedule_route=''):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    if isinstance(kodi_meta, dict):
        kodi_meta = pickle.dumps(kodi_meta)
    try:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute(
            "REPLACE INTO shows ("
            "anilist_id, mal_id, kodi_meta, last_updated, anime_schedule_route)"
            "VALUES "
            "(?, ?, ?, ?, ?)",
            (anilist_id, mal_id, kodi_meta, last_updated, anime_schedule_route))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


def update_show_meta(anilist_id, meta_ids, art):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    if isinstance(meta_ids, dict):
        meta_ids = pickle.dumps(meta_ids)
    if isinstance(art, dict):
        art = pickle.dumps(art)
    try:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute(
            "REPLACE INTO shows_meta ("
            "anilist_id, meta_ids, art)"
            "VALUES "
            "(?, ?, ?)",
            (anilist_id, meta_ids, art))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


def add_mapping_id(anilist_id, column, value):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    cursor.execute('UPDATE shows SET %s=? WHERE anilist_id=?' % column, (value, anilist_id))
    cursor.connection.commit()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)


def update_kodi_meta(anilist_id, kodi_meta):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    kodi_meta = pickle.dumps(kodi_meta)
    cursor.execute('UPDATE shows SET kodi_meta=? WHERE anilist_id=?', (kodi_meta, anilist_id))
    cursor.connection.commit()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)


def update_season(show_id, season):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    try:
        cursor.execute(
            "REPLACE INTO seasons ("
            "anilist_id, season, kodi_meta)"
            "VALUES "
            "(?, ?, ?)",
            (int(show_id), str(season), ''))
        cursor.connection.commit()
        cursor.close()

    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


def update_show_data(anilist_id, data={}, last_updated=''):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    data = pickle.dumps(data)
    try:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute(
            "REPLACE INTO show_data ("
            "anilist_id, data, last_updated)"
            "VALUES "
            "(?, ?, ?)",
            (anilist_id, data, last_updated))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


def update_episode(show_id, season=0, number=0, update_time='', kodi_meta={}, filler=''):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    kodi_meta = pickle.dumps(kodi_meta)
    try:
        cursor.execute(
            "REPLACE INTO episodes ("
            "anilist_id, season, kodi_meta, last_updated, number, filler)"
            "VALUES "
            "(?, ?, ?, ?, ?, ?)",
            (show_id, season, kodi_meta, update_time, number, filler))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


def _get_show_list():
    control.anilistSyncDB_lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    cursor.execute('SELECT * FROM shows')
    shows = cursor.fetchall()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return shows


def get_season_list(show_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    cursor.execute('SELECT* FROM seasons WHERE anilist_id = ?', (show_id,))
    seasons = cursor.fetchone()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return seasons


def get_show_data(anilist_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM show_data WHERE anilist_id IN (%s)' % anilist_id
    cursor.execute(db_query)
    show_data = cursor.fetchone()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return show_data


def get_episode_list(show_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    cursor.execute('SELECT* FROM episodes WHERE anilist_id = ?', (show_id,))
    episodes = cursor.fetchall()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return episodes


def get_show(anilist_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM shows WHERE anilist_id IN (%s)' % anilist_id
    cursor.execute(db_query)
    shows = cursor.fetchone()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return shows


def get_show_meta(anilist_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM shows_meta WHERE anilist_id IN (%s)' % anilist_id
    cursor.execute(db_query)
    shows = cursor.fetchone()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return shows


def get_show_mal(mal_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_connection_cursor(control.anilistSyncDB)
    db_query = 'SELECT * FROM shows WHERE mal_id IN (%s)' % mal_id
    cursor.execute(db_query)
    shows = cursor.fetchone()
    cursor.close()
    control.try_release_lock(control.anilistSyncDB_lock)
    return shows


def remove_season(anilist_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    try:
        cursor.execute("DELETE FROM seasons WHERE anilist_id = ?", (anilist_id,))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


def remove_episodes(anilist_id):
    control.anilistSyncDB_lock.acquire()
    cursor = _get_cursor()
    try:
        cursor.execute("DELETE FROM episodes WHERE anilist_id = ?", (anilist_id,))
        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.anilistSyncDB_lock)


# def get_download(url_hash):
#     control.downloadsDB_lock.acquire()
#     cursor = _get_connection_cursor(control.downloadsDB)
#     cursor.execute('CREATE TABLE IF NOT EXISTS downloads (url_hash BLOB, data BLOB, UNIQUE(url_hash))')
#     cursor.execute('SELECT* FROM downloads WHERE url_hash = ?', url_hash,)
#     download = cursor.fetchall()
#     cursor.close()
#     control.try_release_lock(control.anilistSyncDB_lock)
#     return download
#
#
# def set_download(url_hash, data):
#     control.downloadsDB_lock.acquire()
#     cursor = _get_connection_cursor(control.downloadsDB)
#     cursor.execute('CREATE TABLE IF NOT EXISTS downloads (url_hash BLOB, data BLOB, UNIQUE(url_hash))')
#     cursor.execute("REPLACE INTO downloads (url_hash, data) VALUES (?, ?)", (url_hash, data))
#     cursor.connection.commit()
#     cursor.close()
#     control.try_release_lock(control.downloadsDB_lock)
#
#
# def remove_download(url_hash):
#     control.downloadsDB_lock.acquire()
#     cursor = _get_connection_cursor(control.downloadsDB)
#     cursor.execute('CREATE TABLE IF NOT EXISTS downloads (url_hash BLOB, data BLOB, UNIQUE(url_hash))')
#     cursor.execute("DELETE FROM downloads WHERE url_hash = ?", url_hash,)
#     cursor.connection.commit()
#     cursor.close()
#     control.try_release_lock(control.downloadsDB_lock)


def getSearchHistory(media_type='show'):
    control.searchHistoryDB_lock.acquire()
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
        control.try_release_lock(control.searchHistoryDB_lock)


def addSearchHistory(search_string, media_type):
    control.searchHistoryDB_lock.acquire()
    cursor = _get_connection_cursor(control.searchHistoryDB)
    try:
        cursor.execute('CREATE TABLE IF NOT EXISTS show (value TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS movie (value TEXT)')
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON movie (value)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON show (value)")

        cursor.execute(
            "REPLACE INTO %s Values (?)"
            % media_type, (search_string,)
        )

        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
        return []
    finally:
        control.try_release_lock(control.searchHistoryDB_lock)


def create_torrent_cache(cursor):
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS %s ("
        "anilist_id INTEGER NOT NULL, "
        "sources BLOB, "
        "zfill INTEGER,"
        "UNIQUE(anilist_id))"
        % cache_table
    )
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_%s ON %s (anilist_id)" % (cache_table, cache_table))


def addTorrentList(anilist_id, torrent_list, zfill_int):
    control.torrentScrapeCacheFile_lock.acquire()
    cursor = _get_connection_cursor(control.torrentScrapeCacheFile)
    try:
        create_torrent_cache(cursor)

        if isinstance(torrent_list, list):
            torrent_list = pickle.dumps(torrent_list)
        cursor.execute("REPLACE INTO %s (anilist_id, sources, zfill) "
                       "VALUES (?, ?, ?)" % cache_table,
                       (anilist_id, torrent_list, int(zfill_int)))

        cursor.connection.commit()
        cursor.close()
    except OperationalError:
        cursor.close()
        return []
    finally:
        control.try_release_lock(control.torrentScrapeCacheFile_lock)


def torrent_cache_clear():
    control.torrentScrapeCacheFile_lock.acquire()
    cursor = _get_connection_cursor(control.torrentScrapeCacheFile)
    try:
        for t in [cache_table, 'rel_list', 'rel_lib']:
            cursor.execute("DROP TABLE IF EXISTS %s" % t)
            cursor.execute("VACUUM")
            cursor.connection.commit()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.torrentScrapeCacheFile_lock)

    control.showDialog.notification('{}: {}'.format(control.ADDON_NAME, control.lang(30200)), control.lang(30202), time=5000, sound=False)


def clearSearchHistory():
    control.searchHistoryDB_lock.acquire()
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
        control.try_release_lock(control.searchHistoryDB_lock)


def remove_search(table, value):
    control.searchHistoryDB_lock.acquire()
    cursor = _get_connection_cursor(control.searchHistoryDB)
    try:
        cursor.execute(f'DELETE FROM {table} WHERE value = ?', (value,))
        cursor.connection.commit()
        cursor.close()
        control.refresh()
    except OperationalError:
        cursor.close()
    finally:
        control.try_release_lock(control.searchHistoryDB_lock)


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
