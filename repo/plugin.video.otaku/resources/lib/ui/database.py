import ast
import hashlib
import pickle
import re
import time
import threading
import xbmcvfs

from sqlite3 import OperationalError, dbapi2
from resources.lib.ui import control


def get_(function, duration, *args, **kwargs):
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result

    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
    :param args: Optional arguments for the provided function
    :param kwargs: Optional keyword arguments for the provided function
    """
    key = hash_function(function, args, kwargs)
    if 'key' in kwargs:
        key += kwargs.pop('key')
    cache_result = cache_get(key)
    if cache_result and is_cache_valid(cache_result['date'], duration):
        try:
            return_data = ast.literal_eval(cache_result['value'])
        except:
            import traceback
            control.log('database.get_error', 'fatal')
            control.log(traceback.format_exc(), 'error')
            return_data = None
        return return_data

    fresh_result = repr(function(*args, **kwargs))
    cache_insert(key, fresh_result)
    if not fresh_result:
        return cache_result if cache_result else fresh_result
    data = ast.literal_eval(fresh_result)
    return data


def hash_function(function_instance, *args) -> str:
    function_name = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))
    return function_name + generate_md5(args)


def generate_md5(*args) -> str:
    md5_hash = hashlib.md5()
    [md5_hash.update(str(arg).encode()) for arg in args]
    return str(md5_hash.hexdigest())


def cache_get(key):
    with SQL(control.cacheFile) as cursor:
        cursor.execute('SELECT * FROM cache WHERE key=?', (key,))
        results = cursor.fetchone()
        return results


def cache_insert(key: str, value: str) -> None:
    now = int(time.time())
    with SQL(control.cacheFile) as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_cache ON cache (key)')
        cursor.execute('REPLACE INTO cache (key, value, date) VALUES (?, ?, ?)', (key, value, now))
        cursor.connection.commit()


def cache_clear() -> None:
    with SQL(control.cacheFile) as cursor:
        cursor.execute("DROP TABLE IF EXISTS cache")
        cursor.execute("VACUUM")
        cursor.connection.commit()
        cursor.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
        control.notify(f'{control.ADDON_NAME}: {control.lang(30030)}', control.lang(30031), time=5000, sound=False)


def is_cache_valid(cached_time: int, cache_timeout: int) -> bool:
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff


def update_show(mal_id: int, kodi_meta, anime_schedule_route: str = '') -> None:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute('REPLACE INTO shows (mal_id, kodi_meta, anime_schedule_route) VALUES (?, ?, ?)', (mal_id, kodi_meta, anime_schedule_route))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def update_show_meta(mal_id: int, meta_ids: dict, art: dict) -> None:
    meta_ids = pickle.dumps(meta_ids)
    art = pickle.dumps(art)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute("REPLACE INTO shows_meta (mal_id, meta_ids, art) VALUES (?, ?, ?)", (mal_id, meta_ids, art))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def add_mapping_id(mal_id: int, column: str, value: str):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('UPDATE shows SET %s=? WHERE mal_id=?' % column, (value, mal_id))
        cursor.connection.commit()


def update_kodi_meta(mal_id, kodi_meta: dict):
    kodi_meta = pickle.dumps(kodi_meta)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('UPDATE shows SET kodi_meta=? WHERE mal_id=?', (kodi_meta, mal_id))
        cursor.connection.commit()


def update_show_data(mal_id: int, data: dict, last_updated: str = ''):
    data = pickle.dumps(data)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute('REPLACE INTO show_data (mal_id, data, last_updated) VALUES (?, ?, ?)', (mal_id, data, last_updated))
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.connection.commit()


def create_episode(mal_id: int, number: int, update_time: str, season: int, kodi_meta, filler: str, anidb_ep_id) -> None:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('REPLACE INTO episodes (mal_id, number, last_updated, season, kodi_meta, filler, anidb_ep_id) VALUES (?, ?, ?, ?, ?, ?, ?)', (mal_id, number, update_time, season, kodi_meta, filler, anidb_ep_id))
        cursor.connection.commit()

def update_episode_column(mal_id: int, episode: int, column: str, value):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('UPDATE episodes SET %s=? WHERE mal_id=? AND number=?' % column, (value, mal_id, episode))
        cursor.connection.commit()

def get_show_data(mal_id: int):
    with SQL(control.malSyncDB) as cursor:
        db_query = 'SELECT * FROM show_data WHERE mal_id IN (%s)' % mal_id
        cursor.execute(db_query)
        show_data = cursor.fetchone()
        return show_data


def get_episode_list(mal_id: int):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT* FROM episodes WHERE mal_id=?', (mal_id,))
        episodes = cursor.fetchall()
        return episodes


def get_episode(mal_id, episode: int=None):
    with SQL(control.malSyncDB) as cursor:
        if episode:
            cursor.execute('SELECT * FROM episodes WHERE mal_id=? AND number=?', (mal_id, episode))
        else:
            cursor.execute('SELECT * FROM episodes WHERE mal_id=?', (mal_id,))
        episode = cursor.fetchone()
        return episode


def get_show(mal_id):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT * FROM shows WHERE mal_id IN (%s)' % mal_id)
        shows = cursor.fetchone()
        return shows


def get_show_meta(mal_id: int):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT * FROM shows_meta WHERE mal_id IN (%s)' % mal_id)
        shows = cursor.fetchone()
        return shows


def remove_from_database(table: str, mal_id) -> None:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE mal_id=?", (mal_id,))
        cursor.connection.commit()


def get_mappings(anime_id, send_id):
    with SQL(control.mappingDB) as cursor:
        cursor.execute(f'SELECT * FROM anime WHERE {send_id}=?', (anime_id,))
        mappings = cursor.fetchall()
        return mappings[0] if mappings else {}


def getSearchHistory(media_type: str = 'show'):
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS show (value TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS movie (value TEXT)')
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON movie (value)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON show (value)")
        cursor.execute("SELECT * FROM %s" % media_type)
        history = cursor.fetchall()
        history.reverse()
        history = history[:50]
        filter_ = []
        for i in history:
            if i['value'] not in filter_:
                filter_.append(i['value'])
        return filter_


def addSearchHistory(search_string: str, media_type: str) -> None:
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS show (value TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS movie (value TEXT)')
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON movie (value)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON show (value)")
        cursor.execute("REPLACE INTO %s Values (?)" % media_type, (search_string,))
        cursor.connection.commit()


def clearSearchHistory() -> None:
    confirmation = control.yesno_dialog(control.ADDON_NAME, "Clear search history?")
    if not confirmation:
        return
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute("DROP TABLE IF EXISTS movie")
        cursor.execute("DROP TABLE IF EXISTS show")
        cursor.execute("VACCUM")
        cursor.connection.commit()
        control.refresh()
        control.notify(control.ADDON_NAME, "Search History has been cleared", time=5000)


def remove_search(table: str, value: str) -> None:
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute(f'DELETE FROM {table} WHERE value=?', (value,))
        cursor.connection.commit()
        control.refresh()


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class SQL:
    def __init__(self, path: str, timeout: int = 60):
        self.lock = threading.Lock()
        self.path = path
        self.timeout = timeout

    def __enter__(self):
        self.lock.acquire()
        xbmcvfs.mkdir(control.dataPath)
        conn = dbapi2.connect(self.path, timeout=self.timeout)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA FOREIGN_KEYS=1")
        self.cursor = conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        if self.lock.locked():
            self.lock.release()

        if exc_type:
            import traceback
            control.log('database error')
            control.log(f"{''.join(traceback.format_exception(exc_type, exc_val, exc_tb))}", 'error')
            if exc_type is OperationalError:
                return True


