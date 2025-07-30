import json
import pickle
import re
import urllib.parse
import requests
import itertools

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui import control, database, BrowserBase


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://animixplay.name/'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = self._clean_title(kodi_meta['name'])

        lang_int = control.getInt('general.source')  # 0 SUB, 1 BOTH, 2 DUB
        if lang_int == 1:
            srcs = ['dub', 'sub']
        elif lang_int == 2:
            srcs = ['dub']
        elif lang_int == 0:
            srcs = ['sub']
        else:
            srcs = []

        all_results = []
        headers = {
            'Origin': self._BASE_URL[:-1],
            'Referer': self._BASE_URL
        }
        r = requests.post(f'{self._BASE_URL}api/search', data={'qfast': title}, headers=headers)
        if r.ok:
            soup = BeautifulSoup(r.json()['result'], 'html.parser')
            items = soup.find_all('a')
            slugs = []

            for item in items:
                ititle = item.find('p', {'class': 'name'})
                if ititle:
                    ititle = ititle.text.strip()
                    if 'sub' in srcs:
                        if self.clean_embed_title(ititle) == self.clean_embed_title(title):
                            slugs.append(item.get('href'))
                    if 'dub' in srcs:
                        if self.clean_embed_title(ititle) == self.clean_embed_title(title) + 'dub':
                            slugs.append(item.get('href'))
            if not slugs:
                if len(items) > 0:
                    slugs = [items[0].get('href')]
            if slugs:
                slugs = list(slugs.keys()) if isinstance(slugs, dict) else slugs
                mapfunc = partial(self._process_animix, title=title, episode=episode)
                all_results = map(mapfunc, slugs)
                all_results = list(itertools.chain(*all_results))
        return all_results

    def _process_animix(self, slug, title, episode):
        sources = []
        lang = 2 if slug[-3:] == 'dub' else 0
        slug_url = urllib.parse.urljoin(self._BASE_URL, slug)
        headers = {'Referer': self._BASE_URL}
        r = requests.get(slug_url, headers=headers).text
        eplist = re.search(r'<div\s*id="epslistplace".+?>([^<]+)', r)
        if eplist:
            eplist = json.loads(eplist.group(1).strip())
            ep = str(int(episode) - 1)
            if ep in eplist.keys():
                playbunny = 'https://play.bunnycdn.to/'
                esurl = '{0}hs/{1}'.format(playbunny, eplist.get(ep).split('/')[-1])
                headers = {'Referer': playbunny}
                epage = requests.get(esurl, headers=headers).text
                ep_id = re.search(r'<div\s*id="mg-player"\s*data-id="([^"]+)', epage)
                if ep_id:
                    ep_url = '{0}hs/getSources?id={1}'.format(playbunny, ep_id.group(1))
                    ep_src = requests.get(ep_url, headers=headers)
                    try:
                        ep_src = ep_src.json()
                    except json.JSONDecodeError:
                        return sources
                    src = ep_src.get('sources')
                    if src:
                        server = 'bunny'
                        skip = {}
                        intro = ep_src.get('intro')
                        if intro.get('end'):
                            skip['intro'] = {}
                            skip['intro']['start'] = intro.get('start')
                            skip['intro']['end'] = intro.get('end')
                        outro = ep_src.get('outro')
                        if outro.get('end'):
                            skip['outro'] = {}
                            skip['outro']['start'] = outro.get('start')
                            skip['outro']['end'] = outro.get('end')

                        source = {
                            'release_title': f'{title} Ep{episode}',
                            'hash': f'{src}|Referer={playbunny}&Origin={playbunny[:-1]}&User-Agent=iPad',
                            'type': 'direct',
                            'quality': 2,
                            'debrid_provider': '',
                            'provider': 'animix',
                            'size': 'NA',
                            'seeders': -1,
                            'byte_size': 0,
                            'info': [f'{server} {slug[-3:]}'],
                            'lang': lang,
                            'skip': skip
                        }
                        sources.append(source)

        return sources
