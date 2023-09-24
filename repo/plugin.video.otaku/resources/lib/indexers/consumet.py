import pickle
import requests

from functools import partial
from resources.lib.ui import database, utils, control
from resources.lib import indexers
from resources import jz


class CONSUMETAPI:
    def __init__(self):
        self.baseUrl = f'http://{control.getSetting("consumet.selfhost.ip")}:3000/' if control.getSetting('consumet.selfhost.enable') == 'true' else 'https://api.consumet.org/'

    def get_anilist_meta(self, anilist_id):
        r = requests.get(f'{self.baseUrl}meta/anilist/info/{anilist_id}')
        return r.json() if r.ok else {}

    @staticmethod
    def parse_episode_view(res, anilist_id, season, poster, fanart, eps_watched, update_time, tvshowtitle, dub_data, filler_data, filler_enable, title_disable):

        if res['number'] == 0:
            return utils.allocate_item('', '')

        url = f'{anilist_id}/{res["number"]}/'

        title = res.get('title')
        if not title:
            title = f'Episode {res["number"]}'

        image = res.get('image')
        info = {
            'plot': res.get('description', ''),
            'title': title,
            'season': season,
            'episode': int(res['number']),
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode'
        }
        if eps_watched:
            if int(eps_watched) >= res['number']:
                info['playcount'] = 1

        try:
            filler = filler_data[res['number'] - 1]
        except IndexError:
            filler = ''

        code = jz.get_second_label(info, dub_data)
        if not code and filler_enable:
            filler = code = control.colorString(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code

        parsed = utils.allocate_item(title, "play/%s" % url, False, image, info, fanart, poster)
        database.update_episode(anilist_id, season=season, number=res['number'], update_time=update_time, kodi_meta=parsed, filler=filler)

        if title_disable and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["number"]}'
            parsed['info']['plot'] = None
        return parsed


    def process_episode_view(self, anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data, filler_enable, title_disable):
        from datetime import date
        update_time = date.today().isoformat()

        result = self.get_anilist_meta(anilist_id)
        result_ep = result.get('episodes')
        if not result or not result_ep:
            return []
        season = 1
        s_id = utils.get_season(result)
        if s_id:
            season = int(s_id[0])
        database.update_season(anilist_id, season)

        mapfunc = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                          eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data,
                          filler_data=filler_data, filler_enable=filler_enable, title_disable=title_disable)

        all_results = list(map(mapfunc, result_ep))
        try:
            all_results = sorted(all_results, key=lambda x: x['info']['episode'])
        except TypeError:
            for inx, i in enumerate(all_results):
                if i['url'] == "":
                    all_results.pop(inx)
            all_results = sorted(all_results, key=lambda x: x['info']['episode'])
        control.notify("Consumet", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data=None,
                        dub_data=None, filler_enable=False, title_disable=False):

        import datetime
        import time
        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime(*(time.strptime(episodes[0]['last_updated'], "%Y-%m-%d")[0:6]))
        # last_updated = datetime.datetime.strptime(episodes[0].get('last_updated'), "%Y-%m-%d") # todo add when python 11 is added

        diff = (datetime.datetime.today() - last_updated).days
        result = self.get_anilist_meta(anilist_id) if diff > 3 else []

        if len(result) > episodes[0]['number_abs']:
            season = database.get_season_list(anilist_id)['season']
            result = result.get('episodes')
            mapfunc2 = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                               eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data,
                               filler_data=filler_data, filler_enable=filler_enable, title_disable=title_disable)
            all_results = list(map(mapfunc2, result))
            try:
                all_results = sorted(all_results, key=lambda x: x['info']['episode'])
            except TypeError:
                for inx, i in enumerate(all_results):
                    if i['url'] == "":
                        all_results.pop(inx)
                all_results = sorted(all_results, key=lambda x: x['info']['episode'])
            control.notify("Consumet", f'{tvshowtitle} Appended to Database', icon=poster)
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

        dub_data =  None
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

            return indexers.process_episodes(episodes, eps_watched, dub_data=dub_data, filler_enable=filler_enable,
                                          title_disable=title_disable), 'episodes'

        from resources.jz import anime_filler
        filler_data = anime_filler.get_data(kodi_meta['ename'])
        return self.process_episode_view(anilist_id, poster, fanart, eps_watched, tvshowtitle=tvshowtitle, dub_data=dub_data,
                    filler_data=filler_data, filler_enable=filler_enable, title_disable=title_disable), 'episodes'
