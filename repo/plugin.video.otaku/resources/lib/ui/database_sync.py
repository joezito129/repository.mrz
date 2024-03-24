import os
import xbmcvfs

from resources.lib.ui import control
from sqlite3 import dbapi2


database_path = control.anilistSyncDB


class AnilistSyncDatabase:
    def __init__(self):
        self.activites = {}

        self._build_show_table()
        self._build_showmeta_table()
        self._build_episode_table()
        self._build_sync_activities()
        self._build_season_table()
        self._build_show_data_table()

        # If you make changes to the required meta in any indexer that is cached in this database
        # You will need to update the below version number to match the new addon version
        # This will ensure that the metadata required for operations is available
        # You may also update this version number to force a rebuild of the database after updating Otaku
        self.last_meta_update = '1.0.4.1'

        control.anilistSyncDB_lock.acquire()

        self._refresh_activites()

        if self.activites is None:
            cursor = self._get_cursor()
            cursor.execute("DELETE FROM shows")
            cursor.execute("DELETE FROM seasons")
            cursor.execute("DELETE FROM episodes")
            cursor.connection.commit()

            self._set_base_activites()

            cursor.execute('SELECT * FROM activities WHERE sync_id=1')
            self.activites = cursor.fetchone()
            cursor.close()

        control.try_release_lock(control.anilistSyncDB_lock)

        if self.activites is not None:
            self._check_database_version()

    def _refresh_activites(self):
        cursor = self._get_cursor()
        cursor.execute('SELECT * FROM activities WHERE sync_id=1')
        self.activites = cursor.fetchone()
        cursor.close()

    def _set_base_activites(self):
        cursor = self._get_cursor()
        cursor.execute('INSERT INTO activities(sync_id, otaku_version)'
                       'VALUES(1, ?)',
                       (self.last_meta_update,))

        cursor.connection.commit()
        self.activites = cursor.fetchone()
        cursor.close()

    def _check_database_version(self):
        # Migrate from an old version before database migrations
        if 'otaku_version' not in self.activites:
            self.clear_all_meta()
            control.anilistSyncDB_lock.acquire()
            cursor = self._get_cursor()
            cursor.execute('ALTER TABLE activities ADD COLUMN otaku_version TEXT')
            cursor.execute('UPDATE activities SET otaku_version = ?', (self.last_meta_update,))
            cursor.connection.commit()
            cursor.close()
            control.try_release_lock(control.anilistSyncDB_lock)

        if self.activites['otaku_version'] != self.last_meta_update:
            self.re_build_database(True)

    def clear_all_meta(self):
        path = control.anilistSyncDB
        xbmcvfs.delete(path)
        with open(path, 'a+'):
            pass

        self._build_show_table()
        self._build_showmeta_table()
        self._build_episode_table()
        self._build_sync_activities()
        self._build_season_table()
        self._build_show_data_table()

    def _build_show_table(self):
        control.anilistSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS shows '
                       '(anilist_id INTEGER PRIMARY KEY, '
                       'mal_id INTEGER,'
                       'simkl_id INTEGER,'
                       'kitsu_id INTEGER,'
                       'kodi_meta BLOB NOT NULL, '
                       'last_updated TEXT NOT NULL, '
                       'anime_schedule_route TEXT NOT NULL, '
                       'UNIQUE(anilist_id))')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_shows ON "shows" (anilist_id ASC )')
        cursor.connection.commit()
        cursor.close()
        control.try_release_lock(control.anilistSyncDB_lock)

    def _build_showmeta_table(self):
        control.anilistSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS shows_meta '
                       '(anilist_id INTEGER PRIMARY KEY, '
                       'meta_ids BLOB,'
                       'art BLOB, '
                       'UNIQUE(anilist_id))')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_shows_meta ON "shows_meta" (anilist_id ASC )')
        cursor.connection.commit()
        cursor.close()
        control.try_release_lock(control.anilistSyncDB_lock)

    def _build_season_table(self):
        control.anilistSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS seasons ('
                       'anilist_id INTEGER NOT NULL, '
                       'season INTEGER NOT NULL, '
                       'kodi_meta BLOB NOT NULL, '
                       'FOREIGN KEY(anilist_id) REFERENCES shows(anilist_id) ON DELETE CASCADE)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_season ON seasons (anilist_id ASC, season ASC)')
        cursor.connection.commit()
        cursor.close()
        control.try_release_lock(control.anilistSyncDB_lock)

    def _build_show_data_table(self):
        control.anilistSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS show_data '
                       '(anilist_id INTEGER PRIMARY KEY, '
                       'data BLOB NOT NULL, '
                       'last_updated TEXT NOT NULL, '
                       'UNIQUE(anilist_id))')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_show_data ON "show_data" (anilist_id ASC )')
        cursor.connection.commit()
        cursor.close()
        control.try_release_lock(control.anilistSyncDB_lock)

    def _build_episode_table(self):
        control.anilistSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS episodes ('
                       'anilist_id INTEGER NOT NULL, '
                       'season INTEGER NOT NULL, '
                       'kodi_meta BLOB NOT NULL, '
                       'last_updated TEXT NOT NULL, '
                       'number INTEGER NOT NULL, '
                       'filler TEXT, '
                       'FOREIGN KEY(anilist_id) REFERENCES shows(anilist_id) ON DELETE CASCADE)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_episodes ON episodes (anilist_id ASC, season ASC, number ASC)')
        cursor.connection.commit()
        cursor.close()
        control.try_release_lock(control.anilistSyncDB_lock)

    def _build_sync_activities(self):
        control.anilistSyncDB_lock.acquire()
        cursor = self._get_cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS activities ('
                       'sync_id INTEGER PRIMARY KEY, '
                       'otaku_version TEXT NOT NULL) '
                       )
        cursor.connection.commit()
        cursor.close()
        control.try_release_lock(control.anilistSyncDB_lock)

    @staticmethod
    def _get_cursor():
        conn = _get_connection()
        conn.execute("PRAGMA FOREIGN_KEYS = 1")
        cursor = conn.cursor()
        return cursor

    def re_build_database(self, silent=False):
        if not silent:
            confirm = control.yesno_dialog(control.ADDON_NAME, control.lang(30203))
            if confirm == 0:
                return

        # Delete mal_dub.json from app data
        try:
            os.remove(os.path.join(control.dataPath, 'mal_dub.json'))
        except FileNotFoundError:
            pass

        path = control.anilistSyncDB
        xbmcvfs.delete(path)
        with open(path, 'a+'):
            pass

        self._build_show_table()
        self._build_showmeta_table()
        self._build_episode_table()
        self._build_sync_activities()
        self._build_season_table()
        self._build_show_data_table()

        self._set_base_activites()
        self._refresh_activites()


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _get_connection():
    xbmcvfs.mkdir(control.dataPath)
    conn = dbapi2.connect(database_path, timeout=60.0)
    conn.row_factory = _dict_factory
    return conn
