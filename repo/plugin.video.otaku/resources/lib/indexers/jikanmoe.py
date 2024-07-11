import requests
import pickle
import datetime
import time

from functools import partial
from resources.lib.ui import utils, database, control
from resources.lib import indexers
from resources import jz


class JikanAPI:
    def __init__(self):
        self.baseUrl = "https://api.jikan.moe/v4"

    def get_anime_info(self, anilist_id):
        show = database.get_show(anilist_id)
        mal_id = show['mal_id']
        r = requests.get(f'{self.baseUrl}/anime/{mal_id}')
        return r.json()['data']

    def get_episode_meta(self, anilist_id):
        show = database.get_show(anilist_id)
        mal_id = show['mal_id']
        url = f'{self.baseUrl}/anime/{mal_id}/videos/episodes'
        # url = f'{self.baseUrl}/anime/{mal_id}/episodes' # no pictures but can handle 100 per page
        r = requests.get(url)
        res = r.json()
        if not res['pagination']['has_next_page']:
            res_data = res['data']
        else:
            res_data = res['data']
            for i in range(2, res['pagination']['last_visible_page']):
                params = {
                    'page': i
                }
                if (i - 1) % 3 == 0:
                    time.sleep(2)
                r = requests.get(url, params=params)
                if not r.ok:
                    control.ok_dialog(control.ADDON_NAME, r.json())
                    return res_data
                res = r.json()
                if not res['pagination']['has_next_page']:
                    break
                res_data += res['data']
        return res_data

    @staticmethod
    def parse_episode_view(res, anilist_id, season, poster, fanart, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None):
        episode = res['mal_id']
        url = f"{anilist_id}/{episode}"
        title = res.get('title')
        if not title:
            title = res["episode"]
        image = res['images']['jpg']['image_url'] if res.get('images') else poster
        info = {
            'UniqueIDs': {'anilist_id': str(anilist_id)},
            'title': title,
            'season': season,
            'episode': episode,
            # 'plot': res.get('description', ''),
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode'
        }
        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            filler = filler_data[episode - 1]
        except IndexError:
            filler = ''

        code = jz.get_second_label(info, dub_data)
        if not code and control.settingids.filler:
            filler = code = control.colorstr(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code
        parsed = utils.allocate_item(title, f"play/{url}", False, True, image, info, fanart, poster)
        kodi_meta = pickle.dumps(parsed)
        if not episodes or not any(x['kodi_meta'] == kodi_meta for x in episodes):
            database.update_episode(anilist_id, season, episode, update_time, kodi_meta, filler=filler)
        if control.settingids.clean_titles and info.get('playcount') != 1:
            parsed['info']['title'] = res['episode']
            parsed['info']['plot'] = None
        return parsed

    def process_episode_view(self, anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data):
        update_time = datetime.date.today().isoformat()

        result = self.get_anime_info(anilist_id)
        if not result:
            return []

        title_list = [name['title'] for name in result['titles']]

        season = utils.get_season(title_list)
        result_ep = self.get_episode_meta(anilist_id)
        mapfunc = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
        all_results = sorted(list(map(mapfunc, result_ep)), key=lambda x: x['info']['episode'])
        if control.settingids.show_empty_eps:
            total_ep = result.get('episodes', 0)
            empty_ep = []
            for ep in range(len(all_results) + 1, total_ep + 1):
                empty_ep.append({
                    'title': f'Episode {ep}',
                    'mal_id': ep,
                    'image': poster
                })
            mapfunc_emp = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
            all_results += list(map(mapfunc_emp, empty_ep))
        control.notify("Jikanmoa", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data=None, dub_data=None):
        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(episodes[0].get('last_updated'), '%Y-%m-%d')))

        diff = (datetime.datetime.today() - last_updated).days
        result = self.get_episode_meta(anilist_id) if diff > int(control.getSetting('interface.check.updates')) else []
        if len(result) > len(episodes):
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data, episodes=episodes)
            all_results = list(map(mapfunc2, result))
            control.notify("Jikanmoa", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, anilist_id, show_meta):
        kodi_meta = pickle.loads(database.get_show(anilist_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        tvshowtitle = kodi_meta['title_userPreferred']
        if not (eps_watched := kodi_meta.get('eps_watched')) and control.settingids.watchlist_data:
            from resources.lib.WatchlistFlavor import WatchlistFlavor
            flavor = WatchlistFlavor.get_update_flavor()
            if flavor:
                data = flavor.get_watchlist_anime_entry(anilist_id)
                if data.get('eps_watched'):
                    eps_watched = kodi_meta['eps_watched'] = data['eps_watched']
                    database.update_kodi_meta(anilist_id, kodi_meta)
        episodes = database.get_episode_list(anilist_id)
        dub_data = indexers.process_dub(anilist_id, kodi_meta['ename']) if control.getSetting('jz.dub') == 'true' else None
        if episodes:
            if kodi_meta['status'] != "FINISHED":
                from resources.jz import anime_filler
                filler_data = anime_filler.get_data(kodi_meta['ename'])
                return self.append_episodes(anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data, dub_data), 'episodes'
            return indexers.process_episodes(episodes, eps_watched, dub_data), 'episodes'

        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.jz import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data), 'episodes'
