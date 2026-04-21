import time
import requests

from resources.lib.ui import control, database, utils
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.indexers.simkl import SIMKLAPI
from urllib import parse


class KitsuWLF(WatchlistFlavorBase):
    _NAME = "kitsu"
    _URL = "https://kitsu.io/api"
    _TITLE = "Kitsu"
    _IMAGE = "kitsu.png"

    user_id = control.getInt('kitsu.userid')
    password = control.getString("kitsu.password")
    mapping = None

    def __headers(self):
        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': f'Bearer {self.token}'
        }
        return headers

    def login(self) -> bool:
        params = {
            "grant_type": "password",
            "username": self.auth_var,
            "password": self.password
        }
        resp = requests.post(f'{self._URL}/oauth/token', params=params, timeout=10)

        if not resp.ok:
            return False

        data = resp.json()
        self.token = data['access_token']
        self.refresh = data['refresh_token']

        control.setString('kitsu.token', self.token)
        control.setString('kitsu.refresh', self.refresh)
        control.setInt('kitsu.expiry', int(time.time()) + int(data['expires_in']))

        resp2 = requests.get(f'{self._URL}/edge/users', headers=self.__headers(), params={'filter[self]': True}, timeout=10)
        data2 = resp2.json()["data"][0]


        self.username = data2["attributes"]["name"]
        self.user_id = int(data2['id'])

        control.setString('kitsu.username', self.username)
        control.setInt('kitsu.userid', self.user_id)
        return True

    def refresh_token(self) -> None:
        params = {
            "grant_type": "refresh_token",
            "refresh_token": control.getString('kitsu.refresh')
        }
        resp = requests.post(f'{self._URL}/oauth/token', params=params, timeout=10)

        if not resp:
            return None

        data = resp.json()
        control.setString('kitsu.token', data['access_token'])
        control.setString('kitsu.refresh', data['refresh_token'])
        control.setInt('kitsu.expiry', int(time.time() + int(data['expires_in'])))
        return None

    @staticmethod
    def handle_paging(hasnextpage, base_url, page):
        if not hasnextpage or not control.is_addon_visible() and control.getBool('widget.hide.nextpage'):
            return []
        next_page = page + 1
        name = f"Next Page ({next_page})"
        parsed = parse.urlparse(hasnextpage)
        offset = parse.parse_qs(parsed.query)['page[offset]'][0]
        return [utils.allocate_item(name, f'{base_url}/{offset}?page={next_page}', True, False, [], 'next.png', {'plot': name}, fanart='next.png')]

    def __get_sort(self):
        sort_types = ['-progressed_at', '-progress', f"anime.titles.{self.__get_title_lang()}"]
        return sort_types[int(self.sort)]

    def __get_title_lang(self):
        title_langs = {
            "english": "en",
            "romaji": "en_jp",
        }
        return title_langs[self.title_lang]

    def watchlist(self):
        statuses = [
            ("Next Up", "current?next_up=true", 'nextup.png'),
            ("Current", "current", 'watching.png'),
            ("Want to Watch", "planned", 'plantowatch.png'),
            ("Completed", "completed", 'completed.png'),
            ("On Hold", "on_hold", 'onhold.png'),
            ("Dropped", "dropped", 'dropped.png')
        ]
        return [utils.allocate_item(res[0], f'watchlist_status_type/{self._NAME}/{res[1]}', True, False, [], res[2], {}) for res in statuses]

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to Current", "current"),
            ("Add to Want to Watch", "planned"),
            ("Add to On Hold", "on_hold"),
            ("Add to Completed", "completed"),
            ("Add to Dropped", "dropped"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def get_watchlist_status(self, status, next_up, offset, page):
        url = f'{self._URL}/edge/library-entries'
        params = {
            "fields[anime]": "titles,canonicalTitle,posterImage,episodeCount,synopsis,episodeLength,subtype,averageRating,ageRating,youtubeVideoId",
            "filter[user_id]": self.user_id,
            "filter[kind]": "anime",
            "filter[status]": status,
            "include": "anime,anime.mappings,anime.mappings.item",
            "page[limit]": control.getInt('interface.perpage.watchlist'),
            "page[offset]": offset,
            "sort": self.__get_sort()
        }
        return self.process_watchlist_view(url, params, next_up, f'watchlist_status_type_pages/kitsu/{status}', page)

    def process_watchlist_view(self, url, params, next_up, base_plugin_url, page) -> list:
        result = requests.get(url, headers=self.__headers(), params=params, timeout=10)
        result = result.json()
        _list = result["data"]

        if result.get('included') is None:
            return []

        el = result["included"][:len(_list)]
        self.mapping = [x for x in result['included'] if x['type'] == 'mappings']

        all_results = map(self._base_watchlist_view, _list, el) if next_up is None else map(self._base_next_up_view, _list, el)
        all_results = list(all_results)
        all_results += self.handle_paging(result['links'].get('next'), base_plugin_url, page)
        return all_results


    def _base_watchlist_view(self, res, eres):
        kitsu_id = eres['id']
        if (mal_id := self.mapping_mal(kitsu_id)) is None:
            control.log(f"mal_id not found for kitsu_id={kitsu_id}", 'warning')

        dub = database.check_dub_status(mal_id) if control.getBool("divflavors.dubonly") or control.getBool("divflavors.showdub") else False

        title = eres["attributes"]["titles"].get(self.__get_title_lang(), eres["attributes"]['canonicalTitle'])

        info = {
            'title': title,
            'mpaa': eres['attributes']['ageRating'],
            'trailer': f"plugin://plugin.video.youtube/play/?video_id={eres['attributes']['youtubeVideoId']}",
            'mediatype': 'tvshow'
        }

        progress = res["attributes"]["progress"]
        if (episodes := eres['attributes']['episodeCount']) != 0 and progress == episodes:
            info['playcount'] = 1

        if (plot := eres['attributes'].get('synopsis')) is not None:
            info['plot'] = plot

        if (duration := eres['attributes']['episodeLength']) is not None:
            info['duration'] = duration * 60

        if (rating := eres['attributes']['averageRating']) is not None:
            info['rating'] = {'score': float(rating) / 10}

        poster_image = eres["attributes"]['posterImage']
        base = {
            "name": f"{title} - {progress}/{episodes}",
            "url": f'watchlist_to_ep/{mal_id}/{progress}',
            "image": poster_image.get('large', poster_image['original']),
            "info": info
        }

        if eres['attributes']['subtype'] == 'movie' and episodes == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)


    def _base_next_up_view(self, res, eres):
        kitsu_id = eres['id']
        mal_id = self.mapping_mal(kitsu_id)
        dub = database.check_dub_status(mal_id) if control.getBool("divflavors.dubonly") or control.getBool("divflavors.showdub") else False

        progress = res["attributes"]['progress']
        next_up = progress + 1
        anime_title = eres["attributes"]["titles"].get(self.__get_title_lang(), eres["attributes"]['canonicalTitle'])
        if (episodes:= eres["attributes"]['episodeCount']) is None:
            episodes = 0
        title = f"{anime_title} - {next_up}/{episodes}"
        poster = image = eres["attributes"]['posterImage'].get('large', eres["attributes"]['posterImage']['original'])
        info = {
            'episode': next_up,
            'title': title,
            'tvshowtitle': anime_title,
            'mediatype': 'episode'
        }
        mal_id, next_up_meta = self._get_next_up_meta(mal_id, progress)
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
            "name": info['title'],
            "url": f'watchlist_to_ep/{mal_id}/{res["attributes"]["progress"]}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        if next_up_meta:
            base['url'] = f"play/{mal_id}/{next_up}"
            return utils.parse_view(base, False, True, dub)

        if eres['attributes']['subtype'] == 'movie' and eres['attributes']['episodeCount'] == 1:
            base['url'] = f"play_movie/{mal_id}/"
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)

        return utils.parse_view(base, True, False, dub)

    def mapping_mal(self, kitsu_id):
        mal_id = None
        for i in self.mapping:
            if i['attributes']['externalSite'] == 'myanimelist/anime':
                if i['relationships']['item']['data']['id'] == kitsu_id:
                    mal_id = i['attributes']['externalId']
                    break
        if mal_id is not None:
            ids = SIMKLAPI().get_mapping_ids('kitsu', kitsu_id)
            mal_id = ids['mal']
            database.update_mapping(mal_id, 'mal_id', mal_id)
        return mal_id

    def get_library_entries(self, kitsu_id):
        params = {
            "filter[user_id]": self.user_id,
            "filter[anime_id]": kitsu_id
        }
        r = requests.get(f'{self._URL}/edge/library-entries', headers=self.__headers(), params=params, timeout=10)
        r = r.json()
        return r

    def get_watchlist_anime_entry(self, mal_id):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if kitsu_id is None:
            return {}

        result = self.get_library_entries(kitsu_id)
        try:
            item_dict = result['data'][0]['attributes']
        except IndexError:
            return {}
        anime_entry = {
            'eps_watched': item_dict['progress'],
            'status': item_dict['status'],
            'score': item_dict['ratingTwenty']
        }
        return anime_entry

    def save_completed(self):
        import json
        data = self.get_user_anime_list('completed')
        completed = {}
        for dat in data:
            mal_id = self.mapping_mal(dat['relationships']['anime']['data']['id'])
            completed[str(mal_id)] = dat['attributes']['progress']

        with open(control.completed_json, 'w', encoding='utf-8') as file:
            json.dump(completed, file)

    def get_user_anime_list(self, status):
        url = f'{self._URL}/edge/library-entries'
        params = {
            "filter[user_id]": self.user_id,
            "filter[kind]": "anime",
            "filter[status]": status,
            "page[limit]": "500",
            "include": "anime,anime.mappings,anime.mappings.item",
        }
        r = requests.get(url, headers=self.__headers(), params=params, timeout=10)
        res = r.json()
        paging = res['links']
        data = res['data']
        while paging.get('next'):
            r = requests.get(paging['next'], headers=self.__headers(), timeout=10)
            res = r.json()
            paging = res['links']
            data += res['data']
        return data

    def update_list_status(self, mal_id, status):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        r = self.get_library_entries(kitsu_id)
        if not r['data']:
            data = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'status': status
                    },
                    "relationships": {
                        "user": {
                            "data": {
                                "id": self.user_id,
                                "type": "users"
                            }
                        },
                        "anime": {
                            "data": {
                                "id": kitsu_id,
                                "type": "anime"
                            }
                        }
                    }
                }
            }
            r = requests.post(f'{self._URL}/edge/library-entries', headers=self.__headers(), json=data, timeout=10)
            return r.ok
        animeid = int(r['data'][0]['id'])
        data = {
            'data': {
                'id': animeid,
                'type': 'libraryEntries',
                'attributes': {
                    'status': status
                }
            }
        }
        r = requests.patch(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), json=data, timeout=10)
        return r.ok

    def update_num_episodes(self, mal_id, episode):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        r = self.get_library_entries(kitsu_id)
        if not r['data']:
            data = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'status': 'current',
                        'progress': int(episode)
                    },
                    "relationships": {
                        "user": {
                            "data": {
                                "id": self.user_id,
                                "type": "users"
                            }
                        },
                        "anime": {
                            "data": {
                                "id": kitsu_id,
                                "type": "anime"
                            }
                        }
                    }
                }
            }
            r = requests.post(f'{self._URL}/edge/library-entries', headers=self.__headers(), json=data, timeout=10)
            return r.ok

        animeid = int(r['data'][0]['id'])

        data = {
            'data': {
                'id': animeid,
                'type': 'libraryEntries',
                'attributes': {
                    'status': 'current',
                    'progress': int(episode)}
            }
        }
        r = requests.patch(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), json=data, timeout=10)
        return r.ok

    def update_score(self, mal_id, score):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if not kitsu_id:
            return False

        score = int(score / 10 * 20)
        if score == 0:
            score = None
        r = self.get_library_entries(kitsu_id)
        if not r['data']:
            data = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'ratingTwenty': score
                    },
                    "relationships": {
                        "user": {
                            "data": {
                                "id": self.user_id,
                                "type": "users"
                            }
                        },
                        "anime": {
                            "data": {
                                "id": kitsu_id,
                                "type": "anime"
                            }
                        }
                    }
                }
            }
            r = requests.post(f'{self._URL}/edge/library-entries', headers=self.__headers(), json=data, timeout=10)
            return r.ok

        animeid = int(r['data'][0]['id'])
        data = {
            'data': {
                'id': animeid,
                'type': 'libraryEntries',
                'attributes': {
                    'ratingTwenty': score
                }
            }
        }
        r = requests.patch(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), json=data, timeout=10)
        return r.ok

    def delete_anime(self, mal_id):
        kitsu_id = self._get_mapping_id(mal_id, 'kitsu_id')
        if kitsu_id is None:
            return False

        r = self.get_library_entries(kitsu_id)
        data = r['data']
        if data:
            animeid = data[0]['id']
        else:
            return True

        r = requests.delete(f'{self._URL}/edge/library-entries/{animeid}', headers=self.__headers(), timeout=10)
        return r.ok
