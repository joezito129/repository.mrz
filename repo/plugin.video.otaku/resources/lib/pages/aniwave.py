import base64
import json
import pickle
import re
import xbmc
import requests

from bs4 import BeautifulSoup, SoupStrainer
from urllib import parse
from resources.lib.ui import control, database
from resources.lib.ui.BrowserBase import BrowserBase


class Sources(BrowserBase):
    _BASE_URL = 'https://aniwave.se/'
    EKEY = "ysJhV6U27FVIjjuk"
    DKEY = "hlPeNwkncH0fq9so"
    CHAR_SUBST_OFFSETS = (-3, 3, -4, 2, -2, 5, 4, 5)

    def get_sources(self, mal_id, episode, get_backup=None):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta['name']
        title = self._clean_title(title)

        all_results = []
        items = []
        srcs = ['dub', 'sub', 'softsub']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            srcs.remove('sub')
            srcs.remove('softsub')

        headers = {'Referer': self._BASE_URL}
        params = {'keyword': title}
        res = requests.get(f'{self._BASE_URL}ajax/anime/search', headers=headers, params=params)
        r = res.text
        if not r and ':' in title:
            title = title.split(':')[0]
            params['keyword'] = title
            if not r and ':' in title:
                title = title.split(':')[0]
                params['keyword'] = title
                r = requests.get(f'{self._BASE_URL}ajax/anime/search', headers=headers, params=params)
            if not r:
                return all_results
        if not r:
            return all_results

        if 'NOT FOUND' not in r:
            r = res.json()
            r = BeautifulSoup(r.get('html') or r.get('result', {}).get('html'), "html.parser")
            sitems = r.find_all('a', {'class': 'item'})
            if sitems:
                items = [parse.urljoin(self._BASE_URL, x.get('href')) for x in sitems if self.clean_title(title) in self.clean_title(x.find('div', {'class': 'name'}).text)]

        if items:
            slug = items[0]
            all_results = self._process_aw(slug, title=title, episode=episode, langs=srcs)
        return all_results

    def _process_aw(self, slug, title, episode, langs):
        sources = []
        headers = {'Referer': self._BASE_URL}
        r = requests.get(slug, headers=headers).text
        sid = re.search(r'id="watch-main.+?data-id="([^"]+)', r)
        if not sid:
            return sources

        sid = sid.group(1)
        vrf = self.generate_vrf(sid)
        params = {'vrf': vrf}
        r = requests.get(f'{self._BASE_URL}ajax/episode/list/{sid}', headers=headers, params=params)
        res = r.json().get('result')
        elink = SoupStrainer('div', {'class': re.compile('^episodes')})
        ediv = BeautifulSoup(res, "html.parser", parse_only=elink)
        items = ediv.find_all('a')
        e_id = [x.get('data-ids') for x in items if x.get('data-num') == episode]
        if e_id:
            e_id = e_id[0]
            vrf = self.generate_vrf(e_id)
            params = {'vrf': vrf}
            r = requests.get(f'{self._BASE_URL}ajax/server/list/{e_id}', headers=headers, params=params)
            eres = r.json().get('result')
            scrapes = 0
            for lang in langs:
                elink = SoupStrainer('div', {'data-type': lang})
                sdiv = BeautifulSoup(eres, "html.parser", parse_only=elink)
                srcs = sdiv.find_all('li')
                for src in srcs:
                    edata_id = src.get('data-link-id')
                    edata_name = src.text
                    if self.clean_title(edata_name) in self.embeds():
                        if scrapes == 3:
                            xbmc.sleep(5000)
                            scrapes = 0
                        vrf = self.generate_vrf(edata_id)
                        params = {'vrf': vrf}
                        r = requests.get(f'{self._BASE_URL}ajax/server/{edata_id}', headers=headers, params=params)
                        scrapes += 1
                        resp = r.json().get('result')
                        skip = {}
                        if resp.get('skip_data'):
                            skip_data = json.loads(self.decrypt_vrf(resp.get('skip_data')))
                            intro = skip_data.get('intro')
                            if intro:
                                skip['intro'] = {'start': intro[0], 'end': intro[1]}
                            outro = skip_data.get('outro')
                            if outro:
                                skip['outro'] = {'start': outro[0], 'end': outro[1]}
                        slink = self.decrypt_vrf(resp.get('url'))
                        source = {
                            'release_title': '{0} - Ep {1}'.format(title, episode),
                            'hash': slink,
                            'type': 'embed',
                            'quality': 0,
                            'debrid_provider': '',
                            'provider': 'aniwave',
                            'size': 'NA',
                            'byte_size': 0,
                            'info': [lang, edata_name],
                            'lang': 2 if lang == 'dub' else 0,
                            'skip': skip
                        }
                        sources.append(source)
        return sources

    @staticmethod
    def vrf_shift(t, offsets=CHAR_SUBST_OFFSETS):
        o = ''
        for s in range(len(t)):
            o += chr(ord(t[s]) + offsets[s % 8])
        return o

    @staticmethod
    def clean_title(text):
        return re.sub(r'\W', '', text).lower()

    @staticmethod
    def arc4(key, data):
        l_key = len(key)
        S = [i for i in range(256)]
        j = 0
        out = bytearray()
        app = out.append

        for i in range(256):
            j = (j + S[i] + key[i % l_key]) % 256
            S[i], S[j] = S[j], S[i]

        i = j = 0
        for c in data:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            app(c ^ S[(S[i] + S[j]) % 256])

        return out

    def generate_vrf(self, content_id, key=EKEY):
        vrf = self.arc4(bytes(key.encode(encoding='latin-1')), bytes(parse.quote(content_id).encode(encoding='latin-1')))
        vrf = base64.urlsafe_b64encode(vrf)
        vrf = base64.b64encode(vrf).decode()
        vrf = vrf.replace('/', '_').replace('+', '-')
        vrf = self.vrf_shift(vrf)
        vrf = base64.b64encode(bytes(vrf[::-1].encode(encoding='latin-1'))).decode()
        vrf = vrf.replace('/', '_').replace('+', '-')
        return vrf

    def decrypt_vrf(self, text, key=DKEY):
        data = self.arc4(bytes(key.encode(encoding='latin-1')), base64.urlsafe_b64decode(bytes(text.encode(encoding='latin-1'))))
        data = parse.unquote(data.decode())
        return data
