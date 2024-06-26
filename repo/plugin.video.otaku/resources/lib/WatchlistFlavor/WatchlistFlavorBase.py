import pickle
import random
import requests

from resources.lib.ui import control, database


class WatchlistFlavorBase:
    _URL = None
    _TITLE = None
    _NAME = None
    _IMAGE = None

    def __init__(self, auth_var=None, username=None, password=None, user_id=None, token=None, refresh=None, sort=None):
        self._auth_var = auth_var
        self._username = username
        self._password = password
        self._user_id = user_id
        self._token = token
        self._refresh = refresh
        self._sort = sort
        self._title_lang = control.title_lang(int(control.getSetting("titlelanguage")))

    @classmethod
    def name(cls):
        return cls._NAME

    @property
    def image(self):
        return self._IMAGE

    @property
    def title(self):
        return self._TITLE

    @property
    def url(self):
        return self._URL

    @property
    def flavor_name(self):
        return self._NAME

    @property
    def username(self):
        return self._username

    @staticmethod
    def _get_next_up_meta(mal_id, next_up, anilist_id=''):
        next_up_meta = {}
        show = database.get_show(anilist_id) if anilist_id else database.get_show_mal(mal_id)

        if show:
            anilist_id = show['anilist_id']
            show_meta = database.get_show_meta(anilist_id)

            if show_meta:
                art = pickle.loads(show_meta.get('art'))
                if art.get('fanart'):
                    next_up_meta['image'] = random.choice(art.get('fanart'))

            episodes = database.get_episode_list(show['anilist_id'])
            if episodes:
                try:
                    episode_meta = pickle.loads(episodes[next_up]['kodi_meta'])
                except IndexError:
                    episode_meta = None
                if episode_meta:
                    if control.getSetting('interface.cleantitles') == 'false':
                        next_up_meta['title'] = episode_meta['info']['title']
                        next_up_meta['plot'] = episode_meta['info']['plot']
                    else:
                        next_up_meta['title'] = f'Episode {episode_meta["info"]["episode"]}'
                    next_up_meta['image'] = episode_meta['image']['thumb']
                    next_up_meta['aired'] = episode_meta['info'].get('aired')

        return anilist_id, next_up_meta, show

    def _get_mapping_id(self, anilist_id, flavor):
        show = database.get_show(anilist_id)
        mapping_id = show[flavor] if show and show.get(flavor) else self._get_flavor_id(anilist_id, flavor)
        return mapping_id

    @staticmethod
    def _get_flavor_id(anilist_id, flavor):
        params = {
            'type': "anilist",
            "id": anilist_id
        }
        r = requests.get('https://armkai.vercel.app/api/search', params=params)
        res = r.json()
        flavor_id = res.get(flavor[:-3])
        database.add_mapping_id(anilist_id, flavor, flavor_id)
        return flavor_id
