import requests
import datetime
import xbmc
import threading

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from resources.lib.ui import utils, database, control
from resources.lib import indexers, endpoint
from resources.packages import msgpack


class JikanAPI:
    def __init__(self):
        self.baseUrl = "https://api.jikan.moe/v4"
        self.S = requests.Session()

        self.kodi_meta = None
        self.eps_watched = 0
        self.episode_create_db = []
        self.episode_update_db = []

    def create_ep(self, icon):
        database.create_episode_batch(self.episode_create_db)
        control.notify("Jikanmoe",f"{self.kodi_meta.get('title_userPreferred') or self.kodi_meta['title']} Added to Database", icon=icon)

    def append_ep(self, icon):
        database.update_episode_kodi_meta_batch(self.episode_update_db)
        control.notify("Jikanmoe",f"{self.kodi_meta.get('title_userPreferred') or self.kodi_meta['title']} Added to Database", icon=icon)


    def get_anime_info(self, mal_id):
        r = requests.get(f'{self.baseUrl}/anime/{mal_id}', timeout=10)
        return r.json()['data']

    def get_episode_meta(self, mal_id):
        # url = f'{self.baseUrl}/anime/{mal_id}/videos/episodes'
        url = f'{self.baseUrl}/anime/{mal_id}/episodes'  # no pictures but can handle 100 per page
        r = self.S.get(url)
        res = r.json()
        res_data = res['data']
        for i in range(1, res['pagination']['last_visible_page']):
            if i > 50:
                break
            params = {'page': i + 1}
            if i % 3 == 0:
                xbmc.sleep(1900)
            r = requests.get(url, params=params, timeout=10)
            res = control.json_res(r)
            if r.status_code == 429:
                control.ok_dialog(control.ADDON_NAME, "Rate Limit Exceeded: Please wait 60 seconds before next request")
                return res_data
            res_data += res['data']
            if not res['pagination']['has_next_page']:
                break
        return res_data


    def parse_episode_view(self, res, mal_id, season, poster, fanart, update_time, dub_data, filler_data=None, episodes=None):
        episode = res['mal_id']
        url = f"{mal_id}/{episode}"
        try:
            title = res['title']
        except KeyError:
            title = f'Episode {episode}'

        image = res['images']['jpg']['image_url'] if res.get('images') is not None else poster

        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'title': title,
            'season': season,
            'episode': episode,
            'mediatype': 'episode'
        }

        try:
            info['tvshowtitle'] = self.kodi_meta['title_userPreferred']
        except KeyError:
            info['tvshowtitle'] = title

        if score := res.get('score'):
            info['rating'] = {'score': score}

        try:
            info['aired'] = res['aired'][:10]
        except (KeyError, TypeError):
            pass

        if self.eps_watched >= episode:
            info['playcount'] = 1

        if filler_data is not None and len(filler_data) >= episode:
            filler = filler_data[episode - 1]
        else:
            filler = None
        parsed = utils.allocate_item(title, f"play/{url}", False, True, [], image, info, fanart, poster)
        parsed_json = msgpack.dumps(parsed)
        if not episodes or len(episodes) <= episode or episode == 1:
            self.episode_create_db.append((mal_id, episode, update_time, season, parsed_json, filler, None, None))
        elif parsed_json != episodes[episode - 1]['kodi_meta']:
            self.episode_update_db.append((mal_id, episode, parsed_json))

        if control.getBool('interface.cleantitles') and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["episode"]}'
            parsed['info']['plot'] = None

        code = endpoint.get_second_label(info, dub_data, filler)
        if code is not None:
            parsed['info']['code'] = code
        return parsed

    def process_episode_view(self, mal_id: int, poster, fanart, dub_data, filler_data):
        update_time = datetime.date.today().isoformat()

        result = self.get_anime_info(mal_id)
        if not result:
            return []

        title_list = [name['title'] for name in result['titles']]

        season = utils.get_season(title_list, mal_id)
        result_ep = self.get_episode_meta(mal_id)
        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, update_time=update_time, dub_data=dub_data, filler_data=filler_data)
        all_results = sorted(list(map(mapfunc, result_ep)), key=lambda x: x['info']['episode'])
        if self.episode_create_db:
            db_thread = threading.Thread(target=self.create_ep, args=(poster,))
            db_thread.start()
        return all_results

    def append_episodes(self, mal_id, episodes, poster, fanart, dub_data=None):
        update_time, diff = indexers.get_diff(episodes[0])
        if diff > control.getInt('interface.check.updates'):
            result = self.get_episode_meta(mal_id)
            season = episodes[-1]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, update_time=update_time, dub_data=dub_data, filler_data=None, episodes=episodes)
            all_results = list(map(mapfunc2, result))
            if self.episode_update_db:
                db_thread = threading.Thread(target=self.append_ep, args=(poster,))
                db_thread.start()
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=self.eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id, show) -> list:
        self.kodi_meta = msgpack.loads(show['kodi_meta'])
        self.kodi_meta.update(msgpack.loads(show['art']))
        fanart = self.kodi_meta.get('fanart')
        poster = self.kodi_meta.get('poster')
        self.eps_watched = int(self.kodi_meta.get('eps_watched', 0))
        if control.getBool('watchlist.episode.data'):
            from resources.lib.WatchlistFlavor import WatchlistFlavor
            flavor = WatchlistFlavor.get_update_flavor()
            if flavor and flavor.flavor_name in control.enabled_watchlists():
                data = flavor.get_watchlist_anime_entry(mal_id)
                if data.get('eps_watched'):
                    if self.eps_watched != data['eps_watched']:
                        self.eps_watched = data['eps_watched']
                        self.kodi_meta['eps_watched'] = self.eps_watched
                        database.update_kodi_meta(mal_id, msgpack.dumps(self.kodi_meta))
        episodes = database.get_episode_list(mal_id)
        dub_data = indexers.process_dub(mal_id, self.kodi_meta['ename']) if control.getBool('jz.dub') else None
        if episodes:
            if self.kodi_meta['status'] != "Finished Airing":
                return self.append_episodes(mal_id, episodes, poster, fanart, dub_data)
            return indexers.process_episodes(episodes, self.eps_watched, dub_data)
        if self.kodi_meta['episodes'] is None or self.kodi_meta['episodes'] > 99:
            from resources.lib.endpoint import anime_filler
            filler_data = anime_filler.get_data(self.kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, dub_data, filler_data)

    def get_anime(self, filter_type, page):
        perpage = 25
        params = {
            "limit": perpage,
            "page": page,
            "filter": filter_type
        }
        r = requests.get(f'{self.baseUrl}/top/anime', params, timeout=10)
        return r.json()
