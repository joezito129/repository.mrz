import re

from resources.lib.ui import database, utils
from urllib import parse


class TRAKTAPI:
    def __init__(self):
        self.ClientID = "94babdea045e1b9cfd54b278f7dda912ae559fde990590db9ffd611d4806838c"
        self.baseUrl = 'https://api.trakt.tv'
        self.headers = {
            'trakt-api-version': '2',
            'trakt-api-key': self.ClientID,
            'content-type': 'application/json'
        }

    def get_trakt(self, name, mtype='tv', year=''):
        name = re.sub(r'(?i)(?:part|cour)\s\d+$', '', name)
        name = re.sub(r'(?i)season\s\d+$', '', name)
        name = re.sub(r'(?i)(?:ova|special)s?$', '', name)
        rtype = 'show' if mtype == 'tv' else 'movie'

        url = f'{self.baseUrl}/search/{rtype}?query={parse.quote(name.strip())}&genres=anime&extended=full'
        if year:
            url += '&years=%s' % year
        result = database.get_(utils.database_request_get, 4, url, headers=self.headers)
        if not result:
            name = name.replace('?', '')
            name = re.sub(r'\s\d+$', '', name)
            roman = r'(X{1,3}(IX|IV|V?I{0,3})|X{0,3}(IX|I?V|V?I{1,3}))$'
            name = re.sub(roman, '', name)
            if ':' in name:
                name = name.split(':')[0]
            url = f'{self.baseUrl}/search/{rtype}?query={parse.quote(name.strip())}&genres=anime&extended=full'
            result = database.get_(utils.database_request_get, 4, url, headers=self.headers)

        if not result:
            return

        jres = {}
        if len(result) > 1:
            for res in result:
                if res.get(rtype).get('title').lower == name.lower():
                    jres = res
                    break
        if not jres:
            jres = result[0]

        return jres.get(rtype)
