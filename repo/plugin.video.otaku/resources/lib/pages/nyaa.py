import re
import feedparser
import requests

from functools import partial
from urllib import parse
from resources.lib.debrid import Debrid
from resources.lib.ui import BrowserBase, database, source_utils, control


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://nyaa.si'
    feedparser.SANITIZE_HTML = 0
    feedparser.RESOLVE_RELATIVE_URIS = 0

    def __init__(self):
        self.media_type = None
        self.cached = []
        self.uncached = []
        self.sources = []
        self.titles = None
        self.S = requests.Session()

    def process_nyaa(self, url, params, episode_zfill, season_zfill) -> list:
        params['page'] = 'rss'

        r = self.S.get(url, params=params)
        feed = feedparser.parse(r.content)

        list_ = []
        trackers = [
            "http://nyaa.tracker.wf:7777/announce",
            "udp://open.stealth.si:80/announce",
            "udp://tracker.opentrackr.org:1337/announce",
            "udp://exodus.desync.com:6969/announce",
            "udp://tracker.torrent.eu.org:451/announce",
            "udp://tracker.internetwarriors.net:1337/announce",
            "udp://tracker.cyberia.is:6969/announce",
            "udp://tracker.tiny-vps.com:6969/announce",
            "udp://open.demonii.com:1337/announce",
            "udp://ipv4.tracker.harry.lu:80/announce",
            "udp://tracker.bitsearch.to:1337/announce"
        ]
        tr_params = "".join([f"&tr={parse.quote(t)}" for t in trackers])

        for entry in feed.entries:
            info_hash = entry.get('nyaa_infohash')
            if info_hash:
                title = entry.get('title', '')
                dn_params = f"&dn={parse.quote(title)}"
                list_.append({
                    "name": title,
                    'hash': info_hash,
                    "magnet": f"magnet:?xt=urn:btih:{info_hash}{dn_params}{tr_params}",
                    "size": entry.get('nyaa_size', ''),
                    "seeders": int(entry.get('nyaa_seeders', 0)),
                    "leechers": int(entry.get('nyaa_leechers', 0)),
                    "downloads": int(entry.get('nyaa_downloads', 0))
                })

        if self.media_type != 'movie':
            filtered_list = source_utils.filter_sources(list_, season_zfill, int(episode_zfill), titles=self.titles)
        else:
            filtered_list = list_

        cache_list, uncashed_list_ = Debrid().torrentCacheCheck(filtered_list)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

        uncashed_list = [i for i in uncashed_list_ if i['seeders'] > 0]
        uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)

        re_size = re.compile(r'(\d+).(\d+) (\w+)')
        mapfunc = partial(self.parse_nyaa_view, episode=episode_zfill, re_size=re_size, cached=True)
        all_results = list(map(mapfunc, cache_list))
        if control.getBool('show.uncached'):
            mapfunc2 = partial(self.parse_nyaa_view, episode=episode_zfill, re_size=re_size, cached=False)
            all_results += list(map(mapfunc2, uncashed_list))
        return all_results


    def get_sources(self, titles, mal_id, episode, status, media_type, episodes):
        self.titles = titles
        show = '"' + '"|"'.join(titles) + '"'
        self.media_type = media_type

        if media_type != 'movie':
            self.get_episode_sources(show, mal_id, episode, status, episodes)
        else:
            self.get_movie_sources(show, mal_id)

        # remove any duplicate sources
        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def get_episode_sources(self, show: str, mal_id: int, episode: int, status: str, episodes: int) -> None:
        episode_zfill = str(episode).zfill(2)
        episode_query = {f'- {episode_zfill}'}

        season = database.get_episode(mal_id)
        if season:
            season = season.get('season', 1)
            season_zfill = str(season).zfill(2)
            episode_query.add(f'S{season_zfill}E{episode_zfill}')
        else:
            season_zfill = None

        if episode > 100:
            episode_query.add(f'{str(episode)[:-1]}*')

        # episode_query.add("batch|series")
        query = f'({show}) {episode_zfill}|' + "|".join(episode_query)
        params = {
            'f': '0',
            'c': '1_0',
            'q': query
        }

        self.sources += self.process_nyaa(self._BASE_URL, params, episode_zfill, season_zfill)
        params['q'] = show
        self.sources += self.process_nyaa(self._BASE_URL, params, episode_zfill, season_zfill)


    def get_movie_sources(self, query, mal_id) -> None:
        params = {
            'f': '0',
            'c': '1_2',
            'q': query
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
