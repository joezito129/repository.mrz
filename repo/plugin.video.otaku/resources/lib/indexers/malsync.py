import requests


class MALSYNC:
    def __init__(self):
        self.baseUrl = 'https://api.malsync.moe'

    def get_slugs(self, anilist_id, site=''):
        slugs = []
        if site in ['9anime', 'Gogoanime', 'Zoro']:
            r = requests.get(f'{self.baseUrl}/mal/anime/anilist:{anilist_id}')
            resp = r.json()['Sites'].get(site)
            if resp:
                for key in resp.keys():
                    slugs.append(resp[key].get('url'))
        return slugs
