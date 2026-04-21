import requests
import re

from urllib import parse
from resources.lib.ui import BrowserBase, database, source_utils, control


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://torrentio.strem.fun'

    def __init__(self):
        self.mal_id = None
        self.episode = None
        self.kitsu_id = None
        self.media_type = None
        self.cached = []
        self.uncached = []
        self.sources = []
        self.titles = None
        self.season = None

    @staticmethod
    def headers():
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def process_torrentio(self):
        providers = control.getStringList('torrentio.config')

        config = {
            'providers': ','.join(providers)  # Providers
            # 'sort': 'qualitysize',        # Sort method (sizequality size qualitysize seeders)
            # 'limit': 10,                  # Max results per quality,
            # 'language': 'japanese',       # Language
            # 'qualityfilter': 'cam',         # Exclueded Sources (cam)
            # 'torbox': "065149be-1c2c-449c-be0a-3b87d6fba15c",  # API Key {debrid_type: key}
            # 'debridoptions': 'nodownloadlinks'  # Options (nodownloadlinks nodownloadlinks,nocatalog)
        }
        if not control.getBool('show.uncached'):
            config['debridoptions'] = 'nodownloadlinks'

        enabled_debrids = control.enabled_debrid()

        for debrid in enabled_debrids:
            if debrid == 'premiumize':
                token = control.getString('premiumize.apikey')
            else:
                token = control.getString(f'{debrid}.token')
            if token:
                config[debrid] = token

        config_torrentio = "|".join([f"{k}={v}" for k, v in config.items()])

        url = f"{self._BASE_URL}/{config_torrentio}/stream/series/kitsu:{self.kitsu_id}:{self.episode}.json"
        r = requests.get(url, headers=self.headers(), timeout=10)
        if r.ok:
            data = r.json()
        else:
            control.log(f'Torrentio could not find sources: {r.url}', 'warning')
            return

        re_hash = re.compile(r'(?<=\/)([a-f0-9]{40})(?=\/)')
        re_seeders = re.compile(r'👤\s*(\d+)')
        re_provider = re.compile(r'⚙️\s*(\w+)')
        cache_list = []
        uncashed_list = []
        for x in data['streams']:
            behaviorhints = x['behaviorHints']
            match_seeders = re_seeders.search(x['title'])
            match_provider = re_provider.search(x['title'])
            try:
                match_hash = re_hash.search(x['url'])
                torrent_hash = match_hash.group(1)
            except (AttributeError, IndexError):
                control.log('Hash not Found')
                torrent_hash = ''
            seeders = 0 if match_seeders is None else int(match_seeders.group(1))
            provider = match_provider.group(1)

            title = x['title'].split('\n', 1)[0]
            name = x['name']
            video_size = behaviorhints.get('videoSize', 0)
            cached = 'download' not in name
            dn_params = f"&dn={parse.quote(title)}"

            if 'TB' in name:
                debrid_provider = 'torbox'
            elif 'RD' in name:
                debrid_provider = 'real_debrid'
            elif 'DL' in name:
                debrid_provider = 'debrid_link'
            elif 'PM' in name:
                debrid_provider = 'premiumize'
            elif 'AD' in name:
                debrid_provider = 'alldebrid'
            else:
                debrid_provider = "Unknown"

            source = {
                'hash': torrent_hash,
                'link': x['url'],
                "magnet": f"magnet:?xt=urn:btih:{torrent_hash}{dn_params}",
                'release_title': title,
                'filename': behaviorhints.get('filename'),
                'type': 'torrentio',
                'quality': source_utils.getQuality(name),
                'debrid_provider': debrid_provider,
                'provider': provider,
                'episode_re': str(self.episode).zfill(2),
                'size': source_utils.get_size(video_size),
                'info': source_utils.getInfo(title),
                'byte_size': video_size,
                'lang': source_utils.getAudio_lang(title),
                'seeders': seeders,
                'cached': cached
            }
            if not cached and seeders > 0:
                # source['magnet'] = res['magnet']
                source['type'] += ' (uncached)'
                uncashed_list.append(source)
            else:
                cache_list.append(source)
        if control.getBool('show.uncached'):
            self.uncached = uncashed_list
        self.cached = cache_list

    def get_sources(self, titles, mal_id, episode, status, media_type, episodes):
        self.mal_id = mal_id
        self.episode = episode
        self.media_type = media_type

        if (show_ids := database.get_mappings(mal_id, 'mal_id')) is not None:
            self.kitsu_id = show_ids.get('kitsu_id')
            if self.kitsu_id is None:
                # todo add code to find kitsu_id
                pass
            if self.kitsu_id is not None:
                if media_type != 'movie':
                    self.get_episode_sources()
                else:
                    self.get_episode_sources()
                    # self.get_movie_sources()

        # remove any duplicate sources
        # self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def get_episode_sources(self) -> None:
        self.season = database.get_episode(self.mal_id, self.episode)
        if self.season is not None:
            self.season = self.season.get('season', 1)
        self.process_torrentio()


    def append_cache_uncached_noduplicates(self) -> None:
        seen_sources = []
        for source in self.sources:
            if source not in seen_sources:
                seen_sources.append(source)
                if source['cached']:
                    self.cached.append(source)
                else:
                    self.uncached.append(source)
