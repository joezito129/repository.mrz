import pickle
import requests

from functools import partial
from resources.lib.ui import control, database, utils, get_meta
from resources import jz


class ENIMEAPI:
    def __init__(self):
        self.baseUrl = 'https://api.enime.moe'
        self.episodesUrl = 'mapping/anilist/{0}'
        self.streamUrl = 'source/{0}'

    def get_anilist_meta(self, anilist_id):
        r = requests.get(f'{self.baseUrl}/mapping/anilist/{anilist_id}')
        if r.ok:
            return r.json()

    def process_episode_view(self, anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data,
                             filler_enable, title_disable):
        from datetime import date
        update_time = date.today().isoformat()

        result = self.get_anilist_meta(anilist_id)
        result_ep = result['episodes']
        if not result or not result_ep:
            return

        season = 1
        s_id = utils.get_season(result)
        if s_id:
            season = int(s_id[0])
        database._update_season(anilist_id, season)


        mapfunc = partial(self.parse_episode_view, anilist_id=anilist_id, season=season,
                          poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time,
                          tvshowtitle=tvshowtitle, episode_count=len(result_ep), dub_data=dub_data, filler_data=filler_data, filler_enable=filler_enable,
                          title_disable=title_disable)

        all_results = list(map(mapfunc, result_ep))

        try:
            all_results = sorted(all_results, key=lambda x: x['info']['episode'])
        except TypeError:
            for inx, i in enumerate(all_results):
                if i['url'] == "":
                    all_results.pop(inx)
            all_results = sorted(all_results, key=lambda x: x['info']['episode'])
        control.ok_dialog("ENIME", "Added to Database")
        return all_results

    @staticmethod
    def parse_episode_view(res, anilist_id, season, poster, fanart, eps_watched, update_time, tvshowtitle,
                            episode_count, dub_data, filler_data, filler_enable, title_disable):

        if res['number'] == 0:
            return utils.allocate_item('', '')

        url = "%s/%s/" % (anilist_id, res['number'])

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
            info['aired'] = res['airedAt'][:10]
        except (KeyError, TypeError):
            info['aired'] = ''

        try:
            filler = filler_data[res['number'] - 1]
        except IndexError:
            filler = ''

        code = jz.get_second_label(info, dub_data)

        if not code and filler_enable:
            filler = code = control.colorString(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code

        parsed = utils.allocate_item(title, "play/%s" % url, False, image, info, fanart, poster)
        database._update_episode(anilist_id, season=season, number=res['number'], update_time=update_time,
                                 kodi_meta=parsed, filler=filler, number_abs=episode_count)

        if title_disable and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["number"]}'
            parsed['info']['plot'] = None

        return parsed


    def append_episodes(self, anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, filler_data=None,
                        dub_data=None, filler_enable=False, title_disable=False):
        import datetime
        import time
        update_time = datetime.date.today().isoformat()
        last_updated = datetime.datetime(*(time.strptime(episodes[0]['last_updated'], "%Y-%m-%d")[0:6]))
        # last_updated = datetime.datetime.strptime(episodes[0].get('last_updated'), "%Y-%m-%d") #todo add when python 11 is added

        diff = (datetime.datetime.today() - last_updated).days
        result = self.get_anilist_meta(anilist_id) if diff > 3 else []

        if len(result) > episodes[0]['number_abs']:
            season = database.get_season_list(anilist_id)['season']
            result = result.get('episodes')
            mapfunc2 = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                               eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, episode_count=len(result),
                               dub_data=dub_data, filler_data=filler_data, filler_enable=filler_enable,
                               title_disable=title_disable)
            all_results = list(map(mapfunc2, result))
            try:
                all_results = sorted(all_results, key=lambda x: x['info']['episode'])
            except TypeError:
                for inx, i in enumerate(all_results):
                    if i['url'] == "":
                        all_results.pop(inx)
                all_results = sorted(all_results, key=lambda x: x['info']['episode'])
        else:
            mapfunc1 = partial(self.parse_episodes, eps_watched=eps_watched, dub_data=dub_data, filler_enable=filler_enable,
                           title_disable=title_disable)
            all_results = list(map(mapfunc1, episodes))

        return all_results


    def process_episodes(self, episodes, eps_watched, dub_data=None, filler_enable=False, title_disable=False):
        mapfunc = partial(self.parse_episodes, eps_watched=eps_watched, dub_data=dub_data, filler_enable=filler_enable, title_disable=title_disable)
        all_results = list(map(mapfunc, episodes))
        return all_results

    @staticmethod
    def parse_episodes(res, eps_watched, dub_data=None, filler_enable=False, title_disable=False):
        parsed = pickle.loads(res['kodi_meta'])
        if eps_watched:
            if int(eps_watched) >= res['number']:
                parsed['info']['playcount'] = 1
        if title_disable and parsed['info'].get('playcount') != 1:
            parsed['info']['title'] = f'Episode {res["number"]}'
            parsed['info']['plot'] = None
        code = jz.get_second_label(parsed['info'], dub_data, res['filler'], filler_enable)
        parsed['info']['code'] = code
        return parsed

    def get_episodes(self, anilist_id):
        show_meta = database.get_show_meta(anilist_id)
        if not show_meta:
            get_meta.get_meta(anilist_id)
            show_meta = database.get_show_meta(anilist_id)
            if not show_meta:
                return [], 'episodes'

        kodi_meta = pickle.loads(database.get_show(anilist_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        eps_watched = kodi_meta.get('eps_watched')
        episodes = database.get_episode_list(anilist_id)
        tvshowtitle = kodi_meta['title_userPreferred']

        dub_data = None
        if control.getSetting('jz.dub') == 'true':
            show_data = database.get_show_data(anilist_id)
            if show_data:
                data = pickle.loads(show_data['data'])
                dub_data = data['dub_data']

            import datetime
            import time
            update_time = datetime.date.today().isoformat()
            try:
                last_updated = datetime.datetime(*(time.strptime(show_data['last_updated'], "%Y-%m-%d")[0:6]))
                diff = (datetime.datetime.today() - last_updated).days
            except TypeError:
                diff = 10
            if diff > 3:
                from resources.jz.TeamUp import teamup
                dub_data = teamup.get_dub_data(kodi_meta['ename'])
                update_data = {
                    'dub_data': dub_data,
                }
                database._update_show_data(anilist_id, update_data, update_time)

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
            return self.process_episodes(episodes, eps_watched, dub_data=dub_data, filler_enable=filler_enable,
                                          title_disable=title_disable), 'episodes'


        from resources.jz import anime_filler
        filler_data = anime_filler.get_data(kodi_meta['ename'])
        return self.process_episode_view(anilist_id, poster, fanart, eps_watched,
                                          tvshowtitle=tvshowtitle, dub_data=dub_data,
                                          filler_data=filler_data, filler_enable=filler_enable,
                                          title_disable=title_disable), 'episodes'

    def get_sources(self, anilist_id, episode, provider, lang=None):
        sources = []
        eurl = self.episodesUrl.format(anilist_id)
        r = requests.get(f'{self.baseUrl}/{eurl}')
        episodes = r.json().get('episodes')
        if episodes:
            episodes = sorted(episodes, key=lambda x: x.get('number'))
            if episodes[0].get('number') != 1:
                episode = episodes[0].get('number') - 1 + int(episode)
            episode_srcs = [x.get('sources') for x in episodes if x.get('number') == int(episode)][0]
            episode_id = episode_srcs[0].get('id') if provider == 'gogoanime' else episode_srcs[1].get('id')
            r = requests.get(f'{self.baseUrl}/{self.streamUrl.format(episode_id)}')
            sources = r.json()
        return sources
