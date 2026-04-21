import requests
import datetime
import threading

from resources.packages import msgpack
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from resources.lib.ui import database, control, utils
from resources.lib import indexers, endpoint


class ANIZIPAPI:
    def __init__(self):
        self.baseUrl = "https://api.ani.zip"

        self.kodi_meta = None
        self.eps_watched = 0
        self.episode_create_db = []
        self.episode_update_db = []

    def create_ep(self, icon):
        database.create_episode_batch(self.episode_create_db)
        control.notify("Anizip",f"{self.kodi_meta.get('title_userPreferred') or self.kodi_meta['title']} Added to Database", icon=icon)

    def append_ep(self, icon):
        database.update_episode_kodi_meta_batch(self.episode_update_db)
        control.notify("Anizip",f"{self.kodi_meta.get('title_userPreferred') or self.kodi_meta['title']} Added to Database", icon=icon)


    def get_anime_info(self, mal_id):
        params = {
            'mal_id': mal_id
        }
        r = requests.get(f'{self.baseUrl}/mappings', params=params, timeout=10)
        return r.json()

    def parse_episode_view(self, res, mal_id, season, poster, fanart, update_time, dub_data, filler_data, episodes=None):
        episode = int(res['episode'])

        url = f"{mal_id}/{episode}"

        title = res['title']['en'] or f'Episode {episode}'

        try:
            image = res['image']
        except KeyError:
            image = poster

        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'title': title,
            'season': season,
            'episode': episode,
            'mediatype': 'episode',
            'rating': {'score': float(res.get('rating', 0))}
        }
        try:
            info['tvshowtitle'] = self.kodi_meta['title_userPreferred']
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
        try:
            try:
                info['duration'] = res['runtime'] * 60
            except KeyError:
                info['duration'] = res['length'] * 60
        except KeyError:
            pass
        try:
            try:
                info['plot'] = res['overview']
            except KeyError:
                info['plot'] = res['summary']
        except KeyError:
            pass
        try:
            info['aired'] = res['airDate'][:10]
        except KeyError:
            pass

        if self.eps_watched >= episode:
            info['playcount'] = 1

        if filler_data is not None and len(filler_data) >= episode:
            filler = filler_data[episode - 1]
        else:
            filler = None
        anidb_ep_id = res.get('anidbEid')

        parsed = utils.allocate_item(title, f"play/{url}", False, True, [], image, info, fanart, poster)
        parsed_json = msgpack.dumps(parsed)
        if not episodes or len(episodes) <= episode or episode == 1:
            self.episode_create_db.append((mal_id, episode, update_time, season, parsed_json, filler, anidb_ep_id, None))
        elif parsed_json != episodes[episode - 1]['kodi_meta']:
            self.episode_update_db.append((mal_id, episode, parsed_json))

        if control.getBool('interface.cleantitles') and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["episode"]}'
            parsed['info']['plot'] = None

        code = endpoint.get_second_label(info, dub_data, filler)
        if code is not None:
            parsed['info']['code'] = code

        return parsed

    def process_episode_view(self, mal_id, poster, fanart, dub_data, filler_data):
        update_time = datetime.date.today().isoformat()

        result = self.get_anime_info(mal_id)
        if not result:
            return []
        result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
        if not result_ep:
            return []
        season = result_ep[0].get('seasonNumber', 1)

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, update_time=update_time, dub_data=dub_data, filler_data=filler_data)
        with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
            all_results = list(executor.map(mapfunc, result_ep))

        if self.episode_create_db:
            db_thread = threading.Thread(target=self.create_ep, args=(poster,))
            db_thread.start()
        return all_results

    def append_episodes(self, mal_id, episodes, poster, fanart, dub_data=None):
        update_time, diff = indexers.get_diff(episodes[0])
        if diff > control.getInt('interface.check.updates'):
            result = self.get_anime_info(mal_id)
            result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, update_time=update_time, dub_data=dub_data, filler_data=None, episodes=episodes)
            with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
                all_results = list(executor.map(mapfunc2, result_ep))
            if self.episode_update_db:
                db_thread = threading.Thread(target=self.append_ep, args=(poster,))
                db_thread.start()
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=self.eps_watched, dub_data=dub_data)
            with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
                all_results = list(executor.map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id: int, show) -> list:
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
