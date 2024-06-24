import requests
import pickle

from functools import partial
from resources.lib.ui import database, utils, control
from resources.lib import indexers
from resources import jz


class SIMKLAPI:
    def __init__(self):
        # self.ClientID = "5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b" # Swag API Key
        # self.ClientID = "503b6b37476926a7a17ac86b95a81b245879955a7531e3e7d8913c0624796ea0" # My API key

        self.ClientID = "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8"  # Otaku API key
        self.baseUrl = "https://api.simkl.com"
        self.imagePath = "https://wsrv.nl/?url=https://simkl.in/episodes/%s_w.webp"

    def parse_episode_view(self, res, anilist_id, season, poster, fanart, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None):
        episode = int(res['episode'])

        url = f"{anilist_id}/{episode}/"

        title = res.get('title')
        if not title:
            title = f'Episode {episode}'

        image = self.imagePath % res['img'] if res.get('img') else poster

        info = {
            'UniqueIDs': {
                'anilist_id': str(anilist_id),
                'mal_id': '',
                'kitsu_id': ''
            },
            'plot': res.get('description', ''),
            'title': title,
            'season': season,
            'episode': episode,
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode'
        }
        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            info['aired'] = res['date'][:10]
        except KeyError:
            pass

        try:
            filler = filler_data[episode - 1]
        except (IndexError, TypeError):
            filler = ''
        code = jz.get_second_label(info, dub_data)
        if not code and control.bools.filler:
            filler = code = control.colorString(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code

        parsed = utils.allocate_item(title, f"play/{url}", False, True, image, info, fanart, poster)

        kodi_meta = pickle.dumps(parsed)
        if not episodes or not any(x['kodi_meta'] == kodi_meta for x in episodes):
            database.update_episode(anilist_id, season, episode, update_time, kodi_meta, filler=filler)

        if control.bools.clean_titles and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["episode"]}'
            parsed['info']['plot'] = None
        return parsed

    def process_episode_view(self, anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data):
        from datetime import date
        update_time = date.today().isoformat()

        result = self.get_anime_info(anilist_id)
        if not result:
            return []

        title_list = [name['name'] for name in result['alt_titles']]
        season = utils.get_season(title_list) if int(result.get('season', 1)) == 1 else int(result['season'])

        result_meta = self.get_episode_meta(anilist_id)
        result_ep = [x for x in result_meta if x['type'] == 'episode']

        mapfunc = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)

        all_results = list(map(mapfunc, result_ep))
        if control.bools.show_empty_eps:
            total_ep = result.get('total_episodes', 0)
            empty_ep = []
            for ep in range(len(all_results) + 1, total_ep + 1):
                empty_ep.append({
                    # 'title': control.colorString(f'Episode {ep}', 'red'),
                    'title': f'Episode {ep}',
                    'episode': ep,
                    'image': poster
                })
            mapfunc_emp = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster,
                                  fanart=fanart, eps_watched=eps_watched, update_time=update_time,
                                  tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
            all_results += list(map(mapfunc_emp, empty_ep))

        control.notify("SIMKL", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, dub_data=None):
        import datetime
        import time

        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime(*(time.strptime(episodes[0]['last_updated'], "%Y-%m-%d")[0:6]))

        # todo add when they fucking fix strptime
        # last_updated = datetime.datetime.strptime(episodes[0].get('last_updated'), "%Y-%m-%d")

        diff = (datetime.datetime.today() - last_updated).days
        result_meta = self.get_episode_meta(anilist_id) if diff > int(control.getSetting('interface.check.updates')) else []
        result_ep = [x for x in result_meta if x['type'] == 'episode']
        if len(result_ep) > len(episodes):
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, episodes=episodes, anilist_id=anilist_id, season=season,
                               poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time,
                               tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=None)
            all_results = list(map(mapfunc2, result_ep))
            control.notify("SIMKL Appended", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            database.update_episode(anilist_id, episodes[0]['season'], episodes[0]['number'], update_time, episodes[0]['kodi_meta'], episodes[0]['filler'])
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, anilist_id, show_meta):
        kodi_meta = pickle.loads(database.get_show(anilist_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        eps_watched = kodi_meta.get('eps_watched')
        episodes = database.get_episode_list(anilist_id)
        tvshowtitle = kodi_meta['title_userPreferred']

        dub_data = indexers.process_dub(anilist_id, kodi_meta['ename']) if control.getSetting('jz.dub') == 'true' else None

        if episodes:
            if kodi_meta['status'] != "FINISHED":
                return self.append_episodes(anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle,
                                            dub_data), 'episodes'
            return indexers.process_episodes(episodes, eps_watched, dub_data), 'episodes'
        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.jz import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data,
                                         filler_data), 'episodes'

    def get_anime_info(self, anilist_id):
        show_ids = database.get_show(anilist_id)
        simkl_id = show_ids['simkl_id']

        if not simkl_id:
            simkl_id = self.get_simkl_id('anilist', anilist_id)
            if not simkl_id:
                mal_id = database.get_mappings(anilist_id, 'anilist_id')['mal_id']
                simkl_id = self.get_simkl_id('mal', mal_id)
            database.add_mapping_id(anilist_id, 'simkl_id', simkl_id)
        if not simkl_id:
            return
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        r = requests.get(f'{self.baseUrl}/anime/{simkl_id}', params=params)
        res = r.json() if r.ok else {}
        return res

    def get_episode_meta(self, anilist_id):
        show_ids = database.get_show(anilist_id)
        simkl_id = show_ids['simkl_id']
        if not simkl_id:
            mal_id = show_ids['mal_id']
            simkl_id = self.get_simkl_id('mal', mal_id)
            database.add_mapping_id(anilist_id, 'simkl_id', simkl_id)
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        r = requests.get(f'{self.baseUrl}/anime/episodes/{simkl_id}', params=params)
        res = r.json()
        return res

    def get_simkl_id(self, send_id, anime_id):
        params = {
            send_id: anime_id,
            "client_id": self.ClientID,
        }
        r = requests.get(f'{self.baseUrl}/search/id', params=params)
        r = r.json()
        if r:
            anime_id = r[0]['ids']['simkl']
            return anime_id

    def get_mapping_ids(self, send_id, anime_id):
        # return_id = anidb, ann, mal, offjp, wikien, wikijp, instagram, imdb, tmdb, tw, tvdbslug, anilist, animeplanet, anisearch, kitsu, livechart, traktslug
        simkl_id = self.get_simkl_id(send_id, anime_id)
        params = {
            'extended': 'full',
            'client_id': self.ClientID
        }
        r = requests.get(f'{self.baseUrl}/anime/{simkl_id}', params=params)
        if r.ok:
            r = r.json()
            return r['ids']
