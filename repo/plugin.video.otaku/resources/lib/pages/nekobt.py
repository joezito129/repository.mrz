import requests

from functools import partial
from resources.lib.ui import database, source_utils, control, BrowserBase
from resources.lib.debrid import Debrid


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://nekobt.to/api/v1'
    S = requests.Session()

    def __init__(self):
        self.cached = []
        self.uncached = []
        self.nekobt_id = None
        self.nekobt_ep_id = None
        self.mal_id = None
        self.show_meta = None
        self.meta_ids = None
        self.episode = None
        self.titles = None


    def get_nekobt_ids(self):
        url = f'{self._BASE_URL}/media/search'
        params = {
            "query": self.titles[0]
        }
        r = self.S.get(url, params=params, timeout=10)
        res = control.json_res(r)
        if not r.ok:
            control.log(res, 'warning')
            return None
        resp = res.get('data', {}).get('results')
        if resp:
            self.process_similarity_nekobt_id(resp)
        return None

    def process_similarity_nekobt_id(self, similar_media: list) -> None:
        for x in similar_media:
            if x['similarity'] > 0.25:
                self.nekobt_id = x['id']
                break
        database.update_mapping(self.mal_id, 'nekobt_id', self.nekobt_id)

    def get_episode_ids(self) -> None:
        r = self.S.get(f'{self._BASE_URL}/media/{self.nekobt_id}')
        if r.ok:
            r = control.json_res(r)
            episodes = r.get('data', {}).get('episodes', [])
            self.nekobt_ep_id = next((x['id'] for x in episodes if x['episode'] == self.episode or x.get('absolute') == self.episode), None)
            with database.SQL(control.malSyncDB) as cursor:
                update_data = [(x['id'], self.mal_id, x['episode']) for x in episodes]
                self.nekobt_ep_id = next((x['id'] for x in episodes if x['episode'] == self.episode), None)
                cursor.executemany('UPDATE episodes SET nekobt_ep_id=? WHERE mal_id=? AND number=?', update_data)
                cursor.connection.commit()


    def get_sources(self, titles: list, mal_id: int, episode: int, status: str, media_type: str, episodes: int) -> dict:
        self.mal_id = mal_id
        self.episode = episode
        self.titles = titles
        show = self.titles[0]
        sources = []
        self.nekobt_id= database.get_show_id(mal_id, 'nekobt_id')
        if self.nekobt_id is None:
            self.get_nekobt_ids()
        if self.nekobt_id:
            episode_meta = database.get_episode(mal_id, episode)
            if episode_meta:
                self.nekobt_ep_id = episode_meta.get('nekobt_ep_id')
            if not self.nekobt_ep_id:
                self.get_episode_ids()

        control.log(f'{self.nekobt_id=}, {self.nekobt_ep_id=}')
        episode_zfill = str(episode).zfill(2)
        if media_type != "movie":
            season = database.get_episode(mal_id, episode)['season']
            season_zfill = str(season).zfill(2)
            query = f'"{show}" S{season_zfill}E{episode_zfill}'
        else:
            season_zfill = ''
            query = show

        params = {
            "query": query,
            'limit': 100,
            'sort_by': 'best'
        }

        if self.nekobt_id:
            params['media_id'] = self.nekobt_id
            if not self.nekobt_ep_id:
                self.get_episode_ids()

        if self.nekobt_ep_id:
            params['episode_ids'] = self.nekobt_ep_id
            params['episode_match_any'] = 'true'
            params.pop('query')

        sources += self.process_nekobt(f'{self._BASE_URL}/torrents/search', params, episode_zfill, season_zfill)

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

    def process_nekobt(self, url: str, params: dict, episode_zfill: str, season_zfill: str) -> list:
        all_sources = []
        r = self.S.get(url, params=params, timeout=10)
        res = control.json_res(r)
        if not r.ok:
            control.log(res, 'warning')
        resp = res.get('data', {})
        if not resp:
            control.log(r.url)
            return []
        list_ = [{
            'name': res['title'],
            'auto_title': res['auto_title'],
            'magnet': res['magnet'],
            'hash': res['infohash'],
            'size': int(res['filesize']),
            'seeders': int(res['seeders']),
            'leechers': int(res['leechers']),
            'downloads': int(res['completed']),
            'audio_lang': res['audio_lang'].split(','),
            'sub_lang': res['sub_lang'].split(','),
            'video_codec': res['video_codec'],
            'video_type': res['video_type'],
        } for res in resp['results']]

        if season_zfill:
            filtered_list = source_utils.filter_sources(list_, int(season_zfill), int(episode_zfill), titles=self.titles)
        else:
            filtered_list = list_

        cache_list, uncashed_list_ = Debrid().torrentCacheCheck(filtered_list)
        uncashed_list = [i for i in uncashed_list_ if i['seeders'] != 0]

        uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

        mapfunc = partial(parse_nekobt_view, episode=episode_zfill)
        all_sources += list(map(mapfunc, cache_list))
        if control.getBool('show.uncached'):
            mapfunc2 = partial(parse_nekobt_view, episode=episode_zfill, cached=False)
            all_sources += list(map(mapfunc2, uncashed_list))
        return all_sources

def parse_nekobt_view(res, episode: str, cached=True) -> dict:
    source = {
        'release_title': res['name'],
        'hash': res['hash'],
        'type': 'torrent',
        'quality': source_utils.getQuality(res['name']),
        'debrid_provider': res.get('debrid_provider'),
        'provider': 'nekobt',
        'episode_re': episode,
        'size': source_utils.get_size(res['size']),
        'info': [get_codec(res['video_codec']), get_video_type(res['video_type']), '|'] + res['audio_lang'],
        'byte_size': res['size'],
        'lang': get_audio(res['audio_lang']),
        'cached': cached,
        'seeders': res['seeders']
    }
    if not cached:
        source['magnet'] = res['magnet']
        source['type'] += ' (uncached)'
    return source


def get_audio(audio_lang: list) -> int:
    if 'en' in audio_lang and 'jp' in audio_lang:
        lang = 1
    elif 'en' in audio_lang:
        lang = 2
    else:
        lang = 0
    return lang

def get_codec(codec: int) -> str:
    codec_mapping = {
        1: 'H264',
        2: 'H265',
        3: 'AV1',
        4: 'VP9',
        5: 'MPEG-2',
        6: 'MPEG-4',
        7: 'WMV',
        8: 'VC1',
        0: 'Other'
    }
    return codec_mapping[codec]

def get_video_type(video_type: int):
    video_type_mapping = {
        15: 'Hybrid',
        14: 'BD - Remux',
        13: 'BD - Encode',
        12: 'BD - Mini',
        10: 'BD - Disc',
        9: 'WEB-DL',
        8: 'WEB - Encode',
        7: 'WEB - Mini',
        6: 'DVD - Encode',
        5: 'DVD - Remux',
        16: 'DVD - Disc',
        4: 'TV - Raw',
        3: 'TV - Encode',
        2: 'LaserDisc',
        1: 'VHS',
        0: 'Other'
    }
    return video_type_mapping[video_type]
