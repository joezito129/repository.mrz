import requests
import pickle

from functools import partial
from resources.lib.ui import utils, database, control
from resources.lib import indexers
from resources import jz


class ANIZIPAPI:

    def __init__(self):
        self.baseUrl = "https://api.ani.zip"

    def get_anime_info(self, anilist_id):
        params = {
            'anilist_id': anilist_id
        }
        r = requests.get(f'{self.baseUrl}/mappings', params=params)
        return r.json()

    @staticmethod
    def parse_episode_view(res, anilist_id, season, poster, fanart, eps_watched, update_time, tvshowtitle,
                           dub_data, filler_data, filler_enable, title_disable, episodes=None):
        episode = int(res['episode'])

        url = "%s/%s/" % (anilist_id, episode)

        title = res['title']['en']
        if not title:
            title = f'Episode {episode}'

        image = res['image'] if res.get('image') else poster

        info = {
            'plot': res.get('overview'),
            'title': title,
            'season': season,
            'episode': episode,
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode',
            'rating': float(res.get('rating', 0))
        }
        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            info['aired'] = res['airDate'][:10]
        except KeyError:
            # info['aired'] = res['airDateUtc']
            pass

        try:
            filler = filler_data[episode - 1]
        except (IndexError, TypeError):
            filler = ''
        code = jz.get_second_label(info, dub_data)
        if not code and filler_enable:
            filler = code = control.colorString(filler, color="red") if filler == 'Filler' else filler
        info['code'] = code
        parsed = utils.allocate_item(title, f"play/{url}", False, image, info, fanart, poster, isplayable=True)

        if not episodes or not any(x['number'] == episode for x in episodes):
            database.update_episode(anilist_id, season=season, number=episode, update_time=update_time, kodi_meta=parsed, filler=filler)

        if title_disable and info.get('playcount') != 1:
            parsed['info']['title'] = f'Episode {episode}'
            parsed['info']['plot'] = None
        return parsed

    def process_episode_view(self, anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data, filler_enable, title_disable):
        from datetime import date
        update_time = date.today().isoformat()

        result = self.get_anime_info(anilist_id)
        if not result:
            return []

        result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]

        season = result_ep[0]['seasonNumber']

        mapfunc = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                          eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data,
                          filler_data=filler_data, filler_enable=filler_enable, title_disable=title_disable)

        all_results = list(map(mapfunc, result_ep))
        if control.getSetting('interface.showemptyeps') == 'true':
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
                                  tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data,
                                  filler_enable=filler_enable, title_disable=title_disable)
            all_results += list(map(mapfunc_emp, empty_ep))

        control.notify("Anizip", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle,
                        dub_data=None, filler_enable=False, title_disable=False):
        import datetime
        update_time = datetime.date.today().isoformat()

        import time
        last_updated = datetime.datetime(*(time.strptime(episodes[0]['last_updated'], "%Y-%m-%d")[0:6]))

        # todo add when they fucking fix strptime
        # last_updated = datetime.datetime.strptime(episodes[0].get('last_updated'), "%Y-%m-%d")

        diff = (datetime.datetime.today() - last_updated).days
        if diff > 3:
            result = self.get_anime_info(anilist_id)
            result_ep = [result['episodes'][res] for res in result['episodes'] if res.isdigit()]
        else:
            result_ep = []
        if len(result_ep) > len(episodes):
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, anilist_id=anilist_id, season=season, poster=poster, fanart=fanart,
                               eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data,
                               filler_data=None, filler_enable=filler_enable, title_disable=title_disable, episodes=episodes)
            all_results = list(map(mapfunc2, result_ep))
            control.notify("ANIZIP Appended", f'{tvshowtitle} Appended to Database', icon=poster)
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

        dub_data = indexers.process_dub(anilist_id, kodi_meta['ename']) if control.getSetting('jz.dub') == 'true' else None

        filler_enable = control.getSetting('jz.filler') == 'true'
        title_disable = control.getSetting('interface.cleantitles') == 'true'
        if episodes:
            if kodi_meta['status'] != "FINISHED":
                return self.append_episodes(anilist_id, episodes, eps_watched, poster, fanart, tvshowtitle, dub_data,
                                            filler_enable, title_disable), 'episodes'
            return indexers.process_episodes(episodes, eps_watched, dub_data, filler_enable, title_disable), 'episodes'
        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.jz import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(anilist_id, poster, fanart, eps_watched, tvshowtitle, dub_data, filler_data,
                                         filler_enable, title_disable), 'episodes'
