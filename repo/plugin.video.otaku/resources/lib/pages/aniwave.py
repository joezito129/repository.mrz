import base64
import codecs
import json
import pickle
import re
import requests

from urllib import parse
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import BrowserBase, control, database


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://aniwave.se/'
    EKEY = "ysJhV6U27FVIjjuk"
    DKEY = "hlPeNwkncH0fq9so"
    CHAR_SUBST_OFFSETS = (-3, 3, -4, 2, -2, 5, 4, 5)

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta['name']
        title = self._clean_title(title)

        all_results = []
        items = []
        srcs = ['dub', 'sub', 's-sub']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            srcs.remove('sub')
            srcs.remove('s-sub')

        headers = {'Referer': self._BASE_URL}
        params = {'keyword': title}
        r = requests.get(self._BASE_URL + 'ajax/anime/search', params=params, headers=headers).text
        if 'NOT FOUND' in r:
            r1 = requests.get(self._BASE_URL + 'filter', params=params, headers=headers).text
            mlink = SoupStrainer('div', {'class': 'ani items'})
            soup = BeautifulSoup(r1, "html.parser", parse_only=mlink)
            sitems = soup.find_all('div', {'class': 'item'})
            if sitems:
                items = [
                    parse.urljoin(self._BASE_URL, x.find('a', {'class': 'name'}).get('href'))
                    for x in sitems
                    if self.clean_title(title) == self.clean_title(x.find('a', {'class': 'name'}).get('data-jp'))
                ]
                if not items:
                    items = [
                        parse.urljoin(self._BASE_URL, x.find('a', {'class': 'name'}).get('href'))
                        for x in sitems
                        if self.clean_title(title + 'dub') == self.clean_title(x.find('a', {'class': 'name'}).get('data-jp'))
                    ]
        elif r:
            r = json.loads(r)
            r = BeautifulSoup(r.get('html') or r.get('result', {}).get('html'), "html.parser")
            sitems = r.find_all('a', {'class': 'item'})
            if sitems:
                items = [
                    parse.urljoin(self._BASE_URL, x.get('href'))
                    for x in sitems
                    if self.clean_title(title) in self.clean_title(x.find('div', {'class': 'name'}).text)
                ]
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
        r = requests.get('{0}ajax/episode/list/{1}'.format(self._BASE_URL, sid), params=params, headers=headers)
        res = r.json().get('result')

        elink = SoupStrainer('div', {'class': re.compile('^episodes')})
        ediv = BeautifulSoup(res, "html.parser", parse_only=elink)
        items = ediv.find_all('a')
        e_id = [x.get('data-ids') for x in items if x.get('data-num') == episode]
        if e_id:
            e_id = e_id[0]
            vrf = self.generate_vrf(e_id)
            params = {'vrf': vrf}
            r = requests.get(f'{self._BASE_URL}ajax/server/list/{e_id}', params=params, headers=headers)
            eres = r.json().get('result')
            scrapes = 0
            embeds = self.embeds()
            for lang in langs:
                elink = SoupStrainer('div', {'data-type': lang})
                sdiv = BeautifulSoup(eres, "html.parser", parse_only=elink)
                srcs = sdiv.find_all('li')
                for src in srcs:
                    edata_id = src.get('data-link-id')
                    edata_name = src.text
                    if any(x in self.clean_title(edata_name) for x in embeds):
                        vrf = self.generate_vrf(edata_id)
                        params = {'vrf': vrf}
                        r = requests.get('{0}ajax/server/{1}'.format(self._BASE_URL, edata_id), params=params, headers=headers)
                        scrapes += 1
                        resp = r.json().get('result')
                        skip = {}
                        if resp.get('skip_data'):
                            skip_data = json.loads(self.decrypt_vrf(resp.get('skip_data')))
                            intro = skip_data.get('intro')
                            if intro:
                                skip['intro']['start'] = intro[0]
                                skip['intro']['end'] = intro[1]
                            outro = skip_data.get('outro')
                            if outro:
                                skip['outro']['start'] = outro[0]
                                skip['outro']['end'] = outro[1]
                        slink = self.decrypt_vrf(resp.get('url'))
                        if self._BASE_URL in slink:
                            sresp = self.__extract_aniwave(slink)
                            if sresp:
                                subs = sresp['subs']
                                skip = sresp['skip'] or skip
                                srclink = sresp['url']
                                headers.update({'Origin': self._BASE_URL[:-1]})
                                res = requests.get(srclink, headers=headers).text
                                quals = re.findall(r'#EXT.+?RESOLUTION=\d+x(\d+).+\n(?!#)(.+)', res)
                                for qual, qlink in quals:
                                    qual = int(qual)
                                    if qual > 1080:
                                        quality = 4
                                    elif qual > 720:
                                        quality = 3
                                    elif qual > 480:
                                        quality = 2
                                    else:
                                        quality = 1

                                    source = {
                                        'release_title': '{0} - Ep {1}'.format(title, episode),
                                        'hash': parse.urljoin(srclink, qlink) + '|User-Agent=iPad',
                                        'type': 'direct',
                                        'quality': quality,
                                        'debrid_provider': '',
                                        'provider': 'aniwave',
                                        'size': 'NA',
                                        'seeders': -1,
                                        'byte_size': 0,
                                        'info': [edata_name + (' DUB' if lang == 'dub' else ' SUB')],
                                        'lang': 2 if lang == 'dub' else 0,
                                        'skip': skip
                                    }
                                    if subs:
                                        source['subs'] = subs
                                    sources.append(source)
                        else:
                            source = {
                                'release_title': '{0} - Ep {1}'.format(title, episode),
                                'hash': slink,
                                'type': 'embed',
                                'quality': 0,
                                'debrid_provider': '',
                                'provider': 'aniwave',
                                'size': 'NA',
                                'seeders': -1,
                                'byte_size': 0,
                                'info': [edata_name + (' DUB' if lang == 'dub' else ' SUB')],
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

    def generate_vrf(self, content_id, key=EKEY):
        vrf = self.arc4(key.encode('latin-1'), parse.quote(content_id).encode('latin-1'))
        vrf = (base64.urlsafe_b64encode(vrf.encode('latin-1'))).decode('latin-1')
        vrf = (base64.b64encode(vrf.encode('latin-1'))).decode('latin-1')
        vrf = self.vrf_shift(vrf)
        vrf = (base64.b64encode(vrf.encode('latin-1'))).decode('latin-1')
        vrf = codecs.encode(vrf, 'rot_13')
        return vrf.replace('/', '_').replace('+', '-')

    def decrypt_vrf(self, text, key=DKEY):
        data = self.arc4(key.encode('latin-1'), base64.urlsafe_b64decode(text.encode('latin-1')))
        data = parse.unquote(data)
        return data

    @staticmethod
    def arc4(t, n):
        u = 0
        h = ''
        s = list(range(256))
        for e in range(256):
            x = t[e % len(t)]
            u = (u + s[e] + (x if isinstance(x, int) else ord(x))) % 256
            s[e], s[u] = s[u], s[e]

        e = u = 0
        for c in range(len(n)):
            e = (e + 1) % 256
            u = (u + s[e]) % 256
            s[e], s[u] = s[u], s[e]
            h += chr((n[c] if isinstance(n[c], int) else ord(n[c])) ^ s[(s[e] + s[u]) % 256])
        return h

    @staticmethod
    def clean_title(text):
        return re.sub(r'\W', '', text).lower()

    def __extract_aniwave(self, url) -> dict:
        page_content = requests.get(url, headers={'Referer': self._BASE_URL}).text
        r = re.search(r'''sources["\s]?[:=]\s*\[\{"?file"?:\s*"([^"]+)''', page_content)
        if r:
            subs = []
            skip = {}
            surl = r.group(1)
            if 'vipanicdn.net' in surl:
                surl = surl.replace('vipanicdn.net', 'anzeat.pro')

            s = re.search(r'''tracks:\s*(\[[^\]]+])''', page_content)
            if s:
                s = json.loads(s.group(1))
                subs = [
                    {'url': x.get('file'), 'lang': x.get('label')}
                    for x in s if x.get('kind') == 'captions'
                    and x.get('file') is not None
                ]

            s = re.search(r'''var\s*intro_begin\s*=\s*(\d+);\s*var\s*introEnd\s*=\s*(\d+);\s*var\s*outroStart\s*=\s*(\d+);\s*var\s*outroEnd\s*=\s*(\d+);''', page_content)
            if s:
                if int(s.group(2)) > 0:
                    skip = {
                        "intro": {"start": int(s.group(1)), "end": int(s.group(2))},
                        "outro": {"start": int(s.group(3)), "end": int(s.group(4))}
                    }
            surl = {'url': surl, 'subs': subs, 'skip': skip}
        else:
            surl = {}
        return surl