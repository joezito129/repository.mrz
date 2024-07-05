import re
import time
import requests

from resources.lib.ui import utils, control
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor


class MyAnimeListWLF(WatchlistFlavorBase):
    _URL = "https://api.myanimelist.net/v2"
    _TITLE = "MyAnimeList"
    _NAME = "mal"
    _IMAGE = "myanimelist.png"

    def __headers(self):
        headers = {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        return headers

    def login(self):
        from urllib import parse
        parsed = parse.urlparse(self._auth_var)
        params = dict(parse.parse_qsl(parsed.query))
        code = params.get('code')
        code_verifier = params.get('state')

        oauth_url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': 'a8d85a4106b259b8c9470011ce2f76bc',
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code'
        }
        r = requests.post(oauth_url, data=data)
        if not r.ok:
            return
        res = r.json()

        self._token = res['access_token']
        user = requests.get(f'{self._URL}/users/@me', headers=self.__headers(), params={'fields': 'name'})
        user = user.json()

        login_data = {
            'token': res['access_token'],
            'refresh': res['refresh_token'],
            'expiry': str(int(time.time()) + int(res['expires_in'])),
            'username': user['name']
        }
        return login_data

    @staticmethod
    def refresh_token():
        oauth_url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': 'a8d85a4106b259b8c9470011ce2f76bc',
            'grant_type': 'refresh_token',
            'refresh_token': control.getSetting('mal.refresh')
        }
        r = requests.post(oauth_url, data=data)
        res = r.json()
        control.setSetting('mal.token', res['access_token'])
        control.setSetting('mal.refresh', res['refresh_token'])
        control.setSetting('mal.expiry', str(int(time.time()) + int(res['expires_in'])))

    @staticmethod
    def handle_paging(hasnextpage, base_url, page):
        if not hasnextpage or not control.is_addon_visible() and control.getSetting('widget.hide.nextpage') == 'true':
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        offset = (re.compile("offset=(.+?)&").findall(hasnextpage))[0]
        return [utils.parse_view({'name': name, 'url': f'{base_url}/{offset}/{next_page}', 'image': 'next.png', 'info': {'plot': name}, 'fanart': 'next.png'}, True, False)]

    def __get_sort(self):
        sort_types = {
            "Anime Title": "anime_title",
            "Last Updated": "list_updated_at",
            "Anime Start Date": "anime_start_date",
            "List Score": "list_score"
        }
        return sort_types[self._sort]

    def watchlist(self):
        statuses = [
            ("Next Up", "watching?next_up=true", 'nextup.png'),
            ("Currently Watching", "watching", 'watching.png'),
            ("Completed", "completed", 'completed.png'),
            ("On Hold", "on_hold", 'onhold.png'),
            ("Dropped", "dropped", 'dropped.png'),
            ("Plan to Watch", "plan_to_watch", 'plantowatch.png'),
            ("All Anime", "", 'allanime.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, res[2]) for res in statuses]

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "on_hold"),
            ("Add to Dropped", "dropped"),
            ("Add to Plan to Watch", "plan_to_watch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def get_watchlist_status(self, status, next_up, offset=0, page=1):
        fields = [
            'alternative_titles',
            'list_status',
            'num_episodes',
            'synopsis',
            'mean',
            'rating',
            'genres',
            'studios',
            'start_date',
            'average_episode_duration',
            'media_type',
            'status'
        ]
        params = {
            "status": status,
            "sort": self.__get_sort(),
            "limit": int(control.getSetting('interface.perpage.watchlist')),
            "offset": offset,
            "fields": ','.join(fields),
            "nsfw": True
        }
        url = f'{self._URL}/users/@me/animelist'
        return self._process_status_view(url, params, next_up, f'watchlist_status_type_pages/mal/{status}', page)

    def _process_status_view(self, url, params, next_up, base_plugin_url, page):
        r = requests.get(url, headers=self.__headers(), params=params)
        results = r.json()
        if next_up:
            all_results = list(filter(lambda x: True if x else False, map(self._base_next_up_view, results['data'])))
        else:
            all_results = list(map(self._base_watchlist_status_view, results['data']))

        all_results += self.handle_paging(results['paging'].get('next'), base_plugin_url, page)
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None, dubsub_filter=None):
        mal_id = res['node']['id']
        anilist_id = ''

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        title = res['node'].get('title')
        if self._title_lang == 'english':
            title = res['node']['alternative_titles'].get('en') or title

        info = {
            'title': title,
            'plot': res['node']['synopsis'],
            'rating': res['node'].get('mean'),
            'duration': res['node']['average_episode_duration'],
            'genre': [x.get('name') for x in res['node']['genres']],
            'status': res['node']['status'],
            'mpaa': res['node'].get('rating'),
            'mediatype': 'tvshow',
            'studio': [x.get('name') for x in res['node']['studios']]
        }

        try:
            start_date = res['node']['start_date']
            info['premiered'] = start_date
            info['year'] = int(start_date[:4])
        except KeyError:
            pass

        if res['node']["num_episodes"] != 0 and res['list_status']["num_episodes_watched"] == res['node']["num_episodes"]:
            info['playcount'] = 1

        base = {
            "name": '%s - %d/%d' % (title, res['list_status']["num_episodes_watched"], res['node']["num_episodes"]),
            "url": f'watchlist_to_ep/{anilist_id}/{mal_id}/{res["list_status"]["num_episodes_watched"]}',
            "image": res['node']['main_picture'].get('large', res['node']['main_picture']['medium']),
            "info": info,
            'fanart': res['node']['main_picture']['medium']
        }

        if res['node']['media_type'] == 'movie' and res['node']["num_episodes"] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub=dub, dubsub_filter=dubsub_filter)
        return utils.parse_view(base, True, False, dub=dub, dubsub_filter=dubsub_filter)

    def _base_next_up_view(self, res):
        mal_id = res['node']['id']

        progress = res['list_status']["num_episodes_watched"]
        next_up = progress + 1
        episode_count = res['node']["num_episodes"]

        if 0 < episode_count < next_up:
            return

        base_title = res['node'].get('title')
        if self._title_lang == 'english':
            base_title = res['node']['alternative_titles'].get('en') or base_title

        title = f'{base_title} - {next_up}/{episode_count}'
        poster = image = res['node']['main_picture'].get('large', res['node']['main_picture']['medium'])
        plot = aired = None
        anilist_id, next_up_meta, show = self._get_next_up_meta(mal_id, int(progress))
        if next_up_meta:
            url = 'play/%d/%d/' % (anilist_id, next_up)
            if next_up_meta.get('title'):
                title = f'{title} - {next_up_meta["title"]}'
            if next_up_meta.get('image'):
                image = next_up_meta['image']
            plot = next_up_meta.get('plot')
            aired = next_up_meta.get('aired')

        info = {
            'episode': next_up,
            'title': title,
            'tvshowtitle': base_title,
            'duration': res['node']['average_episode_duration'],
            'plot': plot,
            'mediatype': 'episode',
            'aired': aired
        }

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{anilist_id}/{mal_id}/{res["list_status"]["num_episodes_watched"]}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        if res['node']['media_type'] == 'movie' and res['node']["num_episodes"] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True)

        if next_up_meta:
            base['url'] = url
            return utils.parse_view(base, False, True)

        return utils.parse_view(base, True, False)

    def get_watchlist_anime_entry(self, anilist_id):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return

        params = {
            "fields": 'my_list_status'
        }

        url = f'{self._URL}/anime/{mal_id}'
        r = requests.get(url, headers=self.__headers(), params=params)
        results = r.json().get('my_list_status')
        if not results:
            return {}
        anime_entry = {
            'eps_watched': results['num_episodes_watched'],
            'status': results['status'],
            'score': results['score']
        }
        return anime_entry

    def save_completed(self):
        import json
        from resources.lib.ui import database

        data = self.get_user_anime_list('completed')
        completed_ids = {}
        for dat in data:
            mal_id = dat['node']['id']
            try:
                anilist_id = database.get_mappings(mal_id, 'mal_id')['anilist_id']
                completed_ids[str(anilist_id)] = int(dat['node']['num_episodes'])
            except KeyError:
                pass

        with open(control.completed_json, 'w') as file:
            json.dump(completed_ids, file)

    def get_user_anime_list(self, status):
        fields = [
            'list_status',
            'num_episodes',
            'status'
        ]
        params = {
            'status': status,
            "nsfw": True,
            'limit': 1000,
            "fields": ','.join(fields)
        }
        r = requests.get(f'{self._URL}/users/@me/animelist', headers=self.__headers(), params=params)
        res = r.json()
        paging = res['paging']
        data = res['data']
        while paging.get('next'):
            r = requests.get(paging['next'], headers=self.__headers())
            res = r.json()
            paging = res['paging']
            data += res['data']
        return data

    def update_list_status(self, anilist_id, status):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return False
        data = {
            "status": status,
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.ok

    def update_num_episodes(self, anilist_id, episode):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return False
        data = {
            'num_watched_episodes': int(episode)
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.ok

    def update_score(self, anilist_id, score):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return False
        data = {
            "score": score,
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.ok

    def delete_anime(self, anilist_id):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return False
        r = requests.delete(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers())
        return r.ok
