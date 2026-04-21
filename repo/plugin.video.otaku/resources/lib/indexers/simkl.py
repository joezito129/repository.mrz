import requests
import datetime
import threading

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from resources.lib.ui import database, utils, control
from resources.lib import indexers, endpoint
from resources.packages import msgpack

class SIMKLAPI:
    def __init__(self):
        self.ClientID = "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8"  # Otaku API key
        # self.ClientID = "5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b" # Swag API Key
        # self.ClientID  = "503b6b37476926a7a17ac86b95a81b245879955a7531e3e7d8913c0624796ea0" # My API key

        self.baseUrl = "https://api.simkl.com"
        self.imagePath = "https://wsrv.nl/?url=https://simkl.in/episodes/%s_w.webp"
        # self.mal_id = None
        self.kodi_meta = None
        self.eps_watched = 0
        self.episode_create_db = []
        self.episode_update_db = []

    def create_ep(self, icon):
        database.create_episode_batch(self.episode_create_db)
        control.notify("Simkl",f"{self.kodi_meta.get('title_userPreferred') or self.kodi_meta['title']} Added to Database", icon=icon)

    def append_ep(self, icon):
        database.update_episode_kodi_meta_batch(self.episode_update_db)
        control.notify("Simkl",f"{self.kodi_meta.get('title_userPreferred') or self.kodi_meta['title']} Added to Database", icon=icon)

    def parse_episode_view(self, res: dict, mal_id: int, season: int, poster, fanart, update_time, dub_data, filler_data=None, episodes=None):
        episode = int(res['episode'])
        url = f"{mal_id}/{episode}"

        try:
            title = res['title']
        except KeyError:
            title = f'Episode {episode}'


        if img := res.get('img'):
            image = self.imagePath % img
        else:
            image  = poster

        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'title': title,
            'season': season,
            'episode': episode,
            'mediatype': 'episode',
        }

        try:
            info['tvshowtitle'] = self.kodi_meta['title_userPreferred']
        except KeyError:
            info['tvshowtitle'] = title

        try:
            info['plot'] = res['description']
        except KeyError:
            pass
        try:
            info['cast'] = self.kodi_meta['cast']
        except KeyError:
            pass
        try:
            info['genres'] = self.kodi_meta['genres']
        except KeyError:
            pass
        if self.eps_watched >= episode:
            info['playcount'] = 1

        try:
            info['aired'] = res['date'][:10]
        except KeyError:
            pass

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

    def process_episode_view(self, mal_id: int, poster, fanart, dub_data, filler_data) -> list:
        update_time = datetime.date.today().isoformat()

        result = self.get_anime_info(mal_id)
        if result is None:
            return []

        title_list = [name['name'] for name in result['alt_titles']]
        season = 1 if title_list is None else utils.get_season(title_list, mal_id)
        result_meta = self.get_episode_meta(mal_id)
        result_ep = [x for x in result_meta if x['type'] == 'episode']

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, update_time=update_time, dub_data=dub_data, filler_data=filler_data)
        with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
            all_results = list(executor.map(mapfunc, result_ep))

        if self.episode_create_db:
            db_thread = threading.Thread(target=self.create_ep, args=(poster,))
            db_thread.start()
        return all_results


    def append_episodes(self, mal_id, episodes, poster, fanart, dub_data=None)-> list:
        update_time, diff = indexers.get_diff(episodes[0])
        if diff >= control.getInt('interface.check.updates'):
            result_meta = self.get_episode_meta(mal_id)
            result_ep = [x for x in result_meta if x['type'] == 'episode']

            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, update_time=update_time, dub_data=dub_data, episodes=episodes)
            with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
                all_results = list(executor.map(mapfunc2, result_ep))

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
            if flavor is not None and flavor.flavor_name in control.enabled_watchlists():
                data = database.cache(flavor.get_watchlist_anime_entry, 1, False, mal_id)
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

    def get_anime_info(self, mal_id: int):
        show = database.get_show(mal_id)
        if not (simkl_id := show['simkl_id']):
            simkl_id = self.get_id('mal', mal_id)
            if simkl_id is None:
                return None
            database.update_mapping(mal_id, 'simkl_id', simkl_id)

        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        r = requests.get(f'{self.baseUrl}/anime/{simkl_id}', params=params, timeout=10)
        res = r.json() if r.ok else None
        return res

    def get_episode_meta(self, mal_id: int) -> dict:
        simkl_id = database.get_show_id(mal_id, 'simkl_id')
        if simkl_id is None:
            simkl_id = self.get_id('mal', mal_id)
            database.update_mapping(mal_id, 'simkl_id', simkl_id)
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        r = requests.get(f'{self.baseUrl}/anime/episodes/{simkl_id}', params=params, timeout=10)
        res = r.json()
        return res

    def get_id(self, send_id, anime_id):
        params = {
            send_id: anime_id,
            "client_id": self.ClientID,
        }
        r = requests.get(f'{self.baseUrl}/search/id', params=params, timeout=10)
        r = r.json()
        if r:
            anime_id = r[0]['ids']['simkl']
            return anime_id
        return None

    def get_mapping_ids(self, send_id, anime_id):
        # return_id = anidb, ann, mal, offjp, wikien, wikijp, instagram, imdb, tmdb, tw, tvdbslug, anilist, animeplanet, anisearch, kitsu, livechart, traktslug
        simkl_id = self.get_id(send_id, anime_id)
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        r = requests.get(f'{self.baseUrl}/anime/{simkl_id}', params=params, timeout=10)
        if r.ok:
            r = r.json()
            return r.get('ids')
        return None
