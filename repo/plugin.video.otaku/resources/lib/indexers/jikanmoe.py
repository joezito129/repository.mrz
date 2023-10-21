import requests
import pickle
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
                    control.print(r.json())
                    return res_data
                res = r.json()
                if not res['pagination']['has_next_page']:
                    break
                res_data += res['data']
        return res_data

    @staticmethod
    def parse_episode_view(res, anilist_id, season, poster, fanart, eps_watched, update_time, tvshowtitle,
                           dub_data, filler_data, filler_enable, title_disable):

        episode = res['mal_id']
        url = "%s/%s/" % (anilist_id, episode)

        title = res.get('title')
        if not title:
            title = res["episode"]

        image = res['images']['jpg']['image_url'] if res.get('images') else poster

        info = {
            # 'plot': res.get('description', ''),
            'title': title,
            'season': season,
            'episode': episode,
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode'
        }

        if eps_watched:
            if int(eps_watched) >= episode:
                info['playcount'] = 1

        try:
            filler = filler_data[episode - 1]
        except IndexError:
            filler = ''

        code = jz.get_second_label(info, dub_data)
        if not code and filler_enable:
            filler = code = control.colorString(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code

        parsed = utils.allocate_item(title, "play/%s" % url, False, image, info, fanart, poster)
        database.update_episode(anilist_id, season=season, number=episode, update_time=update_time,
                                kodi_meta=parsed, filler=filler)

        if title_disable and info.get('playcount') != 1:
            parsed['info']['title'] = res['episode']
            parsed['info']['plot'] = None
        return parsed

    def process_episode_view(self, anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data, filler_enable, title_disable):
        from resources.lib.indexers.syncurl import SyncUrl
        from datetime import date
        update_time = date.today().isoformat()

        result = self.get_anime_info(anilist_id)
        if not result:
            return []

        sync_data = SyncUrl().get_anime_data(anilist_id, 'Anilist')
        s_id = utils.get_season(sync_data[0])
        season = int(s_id[0]) if s_id else 1
        database.update_season(anilist_id, season)

        result_ep = self.get_episode_meta(anilist_id)

        mapfunc = partial(self.parse_episode_view, anilist_id=anilist_id, season=season,
                          poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time,
                          tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data, filler_enable=filler_enable,
                          title_disable=title_disable)

        all_results = list(map(mapfunc, result_ep))
        if len(all_results) == 0 or control.getSetting('interface.showemptyeps') == 'true':
            total_ep = result.get('episodes', 0)
            empty_ep = []
            for ep in range(len(all_results) + 1, total_ep + 1):
                empty_ep.append({
                    # 'title': control.colorString(f'Episode {ep}', 'red'),
                    'title': f'Episode {ep}',
                    'mal_id': ep,
                    'image': poster
                })
            mapfunc_emp = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                                eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data,
                                filler_data=filler_data, filler_enable=filler_enable, title_disable=title_disable)
            all_results += list(map(mapfunc_emp, empty_ep))
        control.notify("Jikanmoa", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data=None,
                        dub_data=None, filler_enable=False, title_disable=False):
        import datetime
        import time
        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime(*(time.strptime(episodes[0]['last_updated'], "%Y-%m-%d")[0:6]))
        # last_updated = datetime.datetime.strptime(episodes[0].get('last_updated'), "%Y-%m-%d") #todo add when python 11 is added

        diff = (datetime.datetime.today() - last_updated).days
        result = self.get_episode_meta(anilist_id) if diff > 3 else []

        if len(result) > len(episodes):
            season = database.get_season_list(anilist_id)['season']
            mapfunc2 = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                               eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data,
                               filler_data=filler_data, filler_enable=filler_enable, title_disable=title_disable)
            all_results = list(map(mapfunc2, result))
            control.notify("Jikanmoa", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data, filler_enable=filler_enable, title_disable=title_disable)
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

        dub_data = None
        if control.getSetting('jz.dub') == 'true':
            from resources.jz.TeamUp import teamup
            dub_data = teamup.get_dub_data(kodi_meta['ename'])

        # if control.getSetting('jz.sub') == 'true':
        #     from resources.jz import AniList
        #     ani_data = AniList.get_anime_info_anilist_id(anilist_id)

        filler_enable = control.getSetting('jz.filler') == 'true'
        title_disable = control.getSetting('interface.cleantitles') == 'true'
        if episodes:
            if kodi_meta['status'] != "FINISHED":
                from resources.jz import anime_filler
                filler_data = anime_filler.get_data(kodi_meta['ename'])
                return self.append_episodes(anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data,
                                            dub_data, filler_enable, title_disable), 'episodes'
            return indexers.process_episodes(episodes, eps_watched, dub_data, filler_enable, title_disable), 'episodes'

        from resources.jz import anime_filler
        filler_data = anime_filler.get_data(kodi_meta['ename'])
        return self.process_episode_view(anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data,
                                         filler_enable, title_disable), 'episodes'
