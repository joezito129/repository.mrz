import requests
import xbmc

from resources.lib.ui import utils, database, control
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase


class SimklWLF(WatchlistFlavorBase):
    _NAME = 'simkl'
    _URL = 'https://api.simkl.com'
    _TITLE = 'Simkl'
    _IMAGE = "simkl.png"

    # client_id = '5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b'    # Swag
    # client_id = "503b6b37476926a7a17ac86b95a81b245879955a7531e3e7d8913c0624796ea0"    # JZ
    client_id = "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8"  # Otaku

    def __headers(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f'Bearer {self.token}',
            "simkl-api-key": self.client_id
        }
        return headers

    def login(self) -> bool:
        import pyqrcode
        import os
        from resources.lib.windows.progress_dialog import Progress_dialog
        params = {
            'client_id': self.client_id,
        }

        r = requests.get(f'{self._URL}/oauth/pin', params=params, timeout=10)
        device_code = r.json()

        copied = control.copy2clip(device_code["user_code"])
        display_dialog = (f"{control.lang(30020).format(control.colorstr('https://simkl.com/pin'))}[CR]"
                          f"{control.lang(30021).format(control.colorstr(device_code['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"

        qr_path = os.path.join(control.dataPath, 'qr_code.png')
        qr = pyqrcode.create("https://simkl.com/pin")
        qr.png(qr_path, scale=20)
        config = {
            'heading': f'{control.ADDON_NAME}: SIMKL Auth',
            'text': display_dialog,
            'image': qr_path,
            'percent': 100
        }
        dialog = Progress_dialog('progress_dialog.xml', control.ADDON_PATH, config=config)
        dialog.show()

        inter = int(device_code['expires_in'] / device_code['interval'])
        for i in range(inter):
            if dialog.iscanceled():
                dialog.close()
                return False
            xbmc.sleep(device_code['interval'] * 1000)

            r = requests.get(f'{self._URL}/oauth/pin/{device_code["user_code"]}', params=params, timeout=10)
            r = r.json()
            if r['result'] == 'OK':
                self.token = r['access_token']
                control.setString('simkl.token', self.token)
                r = requests.post(f'{self._URL}/users/settings', headers=self.__headers(), timeout=10)
                if r.ok:
                    user = r.json()['user']
                    self.username = user['name']
                    control.setString('simkl.username', self.username)
                return True
            new_display_dialog = f"{display_dialog}[CR]Code Valid for {control.colorstr(device_code['expires_in'] - i * device_code['interval'])} Seconds"
            dialog.update(int((inter - i) / inter * 100), new_display_dialog)
        return False

    def __get_sort(self):
        sort_types = ['anime_title', 'list_updated_at', 'last_added', 'user_rating']
        return sort_types[int(self.sort)]

    def watchlist(self) -> list:
        statuses = [
            ("Next Up", "watching?next_up=true", 'nextup.png'),
            ("Currently Watching", "watching", 'watching.png'),
            ("Completed", "completed", 'completed.png'),
            ("On Hold", "hold", 'onhold.png'),
            # ("Dropped", "notinteresting"),
            ("Dropped", "dropped", 'dropped.png'),
            ("Plan to Watch", "plantowatch", 'plantowatch.png'),
            ("All Anime", "ALL", 'allanime.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    @staticmethod
    def action_statuses() -> list:
        return [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "hold"),
            ("Add to Dropped", "dropped"),
            # ("Add to Dropped", "notinteresting"),
            ("Add to Plan to Watch", "plantowatch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]

    def _base_watchlist_view(self, res):
        url = f'watchlist_status_type/{self._NAME}/{res[1]}'
        return [utils.allocate_item(res[0], url, True, False, [], f'{res[0].lower()}.png', {})]

    def get_watchlist_status(self, status, next_up, offset, page):
        results = self.get_all_items(status)
        if not results:
            return []

        all_results = map(self._base_watchlist_status_view, results['anime']) if next_up is None else map(self._base_next_up_view, results['anime'])
        all_results = list(all_results)
        sort_pref = self.__get_sort()

        if sort_pref == '2':  # anime_title
            all_results = sorted(all_results, key=lambda x: x['info']['title'])
        elif sort_pref == '0':  # list_updated_at
            all_results = sorted(all_results, key=lambda x: x['info']['last_watched'] or "0", reverse=True)
        elif sort_pref == '3':  # user_rating
            all_results = sorted(all_results, key=lambda x: x['info']['user_rating'] or 0, reverse=True)
        elif sort_pref == '1':  # last_added
            all_results.reverse()
        return all_results


    def _base_watchlist_status_view(self, res: dict):
        show_ids = res['show']['ids']

        if (mal_id := show_ids.get('mal')) is None:
            control.log(f"mal_id not found for simkl={show_ids['simkl']}", 'warning')

        dub = database.check_dub_status(mal_id) if control.getBool("divflavors.dubonly") or control.getBool("divflavors.showdub") else False
        kodi_meta = database.get_show_kodi_meta(mal_id)
        title = kodi_meta.get('ename', res['show']['title']) if self.title_lang == 'english' else res['show']['title']


        eps_watched = res["watched_episodes_count"]
        episodes = res["total_episodes_count"]

        info = {
            'title': title,
            'mediatype': 'tvshow',
            'year': res['show']['year'],
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating']
        }

        if episodes != 0 and eps_watched == episodes:
            info['playcount'] = 1

        image = f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_.jpg'

        base = {
            "name": f"{title} - {eps_watched}/{episodes}",
            "url": f'watchlist_to_ep/{mal_id}/{eps_watched}',
            "image": image,
            "fanart": image,
            "info": info
        }

        if episodes == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)


    def _base_next_up_view(self, res: dict):
        show_ids = res['show']['ids']

        mal_id = show_ids.get('mal')
        if mal_id is None:
            return None

        dub = database.check_dub_status(mal_id) if control.getBool("divflavors.dubonly") or control.getBool("divflavors.showdub") else False

        progress = res['watched_episodes_count']
        next_up = progress + 1
        episode_count = res["total_episodes_count"]

        if 0 < episode_count < next_up:
            return None

        base_title = res['show']['title']
        title = f"{base_title} - {next_up}/{episode_count}"

        info = {
            'episode': next_up,
            'title': title,
            'tvshowtitle': base_title,
            'last_watched': res['last_watched_at'],
            'user_rating': res['user_rating'],
            'mediatype': 'episode'
        }

        poster = image = f'https://wsrv.nl/?url=https://simkl.in/posters/{res["show"]["poster"]}_m.jpg'
        mal_id, next_up_meta = self._get_next_up_meta(mal_id, int(progress))
        if next_up_meta:
            if (title_ := next_up_meta['title']) is not None:
                info['title'] = f"{title} - {title_}"
            if (image_ := next_up_meta.get('image')) is not None:
                image = image_
            if (plot := next_up_meta.get('plot')) is not None:
                info['plot'] = plot
            if (aired := next_up_meta.get('aired')) is not None:
                info['aired'] = aired

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{mal_id}/{episode_count}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        if res["total_episodes_count"] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)

        if next_up_meta:
            base['url'] = f"play/{mal_id}/{next_up}"
            return utils.parse_view(base, False, True, dub)

        return utils.parse_view(base, True, False, dub)

    @staticmethod
    def get_watchlist_anime_entry(mal_id):
        # mal_id = self._get_mapping_id(mal_id, 'mal_id')
        # if not mal_id:
        #     return
        #
        # params = {
        #     'mal': mal_id
        # }
        # r = requests.post(f'{self._URL}/sync/watched', headers=self.__headers(), params=params)
        # result = r.json()
        # anime_entry = {
        #     'eps_watched': results['num_episodes_watched'],
        #     'status': results['status'],
        #     'score': results['score']
        # }
        return {}

    def save_completed(self):
        import json
        data = self.get_all_items('completed')
        completed = {}
        for dat in data['anime']:
            completed[str(dat['show']['ids']['mal'])] = dat['total_episodes_count']
        with open(control.completed_json, 'w', encoding='utf-8') as file:
            json.dump(completed, file)

    def get_all_items(self, status):
        # status values: watching, plantowatch, hold ,completed ,dropped (notinteresting for old api's).
        params = {
            'extended': 'full',
            # 'next_watch_info': 'yes'
        }
        r = requests.get(f'{self._URL}/sync/all-items/anime/{status}', headers=self.__headers(), params=params, timeout=10)
        return r.json()

    def update_list_status(self, mal_id, status):
        data = {
            "shows": [{
                "to": status,
                "ids": {
                    "mal": mal_id
                }
            }]
        }
        r = requests.post(f'{self._URL}/sync/add-to-list', headers=self.__headers(), json=data, timeout=10)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['shows']:
                if status == 'completed' and r.get('added', {}).get('shows', [{}])[0].get('to') == 'watching':
                    return 'watching'
                return True
        return False

    def update_num_episodes(self, mal_id, episode):
        data = {
            "shows": [{
                "ids": {
                    "mal": mal_id
                },
                "episodes": [{'number': i} for i in range(1, int(episode) + 1)]
            }]
        }
        r = requests.post(f'{self._URL}/sync/history', headers=self.__headers(), json=data, timeout=10)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False

    def update_score(self, mal_id, score):
        data = {
            "shows": [{
                'rating': score,
                "ids": {
                    "mal": mal_id,
                }
            }]
        }
        url = f"{self._URL}/sync/ratings"
        if score == 0:
            url = f"{url}/remove"

        r = requests.post(url, headers=self.__headers(), json=data, timeout=10)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False

    def delete_anime(self, mal_id):
        data = {
            "shows": [{
                "ids": {
                    "mal": mal_id
                }
            }]
        }
        r = requests.post(f"{self._URL}/sync/history/remove", headers=self.__headers(), json=data, timeout=10)
        if r.ok:
            r = r.json()
            if not r['not_found']['shows'] or not r['not_found']['movies']:
                return True
        return False
