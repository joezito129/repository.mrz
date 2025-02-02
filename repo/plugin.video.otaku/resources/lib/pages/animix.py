import itertools
import json
import pickle
import re
from functools import partial

import requests
from bs4 import BeautifulSoup, SoupStrainer
from urllib import parse
from resources.lib.ui import database
from resources.lib.ui.BrowserBase import BrowserBase


class Sources(BrowserBase):
    _BASE_URL = 'https://animixplay.fun/'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta['name']
        title = self._clean_title(title)

        headers = {
            'Origin': self._BASE_URL[:-1],
            'Referer': self._BASE_URL
        }

        r = requests.post(self._BASE_URL + 'api/lsearch', data={'qfast': title}, headers=headers).text
        if not r:
            return []
        soup = BeautifulSoup(json.loads(r).get('result'), 'html.parser')
        items = soup.find_all('a')
        slugs = []

        for item in items:
            ititle = item.find('p', {'class': 'name'})
            if ititle:
                ititle = ititle.text.strip()
                if (ititle.lower() + '  ').startswith(title.lower() + '  '):
                    slugs.append(item.get('href'))
        if not slugs:
            if len(items) > 0:
                slugs = [items[0].get('href')]
        all_results = []
        if slugs:
            slugs = list(slugs.keys()) if isinstance(slugs, dict) else slugs
            mapfunc = partial(self._process_animixplay, title=title, episode=episode)
            all_results = list(map(mapfunc, slugs))
            all_results = list(itertools.chain(*all_results))
        return all_results

    def _process_animixplay(self, slug, title, episode):
        sources = []
        r = requests.get(slug, headers={'Referer': self._BASE_URL}).text
        eurl = re.search(r'id="showstreambtn"\s*href="([^"]+)', r)
        if eurl:
            eurl = eurl.group(1)
            resp = requests.get(eurl, headers={'Referer': self._BASE_URL})
            if not resp:
                return
            s = resp.text
            cookie = resp.cookies
            referer = parse.urljoin(eurl, '/')
            if episode:
                esurl = re.findall(r'src="(/ajax/stats.js[^"]+)', s)[0]
                esurl = parse.urljoin(eurl, esurl)
                epage = requests.get(esurl, headers={'Referer': eurl}).text
                soup = BeautifulSoup(epage, "html.parser")
                epurls = soup.find_all('a', {'class': 'playbutton'})
                ep_not_found = True
                for epurl in epurls:
                    try:
                        if int(epurl.text) == int(episode):
                            ep_not_found = False
                            epi_url = epurl.get('href')
                            resp = requests.get(epi_url, headers={'Referer': eurl})
                            cookie = resp.cookies
                            s = resp.text
                            break
                    except:
                        continue
                if ep_not_found:
                    return sources

            csrf_token = re.search(r'name="csrf-token"\s*content="([^"]+)', s)
            if csrf_token:
                csrf_token = csrf_token.group(1)
            else:
                return sources
            mlink = SoupStrainer('div', {'class': re.compile('sv_container$')})
            mdiv = BeautifulSoup(s, "html.parser", parse_only=mlink)
            mitems = mdiv.find_all('li')
            embed_config = self.embeds()
            for mitem in mitems:
                if any(x in mitem.text.lower() for x in embed_config):
                    type_ = 'direct'
                    server = mitem.a.get('data-name')
                    qual = mitem.a.get('title')
                    if '1080p' in qual:
                        qual = 3
                    elif 'HD' in qual:
                        qual = 2
                    else:
                        qual = 0
                    lang = 2 if mitem.a.get('id').endswith('dub') else 0

                    data = {
                        'name_server': server,
                        'data_play': mitem.a.get('data-play'),
                        'id': mitem.a.get('data-id'),
                        'server_id': mitem.a.get('data-serverid'),
                        'expired': mitem.a.get('data-expired')
                    }
                    headers = {
                        'Origin': referer[:-1],
                        'X-CSRF-TOKEN': csrf_token,
                        'Referer': eurl
                    }
                    r = requests.post(parse.urljoin(eurl, '/ajax/embed'), data=data, headers=headers, cookies=cookie).text
                    embed_url = parse.urljoin(eurl, re.findall(r'<iframe.+?src="([^"]+)', r)[0])
                    subs = ''
                    slink = ''
                    s = requests.get(embed_url, headers={'Referer': eurl}).text
                    if not s:
                        continue
                    sdiv = re.search(r'<source.+?src="([^"]+)', s)
                    if sdiv:
                        slink = sdiv.group(1)
                    else:
                        sdiv = re.search(r'sources:.+?file:\s*"([^"]+)', s, re.DOTALL)
                        if sdiv:
                            slink = sdiv.group(1)
                    subdiv = re.search(r'captions:\s*\[.+?file:\s*"([^"]+)', s, re.DOTALL)
                    if subdiv:
                        subs = subdiv.group(1)

                    if slink:
                        source = {
                            'release_title': '{0} - Ep {1}'.format(title, episode),
                            'hash': slink,  # + '|Referer={0}&Origin={1}&User-Agent=iPad'.format(referer, referer[:-1]),
                            'type': type_,
                            'quality': qual,
                            'debrid_provider': '',
                            'provider': 'animix',
                            'size': 'NA',
                            'byte_size': 0,
                            'info': [server, 'DUB' if lang == 2 else 'SUB'],
                            'lang': lang
                        }
                        if subs:
                            source['subs'] = [{'url': subs, 'lang': 'English'}]
                        sources.append(source)
        return sources
