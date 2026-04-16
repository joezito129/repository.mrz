from concurrent.futures.thread import ThreadPoolExecutor

import requests
import pickle
import datetime

from functools import partial
from resources.lib.ui import database, control
from resources.lib import indexers


class ANIZIPAPI:
    def __init__(self):
        self.kodi_meta = None
        self.baseUrl = "https://api.ani.zip"

    def get_anime_info(self, mal_id):
        params = {
            'mal_id': mal_id
        }
        r = requests.get(f'{self.baseUrl}/mappings', params=params)
        return r.json()

    def parse_episode_view(self, res, mal_id, season, poster, fanart, eps_watched, update_time, dub_data, filler_data, episodes=None):
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
        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        if filler_data is not None and len(filler_data) >= episode:
            filler = filler_data[episode - 1]
        else:
            filler = None

        anidb_ep_id = res.get('anidbEid')
        parsed = indexers.update_database(mal_id, update_time, res, url, image, info, season, episode, episodes, title, fanart, poster, dub_data, filler, anidb_ep_id)
        return parsed

    def process_episode_view(self, mal_id, poster, fanart, eps_watched, dub_data, filler_data=None):
        update_time = datetime.date.today().isoformat()

        result = self.get_anime_info(mal_id)
        if not result:
            return []
        result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
        if not result_ep:
            return []
        season = result_ep[0].get('seasonNumber', 1)

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, dub_data=dub_data, filler_data=filler_data)
        with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
            all_results = list(executor.map(mapfunc, result_ep))

        try:
            text = f"{self.kodi_meta['title_userPreferred']} Added to Database"
        except KeyError:
            text = f"{self.kodi_meta['title']} Added to Database"
        control.notify("Anizip", text, icon=poster)
        return all_results

    def append_episodes(self, mal_id, episodes, eps_watched, poster, fanart, dub_data=None):
        update_time, diff = indexers.get_diff(episodes[0])
        if diff > control.getInt('interface.check.updates'):
            result = self.get_anime_info(mal_id)
            result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, dub_data=dub_data, filler_data=None, episodes=episodes)
            with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
                all_results = list(executor.map(mapfunc2, result_ep))
            try:
                text = f"{self.kodi_meta['title_userPreferred']} Appended to Database"
            except KeyError:
                text = f"{self.kodi_meta['title']} Appended to Database"
            control.notify("ANIZIP Appended", text, icon=poster)
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            with ThreadPoolExecutor(max_workers=control.max_threads) as executor:
                all_results = list(executor.map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id: int, show_meta) -> list:
        self.kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        self.kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = self.kodi_meta.get('fanart')
        poster = self.kodi_meta.get('poster')
        eps_watched = int(self.kodi_meta.get('eps_watched', 0))

        if control.getBool('watchlist.episode.data'):
            from resources.lib.WatchlistFlavor import WatchlistFlavor
            flavor = WatchlistFlavor.get_update_flavor()
            if flavor and flavor.flavor_name in control.enabled_watchlists():
                data = flavor.get_watchlist_anime_entry(mal_id)
                if data.get('eps_watched'):
                    eps_watched = data['eps_watched']
                    self.kodi_meta['eps_watched'] = eps_watched
                    database.update_kodi_meta(mal_id, self.kodi_meta)
        episodes = database.get_episode_list(mal_id)
        dub_data = indexers.process_dub(mal_id, self.kodi_meta['ename']) if control.getBool('jz.dub') else None

        if episodes:
            if self.kodi_meta['status'] != "Finished Airing":
                return self.append_episodes(mal_id, episodes, eps_watched, poster, fanart, dub_data)
            return indexers.process_episodes(episodes, eps_watched, dub_data)
        if self.kodi_meta['episodes'] is None or self.kodi_meta['episodes'] > 99:
            from resources.lib.endpoint import anime_filler
            filler_data = anime_filler.get_data(self.kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, eps_watched, dub_data, filler_data)
