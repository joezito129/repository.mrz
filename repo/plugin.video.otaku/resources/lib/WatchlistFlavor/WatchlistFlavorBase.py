import random
import requests

from resources.packages import msgpack
from resources.lib.ui import control, database


class WatchlistFlavorBase:
    _NAME = None
    _URL = None
    _TITLE = None
    _IMAGE = None

    def __init__(self, auth_var=None, username=None, token=None, refresh=None, sort=None):
        self.auth_var = auth_var
        self.username = username
        self.token = token
        self.refresh = refresh
        self.sort = sort
        self.title_lang = ["romaji", 'english'][control.getInt("titlelanguage")]

    @classmethod
    def name(cls):
        return cls._NAME

    @property
    def flavor_name(self):
        return self._NAME

    @property
    def url(self):
        return self._URL

    @property
    def title(self):
        return self._TITLE

    @property
    def image(self):
        return self._IMAGE

    @staticmethod
    def login():
        raise Exception('Should Not be called Directly')

    @staticmethod
    def get_watchlist_status(status, next_up, offset, page):
        raise Exception('Should Not be called Directly')

    @staticmethod
    def watchlist():
        raise Exception('Should Not be called Directly')

    @staticmethod
    def action_statuses():
        raise Exception('Should Not be called Directly')


    @staticmethod
    def _get_next_up_meta(mal_id, next_up: int):
        next_up_meta = {}
        show = database.get_show(mal_id)
        if show is not None:
            if art := msgpack.loads(show['art']):
                if (fanart := art.get('fanart')) is not None:
                    next_up_meta['image'] = random.choice(fanart)
            if (episode := database.get_episode(mal_id, next_up)) is not None:
                if episode_meta := msgpack.loads(episode['kodi_meta']):
                    if control.getBool('interface.cleantitles'):
                        next_up_meta['title'] = f'Episode {episode_meta["info"]["episode"]}'
                    else:
                        next_up_meta['title'] = episode_meta['info']['title']
                        next_up_meta['plot'] = episode_meta['info'].get('plot')
                    next_up_meta['image'] = episode_meta['image']['thumb']
                    next_up_meta['aired'] = episode_meta['info'].get('aired')
        return mal_id, next_up_meta

    def _get_mapping_id(self, mal_id: int, flavor: str):
        show = database.get_show(mal_id)
        mapping_id = show[flavor] if show is not None and show.get(flavor) else self.get_flavor_id_vercel(mal_id, flavor)
        if mapping_id is None:
            mapping_id = self.get_flavor_id_findmyanime(mal_id, flavor)
        return mapping_id


    @staticmethod
    def get_flavor_id_vercel(mal_id: int, flavor: str):
        params = {
            'type': "mal",
            "id": mal_id
        }
        r = requests.get('https://armkai.vercel.app/api/search', params=params, timeout=10)
        res = r.json()
        flavor_id = res.get(flavor[:-3])
        database.update_mapping(mal_id, flavor, flavor_id)
        return flavor_id

    @staticmethod
    def get_flavor_id_findmyanime(mal_id: int, flavor: str):
        if flavor == 'anilist_id':
            mapping = 'Anilist'
        elif flavor == 'mal_id':
            mapping = 'MyAnimeList'
        elif flavor == 'kitsu_id':
            mapping = 'Kitsu'
        else:
            mapping = None
        params = {
            'id': mal_id,
            'providor': 'MyAnimeList'
        }
        r = requests.get('https://find-my-anime.dtimur.de/api', params=params, timeout=10).json()
        flavor_id = r[0]['providerMapping'][mapping]
        database.update_mapping(mal_id, flavor, flavor_id)
        return flavor_id

    @staticmethod
    def get_flavor_id_simkl(mal_id: int, flavor: str):
        from resources.lib.indexers.simkl import SIMKLAPI
        ids = SIMKLAPI().get_mapping_ids(flavor, mal_id)
        flavor_id = ids[flavor]
        database.update_mapping(mal_id, flavor, flavor_id)
        return flavor_id
