import json
import pickle
import re

import requests
from bs4 import BeautifulSoup, SoupStrainer
from urllib import parse
from resources.lib.ui import control, database, utils
from resources.lib.ui.jscrypto import jscrypto
from resources.lib.ui.BrowserBase import BrowserBase


class sources(BrowserBase):
    _BASE_URL = 'https://aniwatch.to/'
    keyurl = 'https://raw.githubusercontent.com/enimax-anime/key/e6/key.txt'
    keyhints = [[53, 59], [71, 78], [119, 126], [143, 150]]

    def get_sources(self, anilist_id, episode):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta['name']
        title = self._clean_title(title)

        langs = ['sub', 'dub']
        if control.getSetting('general.source') == 'Sub':
            langs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            langs.remove('sub')

        headers = {
            'Referer': self._BASE_URL
        }
        params = {
            'keyword': title
        }
        html = database.get_(utils.database_request_get, 8,
                             f'{self._BASE_URL}search', params=params, headers=headers, text=True)

        mlink = SoupStrainer('div', {'class': 'flw-item'})
        mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
        sdivs = mdiv.find_all('h3')
        sitems = []
        for sdiv in sdivs:
            try:
                slug = sdiv.find('a').get('href').split('?')[0]
                stitle = sdiv.find('a').get('data-jname')
                sitems.append({'title': stitle, 'slug': slug})
            except AttributeError:
                pass

        all_results = []
        if sitems:
            if title[-1].isdigit():
                items = [x.get('slug') for x in sitems if title.lower() in x.get('title').lower()]
            else:
                items = [x.get('slug') for x in sitems if (title.lower() + '  ') in (x.get('title').lower() + '  ')]
            if not items and ':' in title:
                title = title.split(':')[0]
                items = [x.get('slug') for x in sitems if (title.lower() + '  ') in (x.get('title').lower() + '  ')]

            if items:
                slug = items[0]
                all_results = self._process_aw(slug, title=title, episode=episode, langs=langs)
        return all_results

    def _process_aw(self, slug, title, episode, langs):
        sources_ = []
        headers = {
            'Referer': self._BASE_URL
        }
        r = database.get_(utils.database_request_get, 8,
                          f'{self._BASE_URL}ajax/v2/episode/list/{slug.split("-")[-1]}', headers=headers)
        res = r.get('html')
        elink = SoupStrainer('div', {'class': re.compile('^ss-list')})
        ediv = BeautifulSoup(res, "html.parser", parse_only=elink)
        items = ediv.find_all('a')
        e_id = [x.get('data-id') for x in items if x.get('data-number') == episode][0]

        params = {
            'episodeId': e_id
        }
        r = database.get_(utils.database_request_get, 8,
            f'{self._BASE_URL}ajax/v2/episode/servers', params=params, headers=headers)
        eres = r.get('html')
        for lang in langs:
            elink = SoupStrainer('div', {'class': re.compile('servers-{0}$'.format(lang))})
            sdiv = BeautifulSoup(eres, "html.parser", parse_only=elink)
            edata_id = sdiv.find('div', {'data-server-id': '4'})
            if edata_id:
                params = {
                    'id': edata_id.get('data-id')
                }
                r = database.get_(utils.database_request_get, 8,
                                  f'{self._BASE_URL}ajax/v2/episode/sources', params=params, headers=headers)
                slink = r.get('link')
                headers = {
                    'Referer': slink
                }
                sl = parse.urlparse(slink)
                spath = sl.path.split('/')
                spath.insert(2, 'ajax')
                sid = spath.pop(-1)
                eurl = '{}://{}{}/getSources'.format(sl.scheme, sl.netloc, '/'.join(spath))
                params = {
                    'id': sid
                }
                res = database.get_(utils.database_request_get, 8,
                                    eurl, params=params, headers=headers)
                subs = res.get('tracks')
                if subs:
                    subs = [{'url': x.get('file'), 'lang': x.get('label')} for x in subs if x.get('kind') == 'captions']
                slink = self._process_link(res.get('sources'))
                if not slink:
                    continue
                res = requests.get(slink, headers=headers).text
                quals = re.findall(r'#EXT.+?RESOLUTION=\d+x(\d+).+\n(?!#)(.+)', res)

                for item in quals:
                    qual = int(item[0])
                    if qual < 577:
                        quality = 'NA'
                    elif qual < 721:
                        quality = '720p'
                    elif qual < 1081:
                        quality = '1080p'
                    else:
                        quality = '4K'
                    source = {
                        'release_title': '{0} - Ep {1}'.format(title, episode),
                        'hash': parse.urljoin(slink, item[1]) + '|User-Agent=iPad',
                        'type': 'direct',
                        'quality': quality,
                        'debrid_provider': '',
                        'provider': 'aniwatch',
                        'size': 'NA',
                        'info': ['DUB' if lang == 'dub' else 'SUB'],
                        'lang': 2 if lang == 'dub' else 0,
                        'subs': subs
                    }
                    sources_.append(source)

        return sources_

    def _process_link(self, sources_):
        r = database.get_(utils.database_request_get, 4,
                          self.keyurl)

        keyhints = r or self.keyhints
        key = ''
        orig_src = sources_
        for start, end in keyhints:
            key += orig_src[start:end]
            sources_ = sources_.replace(orig_src[start:end], '')

        try:
            if 'file' not in sources_:
                sources_ = json.loads(jscrypto.decode(sources_, key))
            return sources_[0].get('file')
        except:
            return ''
