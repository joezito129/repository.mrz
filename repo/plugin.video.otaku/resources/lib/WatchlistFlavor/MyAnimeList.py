import json
import re
import time
import requests

from resources.lib.ui import utils, control
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor


class MyAnimeListWLF(WatchlistFlavorBase):
    _NAME = "mal"
    _URL = "https://api.myanimelist.net/v2"
    _TITLE = "MyAnimeList"
    _IMAGE = "myanimelist.png"


    def __headers(self):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        return headers

    def login(self) -> bool:
        from urllib import parse
        parsed = parse.urlparse(self.auth_var)
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
            return False
        res = r.json()
        self.token = res['access_token']
        self.refresh = res['refresh_token']
        control.setString('mal.token', self.token)
        control.setString('mal.refresh', self.refresh)
        control.setInt('mal.expiry', int(time.time()) + int(res['expires_in']))

        user = requests.get(f'{self._URL}/users/@me', headers=self.__headers(), params={'fields': 'name'})
        user = user.json()
        self.username = user['name']
        control.setString('mal.username', self.username)
        return True

    @staticmethod
    def refresh_token() -> None:
        oauth_url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': 'a8d85a4106b259b8c9470011ce2f76bc',
            'grant_type': 'refresh_token',
            'refresh_token': control.getString('mal.refresh')
        }
        r = requests.post(oauth_url, data=data)
        res = r.json()
        control.setString('mal.token', res['access_token'])
        control.setString('mal.refresh', res['refresh_token'])
        control.setInt('mal.expiry', int(time.time()) + int(res['expires_in']))

    @staticmethod
    def handle_paging(hasnextpage, base_url: str, page: int) -> list:
        if not hasnextpage or not control.is_addon_visible() and control.getBool('widget.hide.nextpage'):
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        offset = (re.compile("offset=(.+?)&").findall(hasnextpage))[0]
        return [utils.allocate_item(name, f'{base_url}/{offset}?page={next_page}', True, False, [], 'next.png', {'plot': name}, fanart='next.png')]

    def __get_sort(self):
        sort_types = ['list_score', 'list_updated_at', 'anime_start_date', 'anime_title']
        return sort_types[self.sort]

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
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    @staticmethod
    def action_statuses() -> list:
        return [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "on_hold"),
            ("Add to Dropped", "dropped"),
            ("Add to Plan to Watch", "plan_to_watch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]

    def get_watchlist_status(self, status, next_up, offset, page):
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
            "limit": control.getInt('interface.perpage.watchlist'),
            "offset": offset,
            "fields": ','.join(fields),
            "nsfw": True
        }
        url = f'{self._URL}/users/@me/animelist'
        return self._process_status_view(url, params, next_up, f'watchlist_status_type_pages/mal/{status}', page)

    def _process_status_view(self, url, params, next_up, base_plugin_url, page):
        r = requests.get(url, headers=self.__headers(), params=params)
        if r.ok:
            results = r.json()
            all_results = map(self._base_watchlist_status_view, results['data']) if next_up is None else map(self._base_next_up_view, results['data'])
            all_results = list(all_results)
            all_results += self.handle_paging(results['paging'].get('next'), base_plugin_url, page)
        else:
            results = json.loads(r.text)
            if results.get('error'):
                control.ok_dialog(control.ADDON_NAME, results['error'])
            all_results = []
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None):
        node = res['node']
        mal_id = node['id']
        dub = bool(mal_dub is not None and mal_dub.get(str(mal_id)))
        title = node['title']
        try:
            if self.title_lang == 'english':
                title = node['alternative_titles']['en'] or title
        except KeyError:
            pass

        eps_watched = res['list_status']["num_episodes_watched"]
        episodes = node["num_episodes"]
        image = node['main_picture'].get('large', node['main_picture']['medium'])

        info = {
            'title': title,
            'plot': node['synopsis'],
            'duration': node['average_episode_duration'],
            'status': node['status'],
            'mediatype': 'tvshow'
        }

        try:
            info['genre'] = [x['name'] for x in node['genres']]
        except KeyError:
            pass

        try:
            info['studio'] = [x['name'] for x in node['studios']]
        except KeyError:
            pass
        try:
            info['rating'] = {'score': node['mean']}
        except KeyError:
            pass

        try:
            info['mpaa'] = node['rating']
        except KeyError:
            pass

        try:
            info['premiered'] = node['start_date']
            info['year'] = int(node['start_date'][:4])
        except KeyError:
            pass

        if eps_watched == episodes and episodes != 0:
            info['playcount'] = 1

        base = {
            "name": f"{title} - {eps_watched}/{episodes}",
            "url": f'watchlist_to_ep/{mal_id}/{eps_watched}',
            "image": image,
            "info": info,
            'fanart': image
        }

        if node['media_type'] == 'movie' and episodes == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)


    @div_flavor
    def _base_next_up_view(self, res, mal_dub=None):
        node = res['node']
        mal_id = node['id']
        dub = bool(mal_dub is not None and mal_dub.get(str(mal_id)))

        eps_watched = res['list_status']["num_episodes_watched"]
        next_up = eps_watched + 1
        episodes = node["num_episodes"]

        if 0 < episodes < next_up:
            return None

        base_title = res['node']['alternative_titles'].get('en', node['title']) if self.title_lang == 'english' else node['title']

        title = f"{base_title} - {next_up}/{episodes}"
        poster = image = node['main_picture'].get('large', node['main_picture']['medium'])

        info = {
            'episode': next_up,
            'title': title,
            'tvshowtitle': base_title,
            'duration': node['average_episode_duration'],
            'mediatype': 'episode',
        }

        mal_id, next_up_meta, show = self._get_next_up_meta(mal_id, eps_watched)
        if next_up_meta is not None:
            if (title_ := next_up_meta.get('title')) is not None:
                info['title'] = f"{title} - {title_}"
            if (image_ := next_up_meta.get('image')) is not None:
                image = image_
            if (plot := next_up_meta.get('plot')) is not None:
                info['plot'] = plot
            if (aired := next_up_meta.get('aired')) is not None:
                info['aired'] = aired

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{mal_id}/{eps_watched}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        if res['node']['media_type'] == 'movie' and episodes == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)

        if next_up_meta:
            base['url'] = f"play/{mal_id}/{next_up}"
            return utils.parse_view(base, False, True, dub)

        return utils.parse_view(base, True, False, dub)

    def get_watchlist_anime_entry(self, mal_id):
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

        data = self.get_user_anime_list('completed')
        completed_ids = {}
        for dat in data:
            node = dat['node']
            mal_id = node['id']
            if (episodes := node.get('num_episodes')) is not None:
                completed_ids[str(mal_id)] = int(episodes)

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

    def update_list_status(self, mal_id, status):
        data = {
            "status": status,
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.ok

    def update_num_episodes(self, mal_id, episode):
        data = {
            'num_watched_episodes': int(episode)
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.ok

    def update_score(self, mal_id, score):
        data = {
            "score": score,
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.ok

    def delete_anime(self, mal_id):
        r = requests.delete(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers())
        return r.ok
