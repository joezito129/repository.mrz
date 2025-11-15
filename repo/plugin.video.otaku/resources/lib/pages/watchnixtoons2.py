import json
import pickle
import re

import requests
import difflib

from urllib import parse
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import BrowserBase, control, database


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://www.wcostream.tv' # wconflix.tv
    S = requests.session()

    def get_sources(self, mal_id, episode) -> list:
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = self._clean_title(kodi_meta['name'])

        all_sources = []
        data = {
            'catara': f"{title.replace(' ', '+')}+S+1+E+{episode}",
            'konuara': 'episodes'
        }
        r = self.S.post(f'{self._BASE_URL}/search', data=data)

        only_results = SoupStrainer("div", class_="cat-listview2 cat-listbsize2")
        soup = BeautifulSoup(r.text, 'html.parser', parse_only=only_results)
        soup_all = soup.find_all('a', class_='sonra')

        table = {}
        lang_int = control.getInt('general.source') # 0 SUB, 1 BOTH, 2 DUB
        for i, t in enumerate(soup_all):
            if i > 10:
                break
            text = t.text.lower()
            if str(episode) in text:
                if lang_int == 1:
                    table[text] = t.get('href')
                elif 'dubbed' in text and lang_int == 2:
                    table[text] = t.get('href')
                else: # elif 'sub' in text and lang_int == 0:
                    table[text] = t.get('href')

        match = difflib.get_close_matches(title, table, cutoff=.3)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'no-cache',
            'Referer': self._BASE_URL
        }

        for m in match:
            r = self.S.get(f"{self._BASE_URL}/{table[m]}")
            only_results = SoupStrainer("iframe")
            soup = BeautifulSoup(r.text, 'html.parser', parse_only=only_results)
            eurl = soup.iframe.get('src')

            if eurl:
                eresp = self.S.get(eurl, headers=headers)
                if eresp.ok:
                    r1 = re.search(r'getJSON\("([^"]+)', eresp.text)
                    if r1:
                        eurl2 = parse.urljoin(eurl, r1.group(1))
                        eresp2 = self.S.get(eurl2, headers=headers)
                        eresp2 = json.loads(eresp2.text)
                        server = eresp2.get('server')
                        items = []
                        if eresp2.get('enc'):
                            items.append((eresp2.get('enc'), 1))
                        if eresp2.get('hd'):
                            items.append((eresp2.get('hd'), 2))
                        if eresp2.get('fhd'):
                            items.append((eresp2.get('fhd'), 3))
                        ref = parse.urljoin(eurl, '/')
                        shdr = {
                            'User-Agent': 'iPad',
                            'Referer': ref,
                            'Origin': ref[:-1]
                        }
                        lang = 2 if "dub" in m else 0
                        for item in items:
                            hash = f'{server}/getvid?evid={item[0]}|{parse.urlencode(shdr)}'
                            source = {
                                'release_title': m.upper(),
                                'hash': hash,
                                'type': 'direct',
                                'quality': item[1],
                                'debrid_provider': '',
                                'provider': 'watchnixtoons2',
                                'size': 'NA',
                                'seeders': -1,
                            'byte_size': 0,
                                'info': ["DUB" if lang == 2 else "SUB"],
                            'lang': lang,
                            }
                            all_sources.append(source)
        return all_sources





