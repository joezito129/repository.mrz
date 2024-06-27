import ast
import datetime
import json
import pickle
import random
import requests

from functools import partial
from resources.lib.ui import database, get_meta, utils, control
from resources.lib.ui.divide_flavors import div_flavor


class AniListBrowser:
    _URL = "https://graphql.anilist.co"

    def __init__(self):
        self._TITLE_LANG = control.title_lang(int(control.getSetting("titlelanguage")))
        self.perpage = int(control.getSetting('interface.perpage.general'))

        if control.getSetting('contentformat.bool') == "true":
            formats = ['TV', 'MOVIE', 'TV_SHORT', 'SPECIAL', 'OVA', 'ONA', 'MUSIC']
            self.format_in_type = formats[int(control.getSetting('contentformat.menu'))]
        else:
            self.format_in_type = ''
        if control.getSetting('contentorigin.bool') == "true":
            countries = ['JP', 'KR', 'CN', 'TW']
            self.countryOfOrigin_type = countries[int(control.getSetting('contentorigin.menu'))]
        else:
            self.countryOfOrigin_type = ''

    @staticmethod
    def _handle_paging(hasNextPage, base_url, page):
        if not hasNextPage or (not control.is_addon_visible() and control.getSetting('widget.hide.nextpage') == 'true'):
            return []

        next_page = page + 1
        name = "Next Page (%d)" % next_page
        return [utils.allocate_item(name, base_url % next_page, True, False, 'next.png', {'plot': name}, 'next.png')]

    @staticmethod
    def get_season_year(period='current'):
        date = datetime.datetime.today()
        year = date.year
        month = date.month
        seasons = ['WINTER', 'SPRING', 'SUMMER', 'FALL']
        if period == "next":
            season = seasons[int((month - 1) / 3 + 1) % 4]
            if season == 'WINTER':
                year += 1
        else:
            season = seasons[int((month - 1) / 3)]
        return season, year

    def get_airing_anime(self, page=1):
        season, year = self.get_season_year('Aired')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            # 'status': "RELEASING",
            'sort': "TRENDING_DESC"
        }

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        airing = database.get_(self.get_base_res, 24, variables, page)
        return self.process_anilist_view(airing, "anilist_airing_anime/%d", page)

    def get_upcoming_next_season(self, page=1):
        season, year = self.get_season_year('next')
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'season': season,
            'year': f'{year}%',
            'sort': "TRENDING_DESC"
        }

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        upcoming = database.get_(self.get_base_res, 24, variables, page)
        return self.process_anilist_view(upcoming, "anilist_upcoming_next_season/%d", page)

    def get_top_100_anime(self, page=1):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'type': "ANIME",
            'sort': "SCORE_DESC"
        }

        if self.format_in_type:
            variables['format'] = self.format_in_type

        if self.countryOfOrigin_type:
            variables['countryOfOrigin'] = self.countryOfOrigin_type

        top_100_anime = database.get_(self.get_base_res, 24, variables, page)
        return self.process_anilist_view(top_100_anime, "anilist_top_100_anime/%d", page)

    def get_search(self, query, page=1):
        variables = {
            'page': page,
            'perpage': self.perpage,
            'search': query,
            'sort': "SEARCH_MATCH",
            'type': "ANIME"
        }
        search = self.get_search_res(variables, page)
        if control.bools.search_adult:
            variables['isAdult'] = True
            search_adult = self.get_search_res(variables, page)
            for i in search_adult["ANIME"]:
                i['title']['english'] = f'{i["title"]["english"]} - {control.colorString("Adult", "red")}'
            search['ANIME'] += search_adult['ANIME']
        return self.process_anilist_view(search, f"search/{query}/%d", page)

    def get_recommendations(self, anilist_id, page=1):
        variables = {
            'page': page,
            'perPage': self.perpage,
            'id': anilist_id
        }
        recommendations = database.get_(self.get_recommendations_res, 24, variables, page)
        return self.process_recommendations_view(recommendations, f'recommendations_next/{anilist_id}/%d', page)

    def get_relations(self, anilist_id):
        variables = {
            'id': anilist_id
        }
        relations = database.get_(self.get_relations_res, 24, variables)
        return self.process_relations_view(relations)

    def get_mal_to_anilist(self, mal_id):
        variables = {
            'idMal': mal_id,
            'type': "ANIME"
        }
        anilist_res = database.get_(self.anilist_res_with_mal_id, 24, variables)
        return self.process_res(anilist_res)

    def get_anilist(self, anilist_id):
        anilist_id = int(anilist_id)
        while anilist_id > 1_000_000_000:
            anilist_id = anilist_id - 1_000_000_000
        else:
            anilist_id_ = anilist_id
        variables = {
            'id': anilist_id,
            'type': "ANIME"
        }
        anilist_res = database.get_(self.get_anilist_res, 24, variables)
        anilist_res['id'] = anilist_id_
        return self.process_res(anilist_res)

    def get_base_res(self, variables, page=1):
        query = '''
        query (
            $page: Int=1,
            $perpage: Int=20
            $type: MediaType,
            $isAdult: Boolean = false,
            $format:[MediaFormat],
            $countryOfOrigin:CountryCode
            $season: MediaSeason,
            $year: String,
            $status: MediaStatus,
            $sort: [MediaSort] = [POPULARITY_DESC, SCORE_DESC]
        ) {
            Page (page: $page, perPage: $perpage) {
                pageInfo {
                    hasNextPage
                }
                ANIME: media (
                    format_in: $format,
                    type: $type,
                    season: $season,
                    startDate_like: $year,
                    sort: $sort,
                    status: $status
                    isAdult: $isAdult
                    countryOfOrigin: $countryOfOrigin
                ) {
                    id
                    idMal
                    title {
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
                    description
                    synonyms
                    format
                    episodes
                    status
                    genres
                    duration
                    countryOfOrigin
                    averageScore
                    trailer {
                        id
                        site
                    }
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
                }
            }
        }
        '''
        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()
        json_res = results['data']['Page']
        return json_res

    def get_search_res(self, variables, page=1):
        query = '''
        query (
            $page: Int=1,
            $perpage: Int=20
            $type: MediaType,
            $isAdult: Boolean = false,
            $search: String,
            $sort: [MediaSort] = [SCORE_DESC, POPULARITY_DESC]
        ) {
            Page (page: $page, perPage: $perpage) {
                pageInfo {
                    hasNextPage
                }
                ANIME: media (
                    type: $type,
                    search: $search,
                    sort: $sort,
                    isAdult: $isAdult
                ) {
                    id
                    idMal
                    title {
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
                    description
                    synonyms
                    format
                    episodes
                    status
                    genres
                    duration
                    countryOfOrigin
                    averageScore
                    trailer {
                        id
                        site
                    }
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
                }
            }
        }
        '''

        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()
        json_res = results['data']['Page']
        return json_res

    def get_recommendations_res(self, variables, page=1):
        query = '''
        query ($id: Int, $page: Int, $perpage: Int=20) {
          Media(id: $id, type: ANIME) {
            id
            recommendations(page: $page, perPage: $perpage, sort: [RATING_DESC, ID]) {
              pageInfo {
                hasNextPage
              }
              edges {
                node {
                  id
                  rating
                  mediaRecommendation {
                    id
                    title {
                      romaji
                      english
                    }
                    genres
                    averageScore
                    description(asHtml: false)
                    coverImage {
                      extraLarge
                    }
                    bannerImage
                    startDate {
                      year
                      month
                      day
                    }
                    format
                    episodes
                    duration
                    status
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
                    characters (perPage: 10) {
                      edges {
                        node {
                          name {
                            full
                            native
                            userPreferred
                          }
                        }
                        voiceActors(language: JAPANESE) {
                          id
                          name {
                            full
                            native
                            userPreferred
                          }
                          image {
                            large
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        '''

        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()
        json_res = results['data']['Media']['recommendations']
        return json_res

    def get_relations_res(self, variables):
        query = '''
        query ($id: Int) {
          Media(id: $id, type: ANIME) {
            relations {
              edges {
                relationType
                node {
                  id
                  title {
                    romaji
                    english
                  }
                  genres
                  averageScore
                  description(asHtml: false)
                  coverImage {
                    extraLarge
                  }
                  bannerImage
                  startDate {
                    year
                    month
                    day
                  }
                  format
                  episodes
                  duration
                  status
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
                  characters (perPage: 10) {
                    edges {
                      node {
                        name {
                          full
                          native
                          userPreferred
                        }
                      }
                      voiceActors(language: JAPANESE) {
                        id
                        name {
                          full
                          native
                          userPreferred
                        }
                        image {
                          large
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        '''

        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()
        json_res = results['data']['Media']['relations']
        return json_res

    def get_anilist_res(self, variables):
        query = '''
        query($id: Int, $type: MediaType){
            Media(id: $id, type: $type) {
                id
                idMal
                title {
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
                description
                synonyms
                format
                episodes
                status
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

        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()

        if "errors" in results.keys():
            return
        json_res = results['data']['Media']
        return json_res

    def anilist_res_with_mal_id(self, variables):
        query = '''
        query($idMal: Int, $type: MediaType){Media(idMal: $idMal, type: $type) {
            id
            idMal
            title {
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
            description
            synonyms
            format
            episodes
            status
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
            trailer {
                id
                site
            }
            studios {
                edges {
                    node {
                        name
                    }
                }
            }
            }
        }
        '''

        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()
        json_res = results['data']['Media']
        return json_res

    def process_anilist_view(self, json_res, base_plugin_url, page):
        hasNextPage = json_res['pageInfo']['hasNextPage']
        get_meta.collect_meta_(json_res['ANIME'])
        completed = self.open_completed()
        mapfunc = partial(self._base_anilist_view, completed=completed)
        all_results = list(map(mapfunc, json_res['ANIME']))
        all_results += self._handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def process_recommendations_view(self, json_res, base_plugin_url, page):
        hasNextPage = json_res['pageInfo']['hasNextPage']
        res = [edge['node']['mediaRecommendation'] for edge in json_res['edges'] if edge['node']['mediaRecommendation']]
        completed = self.open_completed()
        get_meta.collect_meta_(res)

        mapfunc = partial(self._base_anilist_view, completed=completed)
        all_results = list(map(mapfunc, res))
        all_results += self._handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def process_relations_view(self, json_res):
        res = []
        for edge in json_res['edges']:
            if edge['relationType'] != 'ADAPTATION':
                tnode = edge['node']
                tnode['relationType'] = edge['relationType']
                res.append(tnode)
        completed = self.open_completed()
        get_meta.collect_meta_(res)
        mapfunc = partial(self._base_anilist_view, completed=completed)
        all_results = list(map(mapfunc, res))
        return all_results

    def process_res(self, res):
        self.database_update_show(res)
        get_meta.collect_meta_([res])
        return database.get_show(str(res['id']))

    @div_flavor
    def _base_anilist_view(self, res, completed=None, mal_dub=None, dubsub_filter=None):
        if not completed:
            completed = {}
        anilist_id = res['id']
        mal_id = res.get('idMal', '')

        show = database.get_show(anilist_id)
        if not show:
            self.database_update_show(res)

        show_meta = database.get_show_meta(anilist_id)
        kodi_meta = pickle.loads(show_meta.get('art')) if show_meta else {}

        title = res['title'][self._TITLE_LANG]
        if not title:
            title = res['title']['romaji']

        if res.get('relationType'):
            title += ' [COLOR limegreen][I]{0}[/I][/COLOR]'.format(res['relationType'])

        desc = res.get('description')
        if desc:
            desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
            desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
            desc = desc.replace('<br>', '[CR]')
            desc = desc.replace('\n', '')

        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id)
            },
            'genre': res.get('genres'),
            'title': title,
            'plot': desc,
            'status': res.get('status'),
            'mediatype': 'tvshow',
            'country': res.get('countryOfOrigin', '')
        }

        if completed.get(str(anilist_id)):
            info['playcount'] = 1

        try:
            start_date = res.get('startDate')
            info['premiered'] = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
            info['year'] = start_date['year']
        except TypeError:
            pass

        try:
            cast = []
            for x in res['characters']['edges']:
                role = x['node']['name']['userPreferred']
                actor = x['voiceActors'][0]['name']['userPreferred']
                actor_hs = x['voiceActors'][0]['image']['large']
                cast.append({'name': actor, 'role': role, 'thumbnail': actor_hs})
            info['cast'] = cast
        except IndexError:
            pass

        info['studio'] = [x['node'].get('name') for x in res['studios']['edges']]

        try:
            info['rating'] = res.get('averageScore') / 10.0
        except TypeError:
            pass
        try:
            info['duration'] = res['duration'] * 60
        except TypeError:
            pass

        try:
            if res['trailer']['site'] == 'youtube':
                info['trailer'] = f"plugin://plugin.video.youtube/play/?video_id={res['trailer']['id']}"
            else:
                info['trailer'] = f"plugin://plugin.video.dailymotion_com/?url={res['trailer']['id']}&mode=playVideo"
        except (KeyError, TypeError):
            pass

        dub = True if mal_dub and mal_dub.get(str(res.get('idMal', -1))) else False

        base = {
            "name": title,
            "url": f'animes/{anilist_id}/{mal_id}',
            "image": res['coverImage']['extraLarge'],
            "poster": res['coverImage']['extraLarge'],
            "fanart": res['coverImage']['extraLarge'],
            "banner": res.get('bannerImage'),
            "info": info
        }

        if kodi_meta.get('fanart'):
            base['fanart'] = kodi_meta['fanart']
        if kodi_meta.get('thumb'):
            base['landscape'] = random.choice(kodi_meta['thumb'])
        if kodi_meta.get('clearart'):
            base['clearart'] = random.choice(kodi_meta['clearart'])
        if kodi_meta.get('clearlogo'):
            base['clearlogo'] = random.choice(kodi_meta['clearlogo'])

        if res['format'] in ['MOVIE', 'ONA'] and res['episodes'] == 1:
            base['url'] = f'play_movie/{anilist_id}/{mal_id}'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub=dub, dubsub_filter=dubsub_filter)
        return utils.parse_view(base, True, False, dub=dub, dubsub_filter=dubsub_filter)

    def database_update_show(self, res):
        anilist_id = res['id']
        mal_id = res.get('idMal', '')

        titles = self._get_titles(res)

        try:
            start_date = res['startDate']
            start_date = '{}-{:02}-{:02}'.format(start_date['year'], start_date['month'], start_date['day'])
        except TypeError:
            start_date = None

        title_userPreferred = res['title'][self._TITLE_LANG]
        if not title_userPreferred:
            title_userPreferred = res['title']['romaji']
        name = res['title']['romaji']
        ename = res['title']['english']

        kodi_meta = {
            'name': name,
            'ename': ename,
            'title_userPreferred': title_userPreferred,
            'start_date': start_date,
            'query': titles,
            'episodes': res['episodes'],
            'poster': res['coverImage']['extraLarge'],
            'status': res.get('status'),
            'format': res.get('format')
        }

        if res['format'] != 'TV':
            if res.get('averageScore'):
                kodi_meta['rating'] = res['averageScore'] / 10.0
            desc = res.get('description')
            if desc:
                desc = desc.replace('<i>', '[I]').replace('</i>', '[/I]')
                desc = desc.replace('<b>', '[B]').replace('</b>', '[/B]')
                desc = desc.replace('<br>', '[CR]')
                desc = desc.replace('\n', '')
                kodi_meta['plot'] = desc

        database.update_show(anilist_id, mal_id, pickle.dumps(kodi_meta))

    @staticmethod
    def _get_titles(res):
        name = res['title']['romaji']
        ename = res['title']['english']
        query_titles = '({0})|({1})'.format(name, ename)
        return query_titles

    def get_genres(self, genre_dialog):
        query = '''
        query {
            genres: GenreCollection,
            tags: MediaTagCollection {
                name
                isAdult
            }
        }
        '''

        r = requests.post(self._URL, json={'query': query})
        results = r.json()
        genres_list = results['data']['genres']

        del genres_list[6]

        tags_list = []
        try:
            tags = [x for x in results['tags'] if not x['isAdult']]
        except KeyError:
            tags = []
        for tag in tags:
            tags_list.append(tag['name'])

        genres_list += tags_list
        return self.select_genres(genre_dialog, genres_list)

    def select_genres(self, genre_dialog, genre_display_list):
        multiselect = genre_dialog(genre_display_list)
        if not multiselect:
            return []
        genre_list = []
        tag_list = []
        for selection in multiselect:
            if selection <= 17:
                genre_list.append(genre_display_list[selection])
                continue
            tag_list.append(genre_display_list[selection])
        return self.genres_payload(genre_list, tag_list)

    def genres_payload(self, genre_list, tag_list, page=1):
        query = '''
        query (
            $page: Int,
            $perpage: Int=20,
            $type: MediaType,
            $isAdult: Boolean = false,
            $includedGenres: [String],
            $includedTags: [String],
            $sort: [MediaSort] = [SCORE_DESC, POPULARITY_DESC]
        ) {
            Page (page: $page, perPage: $perpage) {
                pageInfo {
                    hasNextPage
                }
                ANIME: media (
                    type: $type,
                    genre_in: $includedGenres,
                    tag_in: $includedTags,
                    sort: $sort,
                    isAdult: $isAdult
                ) {
                    id
                    idMal
                    title {
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
                    description
                    synonyms
                    format
                    episodes
                    status
                    genres
                    duration
                    isAdult
                    countryOfOrigin
                    averageScore
                    trailer {
                        id
                        site
                    }
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
                }
            }
        }
        '''

        variables = {
            'page': page,
            'type': "ANIME"
        }
        if genre_list:
            variables["includedGenres"] = genre_list
        if tag_list:
            variables["includedTags"] = tag_list
        return self.process_genre_view(query, variables, f'anilist_genres/{genre_list}/{tag_list}/%d', page)

    def process_genre_view(self, query, variables, base_plugin_url, page):
        r = requests.post(self._URL, json={'query': query, 'variables': variables})
        results = r.json()
        anime_res = results['data']['Page']['ANIME']
        hasNextPage = results['data']['Page']['pageInfo']['hasNextPage']
        completed = self.open_completed()
        mapfunc = partial(self._base_anilist_view, completed=completed)
        get_meta.collect_meta_(anime_res)
        all_results = list(map(mapfunc, anime_res))
        all_results += self._handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def get_genres_page(self, genre_string, tag_string, page):
        return self.genres_payload(ast.literal_eval(genre_string), ast.literal_eval(tag_string), page)

    @staticmethod
    def open_completed():
        try:
            with open(control.completed_json) as file:
                completed = json.load(file)
        except FileNotFoundError:
            completed = {}
        return completed
    