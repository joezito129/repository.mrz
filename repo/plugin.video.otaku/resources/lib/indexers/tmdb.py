import requests


class TMDBAPI:
    def __init__(self):
        self.apiKey = "6974ec27debf5cce1218136e2a36f64b"
        self.baseUrl = "https://api.themoviedb.org/3/"
        self.thumbPath = "https://image.tmdb.org/t/p/w500"
        self.backgroundPath = "https://image.tmdb.org/t/p/original"

    def getArt(self, meta_ids, mtype):
        art = {}
        mid = meta_ids.get('themoviedb') or meta_ids.get('tmdb')
        if mid is None:
            tvdb = meta_ids.get('thetvdb') or meta_ids.get('tvdb')
            if tvdb:
                params = {
                    'external_source': 'tvdb_id',
                    "api_key": self.apiKey
                }
                r = requests.get(f'{self.baseUrl}find/{tvdb}', params=params)
                if r.ok:
                    res = r.json()
                else:
                    res = {}
                res = res.get('tv_results')
                if res:
                    mid = res[0].get('id')

        if mid:
            params = {
                'include_image_language': 'en,ja,null'
            }
            r = requests.get(f'{self.baseUrl}{mtype[0:5]}/{mid}/images', params=params)
            res = r.json() if r.ok else {}

            if res:
                if res.get('backdrops'):
                    items = []
                    items2 = []
                    for item in res['backdrops']:
                        if item.get('file_path'):
                            items.append(self.backgroundPath + item['file_path'])
                            items.append(self.thumbPath + item['file_path'])
                    art.update({'fanart': items, 'thumb': items2})

                if res.get('logos'):

                    items = [self.backgroundPath + item["url"] for item in res['logos'] if item.get('url')]
                    # items = []
                    # for item in res['logos']:
                    #     if item.get('url'):
                    #         items.append(self.backgroundPath + item["url"])
                    art['clearart'] = items

        return art
