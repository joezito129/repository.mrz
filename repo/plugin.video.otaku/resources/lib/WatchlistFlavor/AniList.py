import itertools
import pickle
import random
import requests

from resources.lib.ui import database, utils, control
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase
from resources.lib.ui.divide_flavors import div_flavor


class AniListWLF(WatchlistFlavorBase):
    _URL = "https://graphql.anilist.co"
    _TITLE = "AniList"
    _NAME = "anilist"
    _IMAGE = "anilist.png"

    def __headers(self):
        headers = {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        return headers

    def login(self):
        query = '''
        query ($name: String) {
            User(name: $name) {
                id
                }
            }
        '''

        variables = {
            "name": self._username
        }

        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        results = r.json()
        if "errors" in results.keys():
            return
        userId = results['data']['User']['id']
        login_data = {
            'userid': str(userId)
        }
        return login_data

    def __get_sort(self):
        sort_types = {
            "Score": "SCORE",
            "Progress": "PROGRESS",
            "Last Updated": "UPDATED_TIME",
            "Last Added": "ADDED_TIME",
            "Romaji Title": "MEDIA_TITLE_ROMAJI_DESC",
            "English Title": "MEDIA_TITLE_ENGLISH_DESC"
        }
        return sort_types[self._sort]

    def watchlist(self):
        statuses = [
            ("Next Up", "CURRENT?next_up=true"),
            ("Current", "CURRENT"),
            ("Rewatching", "REPEATING"),
            ("Plan to Watch", "PLANNING"),
            ("Paused", "PAUSED"),
            ("Completed", "COMPLETED"),
            ("Dropped", "DROPPED")
        ]
        all_results = map(self._base_watchlist_view, statuses)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_view(self, res):
        base = {
            "name": res[0],
            "url": 'watchlist_status_type/%s/%s' % (self._NAME, res[1]),
            "image": f'{res[0].lower()}.png',
            "info": {}
        }
        return utils.parse_view(base)

    @staticmethod
    def action_statuses():
        actions = [
            ("Add to Current", "CURRENT"),
            ("Add to Rewatching", "REPEATING"),
            ("Add to Planning", "PLANNING"),
            ("Add to Paused", "PAUSED"),
            ("Add to Completed", "COMPLETED"),
            ("Add to Dropped", "DROPPED"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
        return actions

    def get_watchlist_status(self, status, next_up):
        query = '''
        query ($userId: Int, $userName: String, $status: MediaListStatus, $type: MediaType, $sort: [MediaListSort]) {
            MediaListCollection(userId: $userId, userName: $userName, status: $status, type: $type, sort: $sort) {
                lists {
                    entries {
                        ...mediaListEntry
                        }
                    }
                }
            }

        fragment mediaListEntry on MediaList {
            id
            mediaId
            status
            progress
            customLists
            media {
                id
                idMal
                title {
                    userPreferred,
                    romaji,
                    english
                }
                coverImage {
                    extraLarge
                }
                bannerImage
                startDate {
                    year,
                    month,
                    day
                }
                nextAiringEpisode {
                    episode,
                    airingAt
                }
                description
                synonyms
                format
                status
                episodes
                genres
                duration
                countryOfOrigin
                averageScore
                characters (
                    page: 1,
                    sort: ROLE,
                    perPage: 10,
                ) {
                    edges {
                        node {
                            name {
                                userPreferred
                            }
                        }
                        voiceActors (language: JAPANESE) {
                            name {
                                userPreferred
                            }
                            image {
                                large
                            }
                        }
                    }
                }
                studios {
                    edges {
                        node {
                            name
                        }
                    }
                }
                trailer {
                    id
                    site
                }
            }
        }
        '''

        variables = {
            'userId': int(self._user_id),
            'username': self._username,
            'status': status,
            'type': 'ANIME',
            'sort': self.__get_sort()
        }
        return self._process_status_view(query, variables, next_up)

    def _process_status_view(self, query, variables, next_up):
        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        results = r.json()
        lists = results['data']['MediaListCollection']['lists']
        entries = []
        for mlist in lists:
            entries += mlist['entries']

        all_results = map(self._base_next_up_view, reversed(entries)) if next_up else map(self._base_watchlist_status_view, reversed(entries))

        all_results = [i for i in all_results if i is not None]
        all_results = list(itertools.chain(*all_results))
        return all_results

    @div_flavor
    def _base_watchlist_status_view(self, res, mal_dub=None, dubsub_filter=None):
        progress = res['progress']
        res = res['media']

        anilist_id = res['id']
        mal_id = res.get('idMal', '')
        kitsu_id = ''

        dub = True if mal_dub and mal_dub.get(str(mal_id)) else False

        title = res['title'].get(self._title_lang) or res['title'].get('userPreferred')

        info = {
            'title': title,
            'genre': res.get('genres'),
            'status': res.get('status'),
            'mediatype': 'tvshow',
            'country': res.get('countryOfOrigin', ''),
            'studio': [x['node'].get('name') for x in res['studios'].get('edges')]
        }

        if res['episodes'] != 0 and progress == res['episodes']:
            info['playcount'] = 1

        try:
            info['duration'] = res.get('duration') * 60
        except TypeError:
            pass

        try:
            info['rating'] = res.get('averageScore') / 10.0
        except TypeError:
            pass

        desc = res.get('description')
        if desc:
            desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
            desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
            desc = desc.replace('<br>', '[CR]')
            desc = desc.replace('\n', '')
            info['plot'] = desc

        try:
            start_date = res.get('startDate')
            info['aired'] = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
        except TypeError:
            pass

        cast = []
        try:
            for x in res['characters']['edges']:
                role = x['node']['name']['userPreferred']
                actor = x['voiceActors'][0]['name']['userPreferred']
                actor_hs = x['voiceActors'][0]['image'].get('large')
                cast.append({'name': actor, 'role': role, 'thumbnail': actor_hs})
                info['cast'] = cast
        except IndexError:
            pass

        base = {
            "name": '%s - %d/%d' % (title, progress, res['episodes'] if res['episodes'] else 0),
            "url": f'watchlist_to_ep/{anilist_id}/{mal_id}/{kitsu_id}/{progress}',
            "image": res['coverImage']['extraLarge'],
            "poster": res['coverImage']['extraLarge'],
            "fanart": res['coverImage']['extraLarge'],
            "banner": res.get('bannerImage'),
            "info": info
        }

        show_meta = database.get_show_meta(anilist_id)
        if show_meta:
            art = pickle.loads(show_meta['art'])
            if art.get('fanart'):
                base['fanart'] = random.choice(art['fanart'])
            if art.get('thumb'):
                base['landscape'] = random.choice(art['thumb'])
            if art.get('clearart'):
                base['clearart'] = random.choice(art['clearart'])
            if art.get('clearlogo'):
                base['clearlogo'] = random.choice(art['clearlogo'])

        if res['format'] == 'MOVIE' and res['episodes'] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}/{kitsu_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, dub=dub, dubsub_filter=dubsub_filter)
        return utils.parse_view(base, dub=dub, dubsub_filter=dubsub_filter)

    def _base_next_up_view(self, res):
        progress = res['progress']
        res = res['media']

        anilist_id = res['id']
        mal_id = res.get('idMal', '')
        kitsu_id = ''

        next_up = progress + 1
        episode_count = res['episodes'] if res['episodes'] is not None else 0
        base_title = res['title'].get(self._title_lang) or res['title'].get('userPreferred')
        title = '%s - %s/%s' % (base_title, next_up, episode_count)
        poster = image = res['coverImage']['extraLarge']
        plot = aired = None

        if (0 < episode_count < next_up) or (res['nextAiringEpisode'] and next_up == res['nextAiringEpisode']['episode']):
            return None

        anilist_id, next_up_meta, show = self._get_next_up_meta('', progress, anilist_id)
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
            'tvshowtitle': res['title']['userPreferred'],
            'plot': plot,
            'genre': res.get('genres'),
            'mediatype': 'episode',
            'aired': aired
        }

        base = {
            "name": title,
            "url": f'watchlist_to_ep/{anilist_id}/{mal_id}/{kitsu_id}/{progress}',
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster
        }

        show_meta = database.get_show_meta(anilist_id)
        if show_meta:
            art = pickle.loads(show_meta['art'])
            if art.get('fanart'):
                base['fanart'] = random.choice(art['fanart'])
            if art.get('thumb'):
                base['landscape'] = random.choice(art['thumb'])
            if art.get('clearart'):
                base['clearart'] = random.choice(art['clearart'])
            if art.get('clearlogo'):
                base['clearlogo'] = random.choice(art['clearlogo'])

        if res['format'] == 'MOVIE' and res['episodes'] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}/{kitsu_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False)

        if next_up_meta:
            base['url'] = url
            return utils.parse_view(base, False)

        return utils.parse_view(base)

    def get_watchlist_anime_entry(self, anilist_id):
        query = '''
        query ($mediaId: Int) {
            Media (id: $mediaId) {
                id
                mediaListEntry {
                    id
                    mediaId
                    status
                    score
                    progress
                    user {
                        id
                        name
                    }
                }
            }
        }
        '''

        variables = {
            'mediaId': anilist_id
        }

        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        results = r.json()['data']['Media']['mediaListEntry']
        if not results:
            return {}
        anime_entry = {
            'eps_watched': results.get('progress'),
            'status': results['status'],
            'score': results['score']
        }
        return anime_entry

    def save_completed(self):
        import json

        data = self.get_user_anime_list('COMPLETED')
        completed = {}
        for dat in data:
            for entrie in dat['entries']:
                completed[str(entrie['media']['id'])] = int(entrie['media']['episodes'])
        with open(control.completed_json, 'w') as file:
            json.dump(completed, file)

    def get_user_anime_list(self, status):
        query = '''
        query ($userId: Int, $userName: String, $status: MediaListStatus, $type: MediaType, $sort: [MediaListSort]) {
            MediaListCollection(userId: $userId, userName: $userName, status: $status, type: $type, sort: $sort) {
                lists {
                    entries {
                        id
                        mediaId
                        progress
                        media {
                            id
                            idMal
                            episodes
                        }
                    }
                }
            }
        }
        '''

        variables = {
            'userId': int(self._user_id),
            'username': self._username,
            'status': status,
            'type': 'ANIME',
            'sort': self.__get_sort()
        }
        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        results = r.json()
        return results['data']['MediaListCollection']['lists']

    def get_watchlist_anime_info(self, anilist_id):
        query = '''
        query ($mediaId: Int) {
            Media (id: $mediaId) {
                id
                mediaListEntry {
                    id
                    mediaId
                    status
                    score
                    progress
                }
            }
        }
        '''

        variables = {
            'mediaId': anilist_id
        }

        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        results = r.json()
        return results

    def update_list_status(self, anilist_id, status):
        query = '''
        mutation ($mediaId: Int, $status: MediaListStatus) {
            SaveMediaListEntry (mediaId: $mediaId, status: $status) {
                id
                status
                }
            }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'status': status
        }

        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        return r.ok

    def update_num_episodes(self, anilist_id, episode):
        query = '''
        mutation ($mediaId: Int, $progress : Int, $status: MediaListStatus) {
            SaveMediaListEntry (mediaId: $mediaId, progress: $progress, status: $status) {
                id
                progress
                status
                }
            }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'progress': int(episode)
        }

        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        return r.ok

    def update_score(self, anilist_id, score):
        query = '''
        mutation ($mediaId: Int, $score: Float) {
            SaveMediaListEntry (mediaId: $mediaId, score: $score) {
                id
                score
                }
            }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'score': float(score)
        }

        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        return r.ok

    def delete_anime(self, anilist_id):
        media_entry = self.get_watchlist_anime_info(anilist_id)['data']['Media']['mediaListEntry']
        if media_entry:
            list_id = media_entry['id']
        else:
            return True
        query = '''
        mutation ($id: Int) {
            DeleteMediaListEntry (id: $id) {
                deleted
            }
        }
        '''

        variables = {
            'id': int(list_id)
        }
        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        return r.ok
