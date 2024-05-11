import time
import requests
import itertools
import pickle

from resources.lib.ui import utils, database, control
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor


class SimklWLF(WatchlistFlavorBase):
    _URL = 'https://api.simkl.com'
    _TITLE = 'Simkl'
    _NAME = 'simkl'
    _IMAGE = "simkl.png"

    # client_id = '5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b'    # Swag
    # client_id = "503b6b37476926a7a17ac86b95a81b245879955a7531e3e7d8913c0624796ea0"
    client_id = "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8"      # Otaku

    def __headers(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f'Bearer {self._token}',
            "simkl-api-key": self.client_id
        }
        return headers

    def login(self):
        params = {
            'client_id': self.client_id,
        }

        r = requests.get(f'{self._URL}/oauth/pin', params=params)
        device_code = r.json()

        control.copy2clip(device_code["user_code"])
        control.progressDialog.create('SIMKL Auth')
        control.progressDialog.update(
            100,
            control.lang(30100).format(control.colorString('https://simkl.com/pin')) + '[CR]'
            + control.lang(30101).format(control.colorString(device_code['user_code'])) + '[CR]'
            + control.lang(30102)
        )
        inter = int(device_code['expires_in'] / device_code['interval'])
        for i in range(inter):
            if control.progressDialog.iscanceled():
                control.progressDialog.close()
                return
            r = requests.get(f'{self._URL}/oauth/pin/{device_code["user_code"]}', params=params)
            r = r.json()
            if r['result'] == 'OK':
                self._token = r['access_token']
                login_data = {
                    'token': self._token
                }
                r = requests.post(f'{self._URL}/users/settings', headers=self.__headers())
                if r.ok:
                    user = r.json()['user']
                    login_data['username'] = user['name']
                return login_data
            control.progressDialog.update(int((inter - i) / inter * 100),
                control.lang(30100).format(control.colorString('https://simkl.com/pin')) + '[CR]'
                + control.lang(30101).format(control.colorString(device_code['user_code'])) + '[CR]'
                + control.lang(30102) + '[CR]'
                + f'Code Valid for {control.colorString(device_code["expires_in"] - i * device_code["interval"])} Seconds'
            )
            time.sleep(device_code['interval'])

    @staticmethod
    def _handle_paging(hasNextPage, base_url, page):
        if not hasNextPage:
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        offset = ''
        return utils.parse_view({'name': name, 'url': f'{base_url}/{offset}/{next_page}', 'image': 'next.png', 'info': {}, 'fanart': 'next.png'})

    def __get_sort(self):
        sort_types = {
            "Anime Title": "anime_title",
            "Last Updated": "list_updated_at",
            'Last Added': "last_added",
            "User Rating": "user_rating"
        }
        return sort_types[self._sort]

    def watchlist(self):
        statuses = [
            ("Next Up", "watching?next_up=true"),
            ("Currently Watching", "watching"),
            ("Completed", "completed"),
            ("On Hold", "hold"),
            # ("Dropped", "notinteresting"),
            ("Dropped", "dropped"),
            ("Plan to Watch", "plantowatch"),
            ("All Anime", "ALL")
        ]
        all_results = map(self._base_watchlist_view, statuses)
        all_results = list(itertools.chain(*all_results))
        return all_results

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "hold"),
            ("Add to Dropped", "dropped"),
            # ("Add to Dropped", "notinteresting"),
            ("Add to Plan to Watch", "plantowatch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def _base_watchlist_view(self, res):
        base = {
            "name": res[0],
            "url": 'watchlist_status_type/%s/%s' % (self._NAME, res[1]),
            "image": '%s.png' % res[0].lower(),
            "info": {}
        }
        return utils.parse_view(base)

    def get_watchlist_status(self, status, next_up, offset=0, page=1):
        results = self.get_all_items(status)
        if not results:
            return []

        if next_up:
            all_results = filter(lambda x: True if x else False, map(self._base_next_up_view, results['anime']))
        else:
            all_results = map(self._base_watchlist_status_view, results['anime'])

        all_results = list(itertools.chain(*all_results))
        sort_pref = self.__get_sort()

        if sort_pref == 'anime_title':
            all_results = sorted(all_results, key=lambda x: x['info']['title'])
        elif sort_pref == 'list_updated_at':
            all_results = sorted(all_results, key=lambda x: x['info']['last_watched'] or "0", reverse=True)
        elif sort_pref == 'user_rating':
            all_results = sorted(all_results, key=lambda x: x['info']['user_rating'] or 0, reverse=True)
        elif sort_pref == 'last_added':
            all_results.reverse()
        # all_results += self._handle_paging(results['paging'].get('next'), base_plugin_url, page)
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None, dubsub_filter=None):
        show_ids = res['show']['ids']

        mal_id = show_ids.get('mal', '')
        anilist_id = show_ids.get('anilist', '')
        kitsu_id = show_ids.get('kitsu', '')

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False
        show = database.get_show(anilist_id)
        if show:
            kodi_meta = pickle.loads(show['kodi_meta'])
        else:
            kodi_meta = {}

        title = res['show']['title']
        if self._title_lang == 'english':
            title = kodi_meta.get('ename') or kodi_meta.get('title_userPreferred') or title

        info = {
            'title': title,
            'mediatype': 'tvshow',
            'year': res['show']['year'],
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating']
        }

        if res["total_episodes_count"] != 0 and res["watched_episodes_count"] == res["total_episodes_count"]:
            info['playcount'] = 1

        base = {
            "name": '%s - %d/%d' % (title, res["watched_episodes_count"], res["total_episodes_count"]),
            "url": f'watchlist_to_ep/{anilist_id}/{mal_id}/{kitsu_id}/{res["watched_episodes_count"]}',
            "image": f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_m.jpg',
            "info": info
        }

        if res["total_episodes_count"] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}/{kitsu_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, dub=dub, dubsub_filter=dubsub_filter)
        return utils.parse_view(base, dub=dub, dubsub_filter=dubsub_filter)

    def _base_next_up_view(self, res):
        show_ids = res['show']['ids']

        mal_id = show_ids.get('mal', '')
        # anilist_id = show_ids.get('anilist', '')
        kitsu_id = show_ids.get('kitsu', '')

        progress = res['watched_episodes_count']
        next_up = progress + 1
        episode_count = res["total_episodes_count"]

        if 0 < episode_count < next_up:
            return None

        base_title = res['show']['title']

        title = '%s - %s/%s' % (base_title, next_up, episode_count)
        poster = image = f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_m.jpg'
        plot = aired = None
        anilist_id, next_up_meta, show = self._get_next_up_meta(mal_id, int(progress))
        if next_up_meta:
            kodi_meta = pickle.loads(show['kodi_meta'])
            if self._title_lang == 'english':
                base_title = kodi_meta['ename'] or kodi_meta['title_userPreferred']
                title = '%s - %s/%s' % (base_title, next_up, episode_count)
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
            'plot': plot,
            'mediatype': 'episode',
            'aired': aired,
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating']
        }

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{anilist_id}/{mal_id}/{kitsu_id}/{res["watched_episodes_count"]}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        if res["total_episodes_count"] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}/{kitsu_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False)

        if next_up_meta:
            base['url'] = 'play/%d/%d/' % (anilist_id, next_up)
            return utils.parse_view(base, False)

        return utils.parse_view(base)

    @staticmethod
    def get_watchlist_anime_entry(anilist_id):
        return {}
        # anime_entry = {
        #     'eps_watched': item_dict['progress'],
        #     'status': item_dict['status'],
        #     'score': item_dict['ratingTwenty']
        # }
        # return anime_entry

    def get_all_items(self, status):
        # status values: watching, plantowatch, hold ,completed ,dropped (notinteresting for old api's).
        params = {
            'extended': 'full',
            # 'next_watch_info': 'yes'
        }
        r = requests.get(f'{self._URL}/sync/all-items/anime/{status}', headers=self.__headers(), params=params)
        return r.json()

    def update_list_status(self, anilist_id, status):
        data = {
            "shows": [{
                "to": status,
                "ids": {
                    "anilist": anilist_id
                }
            }]
        }
        r = requests.post(f'{self._URL}/sync/add-to-list', headers=self.__headers(), json=data)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['shows']:
                if status == 'completed' and r.get('added', {}).get('shows', [{}])[0].get('to') == 'watching':
                    return 'watching'
                return True
        return False

    def update_num_episodes(self, anilist_id, episode):
        data = {
            "shows": [{
                "ids": {
                    "anilist": anilist_id
                },
                "episodes": [{'number': i} for i in range(1, int(episode) + 1)]
            }]
        }
        r = requests.post(f'{self._URL}/sync/history', headers=self.__headers(), json=data)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False

    def update_score(self, anilist_id, score):
        data = {
            "shows": [{
                'rating': score,
                "ids": {
                    "anilist": anilist_id,
                }
            }]
        }
        url = f'{self._URL}/sync/ratings'
        if score == 0:
            url = f'{url}/remove'

        r = requests.post(url, headers=self.__headers(), json=data)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False

    def delete_anime(self, anilist_id):
        data = {
            "shows": [{
                "ids": {
                    "anilist": anilist_id
                }
            }]
        }
        r = requests.post(f'{self._URL}/sync/history/remove', headers=self.__headers(), json=data)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False
