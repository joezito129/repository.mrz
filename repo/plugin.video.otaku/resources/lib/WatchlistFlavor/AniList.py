import itertools
import pickle
import random
import requests


from resources.lib.ui import database, get_meta
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase


class AniListWLF(WatchlistFlavorBase):
    _URL = "https://graphql.anilist.co"
    _TITLE = "AniList"
    _NAME = "anilist"
    _IMAGE = "anilist.png"

    # Not login, but retrieveing userId for watchlist
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

    def watchlist(self):
        return self._process_watchlist_view("watchlist/%d", page=1)

    def _base_watchlist_view(self, res):
        base = {
            "name": res[0],
            "url": 'watchlist_status_type/%s/%s' % (self._NAME, res[1]),
            "image": '%s.png' % res[0].lower(),
            "info": '',
        }
        return self._parse_view(base)

    def _process_watchlist_view(self, base_plugin_url, page):
        all_results = map(self._base_watchlist_view, self.__anilist_statuses())
        all_results = list(itertools.chain(*all_results))
        return all_results

    @staticmethod
    def __anilist_statuses():
        statuses = [
            ("Next Up", "CURRENT?next_up=true"),
            ("Current", "CURRENT"),
            ("Rewatching", "REPEATING"),
            ("Plan to Watch", "PLANNING"),
            ("Paused", "PAUSED"),
            ("Completed", "COMPLETED"),
            ("Dropped", "DROPPED"),
        ]
        return statuses

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
        return self._process_status_view(query, variables, next_up, "watchlist/%d", page=1)

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

        anime_entry = {
            'eps_watched': results.get('progress'),
            'status': results['status'].title(),
            'score': results['score']
        }

        return anime_entry

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


    def _process_status_view(self, query, variables, next_up, base_plugin_url, page):
        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        results = r.json()
        lists = results['data']['MediaListCollection']['lists']
        try:
            entries = [mlist['entries'] for mlist in lists][0]
            get_meta.collect_meta(entries)
        except IndexError:
            entries = []
        if next_up:
            all_results = map(self._base_next_up_view, reversed(entries))
        else:
            all_results = map(self._base_watchlist_status_view, reversed(entries))


        all_results = [i for i in all_results if i is not None]
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_status_view(self, res):
        progress = res['progress']
        res = res['media']
        title = res['title'].get(self._title_lang) or res['title'].get('userPreferred')

        info = {
            'title': title,
            'genre': res.get('genres'),
            'status': res.get('status'),
            'mediatype': 'tvshow',
            'country': res.get('countryOfOrigin', ''),
            'studio': [x['node'].get('name') for x in res['studios'].get('edges')]
        }

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
            "url": "watchlist_to_ep/%d/%s/%d" % (res['id'], res.get('idMal', ''), progress),
            "image": res['coverImage']['extraLarge'],
            "poster": res['coverImage']['extraLarge'],
            "fanart": res['coverImage']['extraLarge'],
            "banner": res.get('bannerImage'),
            "info": info
        }

        show_meta = database.get_show_meta(res['id'])
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
            base['url'] = "watchlist_to_movie/%d/%s" % (res['id'], res.get('idMal', ''))
            base['info']['mediatype'] = 'movie'
            return self._parse_view(base, False)

        return self._parse_view(base)

    def _base_next_up_view(self, res):
        progress = res['progress']
        res = res['media']
        next_up = progress + 1
        episode_count = res['episodes'] if res['episodes'] is not None else 0
        base_title = res['title'].get(self._title_lang) or res['title'].get('userPreferred')
        title = '%s - %s/%s' % (base_title, next_up, episode_count)
        poster = image = res['coverImage']['extraLarge']
        plot = aired = None

        if (0 < episode_count < next_up) or (res['nextAiringEpisode'] and next_up == res['nextAiringEpisode']['episode']):
            return None

        anilist_id, next_up_meta = self._get_next_up_meta('', progress, res['id'])
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
            "url": "watchlist_to_ep/%d/%s/%d" % (res['id'], res.get('idMal', ''), progress),
            "image": image,
            "info": info,
            "fanart": image,
            "poster": poster,
        }

        show_meta = database.get_show_meta(res['id'])
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
            base['url'] = "play_movie/%d/%s" % (res['id'], res.get('idMal', ''))
            base['info']['mediatype'] = 'movie'
            return self._parse_view(base, False)
        if next_up_meta:
            base['url'] = url
            return self._parse_view(base, False)

        return self._parse_view(base)

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

    def __headers(self):
        headers = {
            'Authorization': 'Bearer ' + self._token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        return headers

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
        return r

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
        return r

    def delete_anime(self, anilist_id):
        list_id = self.get_watchlist_anime_info(anilist_id)['data']['Media']['mediaListEntry']['id']
        query = '''
        mutation ($id: Int) {
            DeleteMediaListEntry (id: $id) {
                deleted
            }
        }
        '''

        variables = {
            'id': int(list_id),
        }
        r = requests.post(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
        return r