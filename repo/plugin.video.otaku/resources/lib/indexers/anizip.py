import requests
import pickle
import datetime

from functools import partial
from resources.lib.ui import database, control
from resources.lib import indexers


class ANIZIPAPI:
    def __init__(self):
        self.baseUrl = "https://api.ani.zip"

    def get_anime_info(self, mal_id):
        params = {
            'mal_id': mal_id
        }
        r = requests.get(f'{self.baseUrl}/mappings', params=params)
        return r.json()

    @staticmethod
    def parse_episode_view(res, mal_id, season, poster, fanart, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None):
        episode = int(res['episode'])

        url = f"{mal_id}/{episode}"

        title = res['title']['en']
        if not title:
            title = f'Episode {episode}'

        image = res['image'] if res.get('image') else poster

        info = {
            'UniqueIDs': {'mal_id': str(mal_id)},
            'plot': res.get('overview', res.get('summary')),
            'title': title,
            'season': season,
            'episode': episode,
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode',
            'duration': res.get('runtime', res.get('length', 0)) * 60,
            'rating': {'score': float(res.get('rating', 0))}
        }

        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            info['aired'] = res['airDate'][:10]
        except KeyError:
            pass

        try:
            filler = filler_data[episode - 1]
        except (IndexError, TypeError):
            filler = ''

        anidb_ep_id = res.get('anidbEid')

        parsed = indexers.update_database(mal_id, update_time, res, url, image, info, season, episode, episodes, title, fanart, poster, dub_data, filler, anidb_ep_id)
        return parsed

    def process_episode_view(self, mal_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data=None):
        update_time = datetime.date.today().isoformat()

        result = self.get_anime_info(mal_id)
        if not result:
            return []
        result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
        if not result_ep:
            return []
        season = result_ep[0].get('seasonNumber', 1)

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
        all_results = list(map(mapfunc, result_ep))

        control.notify("Anizip", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, mal_id, episodes, eps_watched, poster, fanart, tvshowtitle, dub_data=None):
        update_time, diff = indexers.get_diff(episodes[0])
        if diff > int(control.getSetting('interface.check.updates')):
            result = self.get_anime_info(mal_id)
            result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=None, episodes=episodes)
            all_results = list(map(mapfunc2, result_ep))
            control.notify("ANIZIP Appended", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id, show_meta) -> list:
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        tvshowtitle = kodi_meta['title_userPreferred']
        eps_watched = kodi_meta.get('eps_watched')

        if control.getBool('watchlist.episode.data'):
            from resources.lib.WatchlistFlavor import WatchlistFlavor
            flavor = WatchlistFlavor.get_update_flavor()
            if flavor and flavor.flavor_name in control.enabled_watchlists():
                data = flavor.get_watchlist_anime_entry(mal_id)
                if data.get('eps_watched'):
                    eps_watched = kodi_meta['eps_watched'] = data['eps_watched']
                    database.update_kodi_meta(mal_id, kodi_meta)
        episodes = database.get_episode_list(mal_id)
        dub_data = indexers.process_dub(mal_id, kodi_meta['ename']) if control.getSetting('jz.dub') == 'true' else None

        if episodes:
            if kodi_meta['status'] != "Finished Airing":
                return self.append_episodes(mal_id, episodes, eps_watched, poster, fanart, tvshowtitle, dub_data)
            return indexers.process_episodes(episodes, eps_watched, dub_data)
        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.lib.endpoint import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data)
