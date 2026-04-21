import ast
import hashlib
import re
import time
import xbmcvfs

from sqlite3 import dbapi2
from resources.lib.ui import control
from resources.packages import msgpack


def background_cache(func, duration, *args, **kwargs):
    if not control.getBool('general.kodi.cache'):
        return None
    try:
        cache(func, duration, True, *args, **kwargs)
    except Exception as e:
        control.log(f"Background Cache Error: {e}", 'warning')


def _mem_get(key):
    """Get cached value from Kodi window property."""
    raw = control.window.getProperty(f'otaku_cache_{key}')
    try:
        if raw:
            data = ast.literal_eval(raw)
            if data[0] > int(time.time()):
                return data[1]
    except Exception as e:
        control.log(f"Cache Error: {e}", 'warning')
    return None


def _mem_set(key, value, expires):
    """Store value in Kodi window property"""
    if control.getBool('general.kodi.cache'):
        control.window.setProperty(f'otaku_cache_{key}', repr((expires, value)))



def cache(function, duration, disk_db: bool, *args, **kwargs):
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result

    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
     :param disk_db: Bool save response to cache.db file
    :param args: Optional arguments for the provided function
    :param kwargs: Optional keyword arguments for the provided function
    """

    key = hash_function(function, args, kwargs)

    # 1. Check Kodi Window Property
    cache_result = _mem_get(key)
    if cache_result:
        return cache_result

    expires = int(time.time()) + duration * 60 * 60

    # 2. Check Cache.db
    if disk_db:
        db_result = cache_get(key)
        if db_result and is_cache_valid(db_result['date'], duration * 60 * 60):
            try:
                data = ast.literal_eval(db_result['value'])
                _mem_set(key, data, expires)
                return data
            except Exception as e:
                control.log(f"Cache Error: {e}", 'warning')

    # 3. API call
    fresh_result_raw = repr(function(*args, **kwargs))
    data = ast.literal_eval(fresh_result_raw)

    if data:
        _mem_set(key, data, expires)
        if disk_db:
            cache_insert(key, fresh_result_raw)
    return data


def get_(function, duration, *args, **kwargs):
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result

    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
    :param args: Optional arguments for the provided function
    :param kwargs: Optional keyword arguments for the provided function
    """

    key = hash_function(function, args, kwargs)

    # 1. Check Kodi Window Property
    cache_result = _mem_get(key)
    if cache_result:
        return cache_result

    expires = int(time.time()) + duration * 60 * 60

    # 2. Check Cache.db
    db_result = cache_get(key)
    if db_result and is_cache_valid(db_result['date'], duration):
        try:
            data = ast.literal_eval(db_result['value'])
            _mem_set(key, data, expires)
            return data
        except Exception as e:
            control.log(f"Cache Error: {e}", 'warning')

    # 3. API call
    fresh_result_raw = repr(function(*args, **kwargs))
    data = ast.literal_eval(fresh_result_raw)

    if data:
        _mem_set(key, data, expires)
        cache_insert(key, fresh_result_raw)
    return data


def hash_function(function_instance, *args) -> str:
    function_name = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))
    return function_name + generate_md5(args)


def generate_md5(*args) -> str:
    md5_hash = hashlib.md5()
    for arg in args:
        md5_hash.update(str(arg).encode('utf-8'))
        md5_hash.update(b'|')
    return md5_hash.hexdigest()


def cache_get(key):
    with SQL(control.cacheFile) as cursor:
        cursor.execute('SELECT * FROM cache WHERE key=?', (key,))
        results = cursor.fetchone()
        return results


def cache_insert(key: str, value: str) -> None:
    now = int(time.time())
    with SQL(control.cacheFile) as cursor:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_cache ON cache (key)')
        cursor.execute('REPLACE INTO cache (key, value, date) VALUES (?, ?, ?)', (key, value, now))
        cursor.connection.commit()


def cache_clear() -> None:
    control.window.clearProperties()
    control.process_context()
    with SQL(control.cacheFile) as cursor:
        cursor.execute("DROP TABLE IF EXISTS cache")
        cursor.execute("VACUUM")
        cursor.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
        cursor.connection.commit()
    control.notify(f'{control.ADDON_NAME}: {control.lang(30030)}', control.lang(30031))


def is_cache_valid(cached_time: int, cache_timeout: int) -> bool:
    now = int(time.time())
    diff = now - cached_time
    return cache_timeout > diff

# Mappings
def get_mappings(anime_id, send_id):
    with SQL(control.mappingDB) as cursor:
        cursor.execute(f'SELECT * FROM anime WHERE {send_id}=?', (anime_id,))
        mappings = cursor.fetchone()
        return mappings if mappings else {}

# Show
def create_show(mal_id, anilist_id, kitsu_id, anidb_id, simkl_id, art) -> None:
    art = msgpack.dumps(art)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute("REPLACE INTO shows (mal_id, anilist_id, kitsu_id, anidb_id, simkl_id, art) VALUES (?, ?, ?, ?, ?, ?)", (mal_id, anilist_id, kitsu_id, anidb_id, simkl_id, art))
        cursor.connection.commit()


def update_kodi_meta(mal_id: int, kodi_meta: str) -> None:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute("UPDATE shows SET kodi_meta=? WHERE mal_id=?", (kodi_meta, mal_id))
        cursor.connection.commit()


def update_mapping(mal_id: int, column: str, value):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f'UPDATE shows SET {column}=? WHERE mal_id=?', (value, mal_id))
        cursor.connection.commit()


def get_show_id(mal_id: int, column: str):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f"SELECT {column} FROM shows WHERE mal_id=?", (mal_id,))
        show = cursor.fetchone()
        return show[column]


def get_show(mal_id) -> dict:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute("SELECT * FROM shows WHERE mal_id=?", (mal_id,))
        show = cursor.fetchone()
        return show


def get_show_kodi_meta(mal_id) -> dict:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute("SELECT kodi_meta FROM shows WHERE mal_id=?", (mal_id,))
        show = cursor.fetchone()
        try:
            kodi_meta = msgpack.loads(show['kodi_meta'])
        except TypeError:
            kodi_meta = {}
        return kodi_meta


def update_show_data(mal_id: int, dub_data: list, last_updated: str):
    data = msgpack.dumps(dub_data)
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('REPLACE INTO show_data (mal_id, dub_data, last_updated) VALUES (?, ?, ?)', (mal_id, data, last_updated))
        cursor.connection.commit()


def get_show_data(mal_id: int):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute("SELECT * FROM show_data WHERE mal_id=?", (mal_id,))
        show_data = cursor.fetchone()
        return show_data

# episode
def create_episode(mal_id: int, number: int, update_time: str, season: int, kodi_meta: str, filler: str, anidb_ep_id: int) -> None:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('REPLACE INTO episodes (mal_id, number, last_updated, season, kodi_meta, filler, anidb_ep_id, nekobt_ep_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (mal_id, number, update_time, season, kodi_meta, filler, anidb_ep_id, ''))
        cursor.connection.commit()


def create_episode_batch(episode_batch: list) -> None:
    with SQL(control.malSyncDB) as cursor:
        if cursor is not None:
            cursor.executemany('REPLACE INTO episodes (mal_id, number, last_updated, season, kodi_meta, filler, anidb_ep_id, nekobt_ep_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', episode_batch)
            cursor.connection.commit()


def update_episode_column(mal_id: int, episode: int, column: str, value):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f"UPDATE episodes SET {column}=? WHERE mal_id=? AND number=?", (value, mal_id, episode))
        cursor.connection.commit()

def update_episode_kodi_meta_batch(episode_batch: list):
    with SQL(control.malSyncDB) as cursor:
        cursor.executemany("UPDATE episodes SET kodi_meta WHERE mal_id=? AND number=?", (episode_batch))
        cursor.connection.commit()


def get_episode_list(mal_id: int):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT* FROM episodes WHERE mal_id=?', (mal_id,))
        episodes = cursor.fetchall()
        return episodes


def get_episode(mal_id: int, episode: int):
    with SQL(control.malSyncDB) as cursor:
        cursor.execute('SELECT * FROM episodes WHERE mal_id=? AND number=?', (mal_id, episode))
        episode = cursor.fetchone()
        return episode


def remove_from_database(table: str, mal_id) -> None:
    with SQL(control.malSyncDB) as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE mal_id=?", (mal_id,))
        cursor.connection.commit()


def getSearchHistory(media_type: str) -> list:
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {media_type} (value TEXT)")
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON {media_type} (value)")
        cursor.execute(f"SELECT * FROM {media_type}")
        history = cursor.fetchall()
    history.reverse()
    return list(dict.fromkeys(i['value'] for i in history))

def addSearchHistory(search_string: str, media_type: str) -> None:
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {media_type} (value TEXT)")
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_history ON {media_type} (value)")
        cursor.execute(f"REPLACE INTO {media_type} Values (?)", (search_string,))
        cursor.connection.commit()


def clearSearchHistory(media_type: str) -> None:
    confirmation = control.yesno_dialog(control.ADDON_NAME, "Clear search history?")
    if confirmation:
        with SQL(control.searchHistoryDB) as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {media_type}")
            cursor.execute("VACUUM")
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {media_type} (value TEXT)")
            cursor.connection.commit()
        control.refresh()
        control.notify(control.ADDON_NAME, "Search History has been cleared")


def remove_search(table: str, value: str) -> None:
    with SQL(control.searchHistoryDB) as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE value=?", (value,))
        cursor.connection.commit()
    control.refresh()


def update_dub_database(json_data):
    with SQL(control.maldubDB) as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS dub_info (mal_id INTEGER PRIMARY KEY, has_dub INTEGER)")
        data_to_insert = [(int(mal_id), 1) for mal_id in json_data]
        cursor.execute("DELETE FROM dub_info")
        cursor.executemany("INSERT INTO dub_info (mal_id, has_dub) VALUES (?, ?)", data_to_insert)
        cursor.connection.commit()


def check_dub_status(mal_id):
    with SQL(control.maldubDB) as cursor:
        cursor.execute("SELECT has_dub FROM dub_info WHERE mal_id=?", (mal_id,))
        result = cursor.fetchone()
        return bool(result['has_dub']) if result else False


# database
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SQL:
    def __init__(self, path: str, timeout: int = 30):
        self.path = path
        self.timeout = timeout
        self.conn = None
        self.cursor = None

    def __enter__(self):
        if not xbmcvfs.exists(control.dataPath):
            xbmcvfs.mkdirs(control.dataPath)
        try:
            self.conn = dbapi2.connect(self.path, timeout=self.timeout, isolation_level=None)
            self.conn.row_factory = dict_factory
            self.conn.execute("PRAGMA synchronous = OFF")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA mmap_size = 168435456")
            self.conn.execute("PRAGMA FOREIGN_KEYS = ON")
            self.cursor = self.conn.cursor()
        except dbapi2.OperationalError as e:
            control.notify(control.ADDON_NAME, "Failed To Load Database")
            control.log(e, 'error')
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor is not None:
            self.cursor.close()
        if self.conn is not None:
            self.conn.close()
