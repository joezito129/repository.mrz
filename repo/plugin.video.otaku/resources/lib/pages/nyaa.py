import pickle
import re
import requests

from functools import partial
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.debrid import Debrid
from resources.lib.ui import BrowserBase, database, source_utils, control


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://nyaa.si'

    def __init__(self):
        self.media_type = None
        self.cached = []
        self.uncached = []
        self.sources = []

    def process_nyaa(self, url, params, episode_zfill, season_zfill, part=None):
        r = requests.get(url, params)
        html = r.text
        mlink = SoupStrainer('div', {'class': 'table-responsive'})
        soup = BeautifulSoup(html, "html.parser", parse_only=mlink)
        re_mag = re.compile(r'(magnet:)+[^"]*')
        re_hash = re.compile(r'btih:(.*?)(?:&|$)')
        list_ = []
        for i in soup.select("tr.danger,tr.default,tr.success"):
            magnet = i.find('a', {'href': re_mag}).get('href')
            hash_ = re_hash.findall(magnet)[0]
            name = i.find_all('a', {'class': None})[1].get('title')
            size = i.find_all('td', {'class': 'text-center'})[1].text.replace('i', '')
            seeders = int(i.find_all('td', {'class': 'text-center'})[-3].text)
            downloads = int(i.find_all('td', {'class': 'text-center'})[-1].text)
            source = {
                'magnet': magnet,
                'hash': hash_,
                'name': name,
                'size': size,
                'seeders': seeders,
                'downloads': downloads
            }
            list_.append(source)
        if self.media_type != 'movie':
            filtered_list = source_utils.filter_sources(list_, int(season_zfill), int(episode_zfill), part=part)
        else:
            filtered_list = list_

        cache_list, uncashed_list_ = Debrid().torrentCacheCheck(filtered_list)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

        uncashed_list = [i for i in uncashed_list_ if i['seeders'] > 0]
        uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)

        re_size = re.compile(r'(\d+).(\d+) (\w+)')
        mapfunc = partial(self.parse_nyaa_view, episode=episode_zfill, re_size=re_size, cached=True)
        all_results = list(map(mapfunc, cache_list))
        if control.settingids.showuncached:
            mapfunc2 = partial(self.parse_nyaa_view, episode=episode_zfill, re_size=re_size, cached=False)
            all_results += list(map(mapfunc2, uncashed_list))
        return all_results

    def get_sources(self, query, mal_id, episode, status, media_type):
        query = self._clean_title(query).replace('-', ' ')
        self.media_type = media_type
        if media_type != 'movie':
            self.get_episode_sources(query, mal_id, episode, status)
        else:
            self.get_movie_sources(query, mal_id)

        # remove any duplicate sources
        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def get_episode_sources(self, show: str, mal_id: int, episode: str, status: str) -> None:
        if 'part' in show.lower():
            part = re.search(r'part ?(\d+)', show.lower())
            if part:
                part = int(part.group(1).strip())
        else:
            part = None

        season = database.get_episode(mal_id)['season']
        season_zfill = str(season).zfill(2)
        episode_zfill = episode.zfill(2)
        query = f'{show} "- {episode_zfill}"'
        query += f'|"S{season_zfill}E{episode_zfill}"'

        params = {
            'f': '0',
            'c': '1_0',
            'q': query.replace(' ', '+'),
            's': 'downloads',
            'o': 'desc'
        }
        self.sources += self.process_nyaa(self._BASE_URL, params, episode_zfill, season_zfill, part)
        if status == "Finished Airing":
            query = '%s "Batch"|"Complete Series"' % show
            episodes = pickle.loads(database.get_show(mal_id)['kodi_meta'])['episodes']
            if episodes:
                query += f'|"01-{episode_zfill}"|"01~{episode_zfill}"|"01 - {episode_zfill}"|"01 ~ {episode_zfill}"'

            query += f'|"S{season_zfill}"|"Season {season_zfill}"|"S{season_zfill}E{episode_zfill}"|"- {episode_zfill}"'

            params = {
                'f': '0',
                'c': '1_0',
                'q': query.replace(' ', '+'),
                's': 'seeders',
                'o': 'desc'
            }
            self.sources += self.process_nyaa(self._BASE_URL, params, episode_zfill, season_zfill, part)

        params = {
            'f': '0',
            'c': '1_0',
            'q': query.replace(' ', '+')
        }
        self.sources += self.process_nyaa(self._BASE_URL, params, episode_zfill, season_zfill, part)

    def get_movie_sources(self, query, mal_id) -> None:
        params = {
            'f': '0',
            'c': '1_2',
            'q': query.replace(' ', '+'),
            's': 'downloads',
            'o': 'desc'
        }
        self.sources = self.process_nyaa(self._BASE_URL, params, '01', None)

    @staticmethod
    def parse_nyaa_view(res: dict, episode: str, re_size, cached: bool) -> dict:
        source = {
            'release_title': res['name'],
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res.get('debrid_provider'),
            'provider': 'nyaa',
            'episode_re': episode,
            'size': res['size'],
            'byte_size': 0,
            'info': source_utils.getInfo(res['name']),
            'lang': source_utils.getAudio_lang(res['name']),
            'cached': cached,
            'seeders': res['seeders']
        }
        match = re_size.match(res['size'])
        if match:
            source['byte_size'] = source_utils.convert_to_bytes(float(f'{match.group(1)}.{match.group(2)}'), match.group(3))
        if not cached:
            source['magnet'] = res['magnet']
            source['type'] += ' (uncached)'
        return source

    def append_cache_uncached_noduplicates(self) -> None:
        seen_sources = []
        for source in self.sources:
            if source not in seen_sources:
                seen_sources.append(source)
                if source['cached']:
                    self.cached.append(source)
                else:
                    self.uncached.append(source)
                    