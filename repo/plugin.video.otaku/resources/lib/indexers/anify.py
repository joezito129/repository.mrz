import requests

class ANIFYAPI:
    def __init__(self):
        self.baseUrl = 'https://api.anify.tv'
        # self.apikey = '\x65\x65\x36\x65\x61\x38\x32\x32\x36\x30\x36\x64\x32\x61\x64\x30\x35\x39\x64\x38\x38\x35\x64\x38\x61\x38\x34\x37\x62\x33\x37\x36'
        self.apikey = 'ee6ea822606d2ad059d885d8a847b376'


    def get_sources_json(self, anilist_id, episode, provider, lang=''):
        sources = []
        episodes = []

        params = {
            'apikey': self.apikey
        }
        r = requests.get(f'{self.baseUrl}/episodes/{anilist_id}', params=params)
        res = r.json() if r.ok else []
        for r in res:
            if r.get('providerId') == provider:
                episodes = r.get('episodes')
                break

        if episodes:
            episodes = sorted(episodes, key=lambda x: x.get('number'))
            if episodes[0].get('number') != 1:
                episode = episodes[0]['number'] - 1 + int(episode)
            eid = [(x.get('id'), x.get('hasDub')) for x in episodes if x.get('number') == int(episode)][0]
            if (lang == 'dub' and eid[1]) or lang == 'sub':
                params = {
                    'apikey': self.apikey,
                    'providerId': provider,
                    'watchId': eid[0],
                    'episode': episode,
                    'id': anilist_id,
                    'subType': lang
                }
                r = requests.get(f'{self.baseUrl}/sources', params)
                if r.ok:
                    sources = r.json()
        return sources


def process_anify(item, provider, title='', lang=0, subs=[], referer=''):
    if provider == '9anime':
        slink = item.get('url') + '|Referer={0}&User-Agent=iPad'.format(referer)
    else:
        slink = item.get('url')
    qual = item.get('quality')
    if qual.endswith('p'):
        qual = int(qual[:-1])
        if qual <= 480:
            quality = 'NA'
        elif qual <= 720:
            quality = '720p'
        elif qual <= 1080:
            quality = '1080p'
        else:
            quality = '4K'
    else:
        quality = 'EQ'

    source = {
        'release_title': title,
        'hash': slink,
        'type': 'direct',
        'quality': quality,
        'debrid_provider': '',
        'provider': provider,
        'size': 'NA',
        'info': ['DUB' if lang == 2 else 'SUB'],
        'lang': lang,
        'subs': subs
    }
    return [source]