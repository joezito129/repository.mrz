import xbmc
import requests
import random
import pickle

from functools import partial
from resources.lib.ui import BrowserBase, database, control, utils, get_meta
from resources.lib.ui.divide_flavors import div_flavor


class MalBrowser(BrowserBase.BrowserBase):
    _BASE_URL = "https://api.jikan.moe/v4"

    def __init__(self):
        self._TITLE_LANG = ['title', 'title_english'][control.getInt("titlelanguage")]
        self.perpage = control.getInt('interface.perpage.general.mal')
        self.format_in_type = ['tv', 'movie', 'tv_special', 'special', 'ova', 'ona', 'music'][control.getInt('contentformat.menu')] if control.getBool('contentformat.bool') else None
        self.adult = 'true' if not control.getBool('search.adult') else 'false'

    def process_mal_view(self, res, base_plugin_url, page) -> list:
        get_meta.collect_meta(res['data'])
        mapfunc = partial(self.base_mal_view, completed=self.open_completed())

        no_duplicate_res = []
        for x in res['data']:
            if x not in no_duplicate_res:
                no_duplicate_res.append(x)

        all_results = list(map(mapfunc, no_duplicate_res))
        hasNextPage = res['pagination']['has_next_page']
        all_results += self.handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def process_res(self, res):
        self.database_update_show(res)
        get_meta.collect_meta([res])
        return database.get_show(res['mal_id'])

    @staticmethod
    def get_season_year(period='current'):
        import datetime
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

    def get_anime(self, mal_id):
        res = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/anime/{mal_id}")
        if res.get('data') is None:
            control.notify(control.ADDON_NAME, res.get('message'))
            return None
        return self.process_res(res['data'])

    def get_recommendations(self, mal_id, page: int) -> list:
        params = {
            'page': page,
            'limit': self.perpage,
            'sfw': self.adult
        }
        recommendations = database.get_(self.get_base_res, 24, f'{self._BASE_URL}/anime/{mal_id}/recommendations', params)
        mapfunc = partial(self.recommendation_relation_view, completed=self.open_completed())
        all_results = list(map(mapfunc, recommendations['data']))
        return all_results

    def get_relations(self, mal_id) -> list:
        relations = database.get_(self.get_base_res, 24, f'{self._BASE_URL}/anime/{mal_id}/relations')
        relation_res = self.process_relations(relations)
        mapfunc = partial(self.base_mal_view, completed=self.open_completed())
        all_results = list(map(mapfunc, relation_res))
        return all_results

    def process_relations(self, relations: dict) -> list:
        relation_res = []
        count = 1
        for relation in relations['data']:
            for entry in relation['entry']:
                if entry['type'] == 'anime':
                    if count % 3 == 0:
                        xbmc.sleep(1900)
                    count += 1
                    if count > 50:
                        return relation_res
                    res = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/anime/{entry['mal_id']}")
                    if (res_data := res.get('data')) is not None:
                        res_data['relation'] = relation['relation']
                        relation_res.append(res_data)
                    elif res.get('status') == '429':
                        control.notify(control.ADDON_NAME, "Rate Limit Exceeded: Please wait 60 seconds before next request")
                        return relation_res
        return relation_res

    def get_search(self, query, page: int) -> list:
        params = {
            "q": query,
            "page": page,
            "limit": self.perpage,
            'sfw': self.adult
        }

        if self.format_in_type is not None:
            params['type'] = self.format_in_type

        search = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/anime", params)
        return self.process_mal_view(search, f"search?q={query}&page=%d", page)

    def get_airing_calendar(self, page: int) -> list:
        params = {
            'page': page,
            'limit': self.perpage,
            'sfw': self.adult
        }
        if self.format_in_type is not None:
            params['filter'] = self.format_in_type

        calendar = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/seasons/now", params)
        return self.process_calendar_view(calendar, f"airing_calendar?page=%d", page)

    def get_airing_anime(self, page: int) -> list:
        params = {
            'page': page,
            'limit': self.perpage,
            'sfw': self.adult
        }
        if self.format_in_type is not None:
            params['filter'] = self.format_in_type

        airing = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/seasons/now", params)
        return self.process_mal_view(airing, "airing_anime?page=%d", page)

    def get_upcoming_next_season(self, page: int) -> list:
        season, year = self.get_season_year('next')
        params = {
            'page': page,
            'limit': self.perpage,
            'sfw': self.adult
        }
        if self.format_in_type is not None:
            params['filter'] = self.format_in_type

        upcoming = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/seasons/{year}/{season}", params)
        return self.process_mal_view(upcoming, "upcoming_next_season?page=%d", page)

    def get_top_100_anime(self, page: int) -> list:
        params = {
            'page': page,
            'limit': self.perpage,
            'sfw': self.adult
        }
        if self.format_in_type is not None:
            params['type'] = self.format_in_type

        top_100_anime = database.get_(self.get_base_res, 24, f"{self._BASE_URL}/top/anime", params)
        return self.process_mal_view(top_100_anime, "top_100_anime?page=%d", page)

    @staticmethod
    def get_base_res(url, params=None):
        r = requests.get(url, params=params)
        return r.json()


    @div_flavor
    def recommendation_relation_view(self, res, completed=None, mal_dub=None) -> dict:
        if completed is None:
            completed = {}

        if (entry :=  res.get('entry')) is not None:
            res = entry

        mal_id = res['mal_id']
        title = res['title']

        if (relation := res.get('relation')) is not None:
            title += ' [I]%s[/I]' % control.colorstr(relation, 'limegreen')

        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'title': title,
            'mediatype': 'tvshow'
        }

        if completed.get(str(mal_id)) is not None:
            info['playcount'] = 1

        dub = bool(mal_dub is not None and mal_dub.get(str(mal_id)))
        try:
            image = res['images']['webp']['large_image_url']
        except KeyError:
            image = None

        base = {
            "name": title,
            "url": f'animes/{mal_id}/',
            "image": image,
            "poster": image,
            'fanart': image,
            "banner": image,
            "info": info
        }

        return utils.parse_view(base, True, False, dub)

    def get_genres(self) -> list:
        res = database.get_(self.get_base_res, 24, f'{self._BASE_URL}/genres/anime')

        genre = res['data']
        genres_list = []
        for x in genre:
            genres_list.append(x['name'])
        multiselect = control.multiselect_dialog(control.lang(30004), genres_list)
        if not multiselect:
            return []
        genre_display_list = []
        for selection in multiselect:
            if selection < len(genres_list):
                genre_display_list.append(str(genre[selection]['mal_id']))
        return self.genres_payload(genre_display_list, [], 1)

    def genres_payload(self, genre_list, tag_list, page: int) -> list:
        import ast
        if not isinstance(genre_list, list):
            genre_list = ast.literal_eval(genre_list)

        genre = ','.join(genre_list)
        params = {
            'page': page,
            'limit': self.perpage,
            'genres': genre,
            'sfw': self.adult,
            'order_by': 'popularity'
        }

        if self.format_in_type is not None:
            params['type'] = self.format_in_type

        genres = database.get_(self.get_base_res, 24, f'{self._BASE_URL}/anime', params)
        return self.process_mal_view(genres, f"genres/{genre_list}/{tag_list}?page=%d", page)

    @div_flavor
    def base_mal_view(self, res: dict, completed=None, mal_dub=None) -> dict:
        if completed is None:
            completed = {}

        mal_id = res['mal_id']

        if database.get_show(mal_id) is None:
            self.database_update_show(res)

        show_meta = database.get_show_meta(mal_id)
        try:
            kodi_meta= pickle.loads(show_meta['art'])
        except KeyError:
            kodi_meta = {}

        title = res[self._TITLE_LANG] or res['title']


        if (mpaa := res.get('rating')) == 'Rx - Hentai':
            title += ' - ' + control.colorstr("Adult", 'red')

        if (relation := res.get('relation')) is not None:
            title += ' [I]%s[/I]' % control.colorstr(relation, 'limegreen')

        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'title': title,
            'mpaa': mpaa,
            'mediatype': 'tvshow'
        }
        try:
            info['plot'] = res['synopsis']
        except KeyError:
            pass

        try:
            info['genre'] = [x['name'] for x in res['genres']]
        except KeyError:
            pass

        try:
            info['studio'] = [x['name'] for x in res['studios']]
        except KeyError:
            pass
        try:
            info['duration'] = self.duration_to_seconds(res['duration'])
        except KeyError:
            pass

        try:
            info['status'] = res['status']
        except KeyError:
            pass

        try:
            start_date = res['aired']['from']
            info['premiered'] = start_date[:10]
            info['year'] = res.get('year', int(start_date[:3]))
        except KeyError:
            pass

        try:
            info['rating'] = {'score': res['score'] or 0}
            try:
                info['rating']['votes'] = res['scored_by'] or 0
            except KeyError:
                pass
        except KeyError:
            pass

        try:
            info['trailer'] = f"plugin://plugin.video.youtube/play/?video_id={res['trailer']['youtube_id']}"
        except KeyError:
            pass

        if (broadcast := res.get('broadcast')) is not None:
            try:
                airingat = res['aired']['from']
                broadcast = broadcast
                day = broadcast['day']
                time_ = broadcast['time']
                timezone = broadcast['timezone']
                if day and time_ and airingat:
                    string_time = f"{airingat[:10]} at {time_}"
                    if timezone == 'Asia/Tokyo':
                        string_time += "+09:00"
                    time_format = utils.strp_time(string_time, '%Y-%m-%d at %H:%M%z')
                    if time_format is not None:
                        info['properties'] = {
                            "airingat": f"{time_format:%Y-%m-%d %H:%M:%S%z}",
                            "date": f"{time_format:%A[CR]%B %d, %Y}",
                            "time": f"{time_format:%I:%M %p}",
                        }
            except KeyError:
                pass

        if completed.get(str(mal_id)) is not None:
            info['playcount'] = 1

        dub = bool(mal_dub is not None and mal_dub.get(str(mal_id)))

        image = res['images']['webp']['large_image_url']
        base = {
            "name": title,
            "url": f'animes/{mal_id}/',
            "image": image,
            "poster": image,
            "banner": image,
            "info": info
        }
        try:
            base['fanart'] = kodi_meta['fanart']
        except KeyError:
            base['fanart'] = image

        if kodi_meta.get('thumb') is not None:
            base['landscape'] = random.choice(kodi_meta['thumb'])
        if kodi_meta.get('clearart'):
            base['clearart'] = random.choice(kodi_meta['clearart'])
        if kodi_meta.get('clearlogo') is not None:
            base['clearlogo'] = random.choice(kodi_meta['clearlogo'])

        if res.get('type') in ['Movie', 'ONA', 'Special', 'TV Special'] and res['episodes'] == 1:
            base['url'] = f'play_movie/{mal_id}/'
            base['info']['mediatype'] = 'movie'
            return utils.parse_view(base, False, True, dub)
        return utils.parse_view(base, True, False, dub)

    def database_update_show(self, res: dict) -> None:
        mal_id = res['mal_id']

        try:
            start_date = res['aired']['from']
        except KeyError:
            start_date = None

        title_userPreferred = res[self._TITLE_LANG] or res['title']
        name = res['title']
        ename = res['title_english'] or res['title']

        kodi_meta = {
            'name': name,
            'ename': ename,
            'synonyms': res['title_synonyms'],
            'title_userPreferred': title_userPreferred,
            'start_date': start_date,
            'episodes': res['episodes'],
            'poster': res['images']['webp']['large_image_url']
        }

        try:
            kodi_meta['plot'] = res['synopsis']
        except KeyError:
            pass

        try:
            kodi_meta['format'] = res['type']
        except KeyError:
            pass

        try:
            kodi_meta['status'] = res['status']
        except KeyError:
            pass

        try:
            kodi_meta['rating'] = {'score': res['score'] or 0}
            try:
                kodi_meta['rating']['votes'] = res['scored_by'] or 0
            except KeyError:
                pass
        except KeyError:
            pass

        database.update_show(mal_id, pickle.dumps(kodi_meta))

    def process_calendar_view(self, res: dict, base_plugin_url: str, page: int):
        all_results = []
        previous_page = page - 1
        if previous_page > 0:
            name = f"Prevous Page ({previous_page})"
            all_results.append(utils.allocate_item(name, base_plugin_url % previous_page, True, False, [], 'next.png', {'plot': name}, 'next.png'))
        anime_res = res['data']
        hasNextPage = res['pagination']['has_next_page']
        all_results += list(map(self.base_mal_view, anime_res))
        all_results += self.handle_paging(hasNextPage, base_plugin_url, page)
        return all_results