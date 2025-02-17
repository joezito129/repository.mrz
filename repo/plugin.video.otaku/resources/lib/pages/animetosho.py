import re
import pickle
import base64
import asyncio

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui import database, source_utils, control, BrowserBase
from resources.lib import debrid


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://animetosho.org'

    def __init__(self):
        self.sources = []
        self.cached = []
        self.uncached = []
        self.anidb_id = None
        self.anidb_ep_id = None

    def get_sources(self, show, mal_id, episode, status, media_type) -> dict:
        asyncio.run(self.get_sources_async(show, mal_id, episode, media_type))
        return {'cached': self.cached, 'uncached': self.uncached}

    async def get_sources_async(self, show, mal_id, episode, media_type):
        show_meta = database.get_show_meta(mal_id)
        if show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            self.anidb_id = meta_ids.get('anidb_id')
            if not self.anidb_id:
                from resources.lib.indexers.simkl import SIMKLAPI
                ids = SIMKLAPI().get_mapping_ids('mal', mal_id)
                if ids:
                    self.anidb_id = meta_ids['anidb_id'] = ids['anidb']
                    database.update_show_meta(mal_id, meta_ids, pickle.loads(show_meta['art']))
        if self.anidb_id:
            episode_meta = database.get_episode(mal_id, episode)
            if episode_meta:
                self.anidb_ep_id = episode_meta['anidb_ep_id']
            if not self.anidb_ep_id:
                from resources.lib.endpoint import anidb
                anidb_meta = anidb.get_episode_meta(self.anidb_id)
                anidb_meta = {x: v for x, v in anidb_meta.items() if x.isdigit()}
                for anidb_ep in anidb_meta:
                    database.update_episode_column(mal_id, anidb_ep, 'anidb_ep_id', anidb_meta[anidb_ep]['anidb_id'])

        episode_zfill = episode.zfill(2)

        if self.anidb_ep_id:
            task1 = asyncio.create_task(self.process_animetosho_episodes(f'{self._BASE_URL}/episode/{self.anidb_ep_id}', None, episode_zfill, ''))
        else:
            task1 = None

        show = self._clean_title(show)
        if media_type != "movie":
            season = database.get_episode(mal_id)['season']
            season_zfill = str(season).zfill(2)

            query = f'{show} "- {episode_zfill}"'
        else:
            season_zfill = None
            query = show

        params = {
            'q': self._sphinx_clean(query),
            'qx': 1
        }
        if self.anidb_id:
            params['aids'] = self.anidb_id

        task2 = asyncio.create_task(self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode_zfill, season_zfill))


        show_lower = show.lower()
        if 'season' in show_lower:
            show_variations = re.split(r'season\s*\d+', show_lower)
            cleaned_variations = [self._sphinx_clean(var.strip() + ')') for var in show_variations if var.strip()]
            params['q'] = '|'.join(cleaned_variations)
        else:
            params['q'] = self._sphinx_clean(show)

        task3 = asyncio.create_task(self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode_zfill, season_zfill))

        task1_result = await task1 if task1 else []
        task2_result = await task2
        task3_result = await task3


        self.sources = task1_result + task2_result + task3_result

        # remove any duplicate sources
        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    async def process_animetosho_episodes(self, url: str, params, episode_zfill: str, season_zfill: str) -> list:
        r = await self.send_request(url, params)
        control.log('got data')
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find('div', id='content')
        if not content:
            return []
        soup_all = content.find_all('div', class_='home_list_entry')

        re_mag = re.compile(r'(magnet:)+[^"]*')
        re_seed_text = re.compile(r'Seeders')
        re_seed = re.compile(r'Seeders: (\d+)')
        re_hash = re.compile(r'btih:(\w+)&tr=http')
        list_ = []
        for soup in soup_all:
            list_item = {
                'name': soup.find('div', class_='link').a.text,
                'magnet': soup.find('a', {'href': re_mag}).get('href'),
                'size': soup.find('div', class_='size').text,
                'downloads': 0
            }
            try:
                hash_32 = re_hash.search(list_item['magnet']).group(1)
                list_item['hash'] = base64.b16encode(base64.b32decode(hash_32)).decode().lower()
            except AttributeError:
                continue
            try:
                seeders_text = soup.find('span', {'title': re_seed_text}).get('title')
                list_item['seeders'] = int(re_seed.match(seeders_text).group(1))
            except AttributeError:
                list_item['seeders'] = -1
            list_.append(list_item)
        if season_zfill:
            filtered_list = source_utils.filter_sources(list_, int(season_zfill), int(episode_zfill), anidb_id=self.anidb_id)
        else:
            filtered_list = list_

        cache_list, uncashed_list_ = debrid.torrentCacheCheck(filtered_list)
        uncashed_list = [i for i in uncashed_list_ if i['seeders'] != 0]

        uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

        mapfunc = partial(parse_animetosho_view, episode=episode_zfill)
        all_results = list(map(mapfunc, cache_list))
        if control.settingids.showuncached:
            mapfunc2 = partial(parse_animetosho_view, episode=episode_zfill, cached=False)
            all_results += list(map(mapfunc2, uncashed_list))
        return all_results

    def append_cache_uncached_noduplicates(self):
        seen_sources = []
        for source in self.sources:
            if source not in seen_sources:
                seen_sources.append(source)
                if source['cached']:
                    self.cached.append(source)
                else:
                    self.uncached.append(source)

def parse_animetosho_view(res, episode: str, cached=True) -> dict:
    source = {
        'release_title': res['name'],
        'hash': res['hash'],
        'type': 'torrent',
        'quality': source_utils.getQuality(res['name']),
        'debrid_provider': res.get('debrid_provider'),
        'provider': 'animetosho',
        'episode_re': episode,
        'size': res['size'],
        'info': source_utils.getInfo(res['name']),
        'byte_size': 0,
        'lang': source_utils.getAudio_lang(res['name']),
        'cached': cached,
        'seeders': res['seeders']
    }

    match = re.match(r'(\d+).(\d+) (\w+)', res['size'])
    if match:
        source['byte_size'] = source_utils.convert_to_bytes(float(f'{match.group(1)}.{match.group(2)}'), match.group(3))
    if not cached:
        source['magnet'] = res['magnet']
        source['type'] += ' (uncached)'
    return source
