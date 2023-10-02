import requests


class SyncUrl:
    BaseURL = 'https://find-my-anime.dtimur.de/api'

    def get_anime_data(self, anime_id, anime_id_provider):
        params = {
            'id': anime_id,
            'provider': anime_id_provider,
            'includeAdult': 'true'
        }
        r = requests.get(self.BaseURL, params=params)
        if r.ok:
            return r.json()
