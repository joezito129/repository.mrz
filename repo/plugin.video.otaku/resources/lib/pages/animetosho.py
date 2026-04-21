import requests

from functools import partial
from resources.lib.ui import database, source_utils, control, BrowserBase
from resources.lib.debrid import Debrid


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://feed.animetosho.org/json'
    S = requests.Session()

    def __init__(self):
        self.cached = []
        self.uncached = []
        self.anidb_id = None
        self.anidb_ep_id = None

    def get_sources(self, titles: list, mal_id, episode, status, media_type, episodes) -> dict:
        show_titles = '"' + '"|"'.join(titles) + '"'
        sources = []

        self.anidb_id = database.get_show_id(mal_id, 'anidb_id')
        if self.anidb_id is None:
            from resources.lib.indexers.simkl import SIMKLAPI
            ids = SIMKLAPI().get_mapping_ids('mal', mal_id)
            self.anidb_id = ids['anidb'] if ids else 0
            database.update_mapping(mal_id, 'anidb_id', self.anidb_id)
        if self.anidb_id:
            episode_meta = database.get_episode(mal_id, episode)
            if episode_meta:
                self.anidb_ep_id = episode_meta['anidb_ep_id']
            if self.anidb_ep_id is None:
                from resources.lib.endpoint import anidb
                anidb_meta = anidb.get_episode_meta(self.anidb_id)
                anidb_meta = {x: v for x, v in anidb_meta.items() if x.isdigit()}
                self.anidb_ep_id = anidb_meta.get(str(episode), {}).get('anidb_id')
                if self.anidb_ep_id is None:
                    self.anidb_ep_id = 0
                    database.update_episode_column(mal_id, episode, 'anidb_ep_id', self.anidb_ep_id)
                with database.SQL(control.malSyncDB) as cursor:
                    for anidb_ep in anidb_meta:
                        cursor.execute('UPDATE episodes SET anidb_ep_id=? WHERE mal_id=? AND number=?', (anidb_meta[anidb_ep]['anidb_id'], mal_id, anidb_ep))
                    cursor.connection.commit()

        episode_zfill = str(episode).zfill(2)

        if self.anidb_ep_id:
            params = {
                'eid': self.anidb_ep_id,
                'filter[0][type]': 'torrent'
            }
            sources += self.process_animetosho(self._BASE_URL, params, episode_zfill, '')

        if media_type != "movie":
            season = database.get_episode(mal_id, episode)['season']
            season_zfill = str(season).zfill(2)
            query = f'{show_titles} {episode_zfill}|- {episode_zfill}|S{season_zfill}E{episode_zfill}'
        else:
            season_zfill = ''
            query = show_titles

        params = {
            'qx': 1,
            'filter[0][type]': 'torrent'
        }

        if self.anidb_id:
            params['aids'] = self.anidb_id

        params['q'] = self._sphinx_clean(query)
        sources += self.process_animetosho(self._BASE_URL, params, episode_zfill, season_zfill)

        params['q'] = self._sphinx_clean(show_titles)
        sources += self.process_animetosho(self._BASE_URL, params, episode_zfill, season_zfill)

        # remove any duplicate sources
        seen_sources = []
        for source in sources:
            if source not in seen_sources:
                seen_sources.append(source)
                if source['cached']:
                    self.cached.append(source)
                else:
                    self.uncached.append(source)

        return {'cached': self.cached, 'uncached': self.uncached}

    def process_animetosho(self, url: str, params: dict, episode_zfill: str, season_zfill: str) -> list:
        all_sources = []
        r = self.S.get(url, params=params)
        resp = r.json()
        list_ = [{
            'name': res['title'],
            'magnet': res['magnet_uri'],
            'hash': res['info_hash'],
            'size': res['total_size'],
            'seeders': res['seeders'] if res['seeders'] else 0,
            'leechers': res['leechers'] if res['leechers'] else 0,
            'downloads': res['torrent_downloaded_count'] if res['torrent_downloaded_count'] else 0
        } for res in resp]
        if season_zfill:
            filtered_list = source_utils.filter_sources(list_, int(season_zfill), int(episode_zfill))
        else:
            filtered_list = list_

        cache_list, uncashed_list_ = Debrid().torrentCacheCheck(filtered_list)
        uncashed_list = [i for i in uncashed_list_ if i['seeders'] != 0]

        uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

        mapfunc = partial(parse_animetosho_view, episode=episode_zfill)
        all_sources += list(map(mapfunc, cache_list))
        if control.getBool('show.uncached'):
            mapfunc2 = partial(parse_animetosho_view, episode=episode_zfill, cached=False)
            all_sources += list(map(mapfunc2, uncashed_list))
        return all_sources

def parse_animetosho_view(res, episode: str, cached=True) -> dict:
    source = {
        'release_title': res['name'],
        'hash': res['hash'],
        'type': 'torrent',
        'quality': source_utils.getQuality(res['name']),
        'debrid_provider': res.get('debrid_provider'),
        'provider': 'animetosho',
        'episode_re': episode,
        'size': source_utils.get_size(res['size']),
        'info': source_utils.getInfo(res['name']),
        'byte_size': res['size'],
        'lang': source_utils.getAudio_lang(res['name']),
        'cached': cached,
        'seeders': res['seeders']
    }
    if not cached:
        source['magnet'] = res['magnet']
        source['type'] += ' (uncached)'
    return source
