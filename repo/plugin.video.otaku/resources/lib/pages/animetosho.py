import requests
import re
import itertools
import pickle

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import database, source_utils
from resources.lib import debrid
from resources.lib.indexers.simkl import SIMKLAPI


class Sources(BrowserBase):
    _BASE_URL = 'https://animetosho.org'

    def __init__(self):
        self.all_sources = []
        self.sources = []

    def get_sources(self, show, anilist_id, episode, status, media_type, rescrape):
        show = self._clean_title(show)
        query = self._sphinx_clean(show)

        if rescrape:
            # todo add re-scape stuff here
            pass
        if media_type != "movie":
            season = database.get_episode_list(anilist_id)[0]['season']
            season = str(season).zfill(2)
            episode = episode.zfill(2)
            query = f'{query} "\\- {episode}"'
            query += f'|"S{season}E{episode}"'
        else:
            season = None

        show_meta = database.get_show_meta(anilist_id)
        params = {
            'q': query,
            'qx': 1
        }
        if show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            params['aids'] = meta_ids.get('anidb_id')
            if not params['aids']:
                ids = SIMKLAPI().get_mapping_ids('anilist', anilist_id)
                params['aids'] = meta_ids['anidb_id'] = ids['anidb']
                database.update_show_meta(anilist_id, meta_ids, pickle.loads(show_meta['art']))

        self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode, season)

        if status == 'FINISHED':
            query = f'{show} "Batch"|"Complete Series"'
            episodes = pickle.loads(database.get_show(anilist_id)['kodi_meta'])['episodes']
            if episodes:
                query += f'|"01-{episode}"|"01~{episode}"|"01 - {episode}"|"01 ~ {episode}"'

            if season:
                query += f'|"S{season}"|"Season {season}"'
                query += f'|"S{season}E{episode}"'

            query = self._sphinx_clean(show)
            params['q'] = query
            self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode, season)

        show = show.lower()
        if 'season' in show:
            query1, query2 = show.rsplit('|', 2)
            match_1 = re.match(r'.+?(?=season)', query1)
            if match_1:
                match_1 = match_1.group(0).strip() + ')'
            match_2 = re.match(r'.+?(?=season)', query2)
            if match_2:
                match_2 = match_2.group(0).strip() + ')'
            params['q'] = self._sphinx_clean(f'{match_1}|{match_2}')

            self.sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, episode, season)

        # remove any duplicate sources
        for source in self.sources:
            if source not in self.all_sources:
                self.all_sources.append(source)
        return self.all_sources

    @staticmethod
    def process_animetosho_episodes(url, params, episode, season):
        r = requests.get(url, params=params)
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        soup_all = soup.find('div', id='content').find_all('div', class_='home_list_entry')
        rex = r'(magnet:)+[^"]*'
        list_ = [{
            'name': soup.find('div', class_='link').a.text,
            'magnet': soup.find('a', {'href': re.compile(rex)}).get('href'),
            'size': soup.find('div', class_='size').text,
            'downloads': 0,
            'torrent': soup.find('a', class_='dllink').get('href')
        } for soup in soup_all]

        regex = r'\ss(\d+)|season\s(\d+)|(\d+)+(?:st|[nr]d|th)\sseason'
        regex_ep = r'\de(\d+)\b|\se(\d+)\b|\s-\s(\d{1,3})\b'
        rex = re.compile(regex)
        rex_ep = re.compile(regex_ep)

        filtered_list = []
        for torrent in list_:
            try:
                torrent['hash'] = re.match(r'https://animetosho.org/storage/torrent/([^/]+)', torrent['torrent']).group(1)
            except AttributeError:
                continue

            if season:
                title = torrent['name'].lower()

                ep_match = rex_ep.findall(title)
                ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))

                if ep_match and ep_match[0] != int(episode):
                    regex_ep_range = r'\s\d+-\d+|\s\d+~\d+|\s\d+\s-\s\d+|\s\d+\s~\s\d+'
                    rex_ep_range = re.compile(regex_ep_range)

                    if not rex_ep_range.search(title):
                        continue

                match = rex.findall(title)
                match = list(map(int, list(filter(None, itertools.chain(*match)))))

                if not match or match[0] == int(season):
                    filtered_list.append(torrent)

            else:
                filtered_list.append(torrent)

        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(filtered_list)
        mapfunc = partial(parse_animetosho_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results


def parse_animetosho_view(res, episode):
    source = {
        'release_title': res['name'],
        'hash': res['hash'],
        'type': 'torrent',
        'quality': source_utils.getQuality(res['name']),
        'debrid_provider': res['debrid_provider'],
        'provider': 'animetosho',
        'episode_re': episode,
        'size': res['size'],
        'info': source_utils.getInfo(res['name']),
        'lang': source_utils.getAudio_lang(res['name'])
    }
    return source
