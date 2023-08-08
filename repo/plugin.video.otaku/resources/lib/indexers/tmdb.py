import requests

class TMDBAPI:
    def __init__(self):
        self.apiKey = "6974ec27debf5cce1218136e2a36f64b"
        self.baseUrl = "https://api.themoviedb.org/3/"
        self.thumbPath = "https://image.tmdb.org/t/p/w500"
        self.backgroundPath = "https://image.tmdb.org/t/p/original"
        self.request_response = None

    def get_request(self, url):
        if '?' not in url:
            url += "?"
        else:
            url += "&"

        if 'api_key' not in url:
            url += "api_key=%s" % self.apiKey
            url = self.baseUrl + url

        r = requests.get(url)
        if r.ok:
            response = r.json()
            self.request_response = response
            return response

        # if not response:
        #     response = client.request(url, verify=False)

    def getArt(self, meta_ids, mtype):
        art = {}
        mid = meta_ids.get('themoviedb') or meta_ids.get('tmdb')
        if mid is None:
            tvdb = meta_ids.get('thetvdb') or meta_ids.get('tvdb')
            if tvdb:
                url = 'find/{0}?external_source=tvdb_id'.format(tvdb)
                res = self.get_request(url)
                res = res.get('tv_results')
                if res:
                    mid = res[0].get('id')

        if mid:
            url = '{0}/{1}/images?include_image_language=en,ja,null'.format(mtype[0:5], mid)
            res = self.get_request(url)
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
                    items = []
                    for item in res['logos']:
                        if item.get('url'):
                            items.append(self.backgroundPath + item['url'])
                    art.update({'clearart': items})

        return art
