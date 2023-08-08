import itertools
import re
import time
import requests

from resources.lib.ui import control
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase


class MyAnimeListWLF(WatchlistFlavorBase):
    _URL = "https://api.myanimelist.net/v2"
    _TITLE = "MyAnimeList"
    _NAME = "mal"
    _IMAGE = "myanimelist.png"


    def __headers(self):
        return {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }


    def login(self):
        from urllib import parse
        parsed = parse.urlparse(self._auth_var)
        params = dict(parse.parse_qsl(parsed.query))
        code = params['code']
        code_verifier = params['state']

        oauth_url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': 'a8d85a4106b259b8c9470011ce2f76bc',
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code'
        }
        r = requests.post(oauth_url, data=data)
        res = r.json()

        self._token = res['access_token']
        user = requests.get(f'{self._URL}/users/@me', headers=self.__headers(), params={'fields': 'name'})
        user = user.json()

        login_data = {
            'token': res['access_token'],
            'refresh': res['refresh_token'],
            'expiry': str(time.time() + int(res['expires_in'])),
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

    def _handle_paging(self, hasNextPage, base_url, page):
        if not hasNextPage:
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        offset = (re.compile("offset=(.+?)&").findall(hasNextPage))[0]
        return self._parse_view({'name': name, 'url': base_url % (offset, next_page), 'image': 'next.png', 'info': None, 'fanart': 'next.png'})

    def watchlist(self):
        return self._process_watchlist_view()

    def _base_watchlist_view(self, res):
        base = {
            "name": res[0],
            "url": 'watchlist_status_type/%s/%s' % (self._NAME, res[1]),
            "image": '%s.png' % res[0].lower(),
            "info": {}
        }

        return self._parse_view(base)

    def _process_watchlist_view(self):
        statuses = [
            ("Next Up", "watching?next_up=true"),
            ("Currently Watching", "watching"),
            ("Completed", "completed"),
            ("On Hold", "on_hold"),
            ("Dropped", "dropped"),
            ("Plan to Watch", "plan_to_watch"),
            ("All Anime", ""),
        ]
        all_results = map(self._base_watchlist_view, statuses)
        all_results = list(itertools.chain(*all_results))
        return all_results

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
            "limit": 100,
            "offset": offset,
            "fields": ','.join(fields)
        }

        url = f'{self._URL}/users/@me/animelist'
        return self._process_status_view(url, params, next_up, "watchlist_status_type_pages/mal//%s%%s/%%d" % status, page)

    def get_watchlist_anime_entry(self, anilist_id):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')

        if not mal_id:
            return

        params = {
            "fields": 'my_list_status'
        }

        url = f'{self._URL}/anime/{mal_id}'
        r = requests.get(url, headers=self.__headers(), params=params)
        results = r.json()['my_list_status']

        anime_entry = {
            'eps_watched': results['num_episodes_watched'],
            'status': results['status'].title(),
            'score': results['score']
        }
        return anime_entry

    def _process_status_view(self, url, params, next_up, base_plugin_url, page):
        results = requests.get(url, headers=self.__headers(), params=params)
        if results.ok:
            results = results.json()
        else:
            control.ok_dialog(control.ADDON_NAME, "Can't connect MyAnimeList 'API'")
            return []

        if next_up:
            all_results = filter(lambda x: True if x else False, map(self._base_next_up_view, results['data']))
        else:
            all_results = map(self._base_watchlist_status_view, results['data'])
        all_results = list(itertools.chain(*all_results))
        all_results += self._handle_paging(results['paging'].get('next'), base_plugin_url, page)
        return all_results

    def _base_watchlist_status_view(self, res):
        # show = database.get_show_mal(res['node']['id'])
        # anilist_id = show['anilist_id'] if show else ''
        title = res['node'].get('title')
        if self._title_lang == 'english':
            title = res['node']['alternative_titles'].get('en') or title

        anilist_id = ''
        info = {
            'title': title,
            'plot': res['node']['synopsis'],
            'rating': res['node'].get('mean'),
            'duration': res['node']['average_episode_duration'],
            'genre': [x.get('name') for x in res['node']['genres']],
            'status': res['node']['status'],
            'mpaa': res['node']['rating'],
            'mediatype': 'tvshow',
            'studio': [x.get('name') for x in res['node']['studios']]
        }

        try:
            start_date = res['node']['start_date']
            info['premiered'] = start_date
            info['year'] = int(start_date[:4])
        except KeyError:
            pass

        base = {
            "name": '%s - %d/%d' % (title, res['list_status']["num_episodes_watched"], res['node']["num_episodes"]),
            "url": "watchlist_to_ep/%s/%d/%d" % (anilist_id, res['node']['id'], res['list_status']["num_episodes_watched"]),
            "image": res['node']['main_picture'].get('large', res['node']['main_picture']['medium']),
            "info": info,
        }


        if res['node']['media_type'] == 'movie' and res['node']["num_episodes"] == 1:
            base['url'] = "play_movie/%s/%d" % (anilist_id, res['node']['id'])
            base['info']['mediatype'] = 'movie'
            return self._parse_view(base, False)
        return self._parse_view(base)

    def _base_next_up_view(self, res):
        mal_id = res['node']['id']
        progress = res['list_status']["num_episodes_watched"]
        next_up = progress + 1
        episode_count = res['node']["num_episodes"]
        if 0 < episode_count < next_up:
            return None

        base_title = res['node'].get('title')
        if self._title_lang == 'english':
            base_title = res['node']['alternative_titles'].get('en') or base_title

        title = '%s - %s/%s' % (base_title, next_up, episode_count)
        poster = image = res['node']['main_picture'].get('large', res['node']['main_picture']['medium'])
        plot = aired = None
        anilist_id, next_up_meta = self._get_next_up_meta(mal_id, int(progress))
        if next_up_meta:
            url = 'play/%d/%d/' % (anilist_id, next_up)
            if next_up_meta.get('title'):
                title = '%s - %s' % (title, next_up_meta['title'])
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
            "url": "watchlist_to_ep/%s/%d/%d" % (anilist_id, res['node']['id'], res['list_status']["num_episodes_watched"]),
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster,
        }

        if res['node']['media_type'] == 'movie' and res['node']["num_episodes"] == 1:
            base['url'] = "play_movie/%d/%d" % (anilist_id, res['node']['id'])
            base['info']['mediatype'] = 'movie'
            return self._parse_view(base, False)

        if next_up_meta:
            base['url'] = url
            return self._parse_view(base, False)

        return self._parse_view(base)

    def __get_sort(self):
        sort_types = {
            "Anime Title": "anime_title",
            "Last Updated": "list_updated_at",
            "Anime Start Date": "anime_start_date",
            "List Score": "list_score"
        }

        return sort_types[self._sort]

    def update_num_episodes(self, anilist_id, episode):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return
        data = {
            'num_watched_episodes': int(episode)
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.json() if r.ok else False

    def update_list_status(self, anilist_id, status):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return
        data = {
            "status": status,
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.json() if r.ok else False


    def update_score(self, anilist_id, score):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return
        data = {
            "score": score,
        }
        r = requests.put(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers(), data=data)
        return r.json() if r.ok else False

    def delete_anime(self, anilist_id):
        mal_id = self._get_mapping_id(anilist_id, 'mal_id')
        if not mal_id:
            return
        r = requests.delete(f'{self._URL}/anime/{mal_id}/my_list_status', headers=self.__headers())
        return r.json() if r.ok else False