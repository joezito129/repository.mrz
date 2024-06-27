import pickle

from functools import partial
from resources import jz


def parse_episodes(res, eps_watched, dub_data=None, filler_enable=False, title_disable=False):
    parsed = pickle.loads(res['kodi_meta'])
    if eps_watched and int(eps_watched) >= res['number']:
        parsed['info']['playcount'] = 1
    if title_disable and parsed['info'].get('playcount') != 1:
        parsed['info']['title'] = f'Episode {res["number"]}'
        parsed['info']['plot'] = None
    code = jz.get_second_label(parsed['info'], dub_data, res['filler'], filler_enable)
    parsed['info']['code'] = code
    return parsed


def process_episodes(episodes, eps_watched, dub_data=None, filler_enable=False, title_disable=False):
    mapfunc = partial(parse_episodes, eps_watched=eps_watched, dub_data=dub_data, filler_enable=filler_enable, title_disable=title_disable)
    all_results = list(map(mapfunc, episodes))
    return all_results


def process_dub(anilist_id, ename):
    from resources.lib.ui import database, control
    from datetime import date

    update_time = date.today().isoformat()

    show_data = database.get_show_data(anilist_id)
    if not show_data or show_data['last_updated'] != update_time:
        if int(control.getSetting('jz.dub.api')) == 0:
            from resources.jz.teamup import teamup
            dub_data = teamup.get_dub_data(ename)
            data = {"dub_data": dub_data}
            database.update_show_data(anilist_id, data, update_time)
        else:
            from resources.jz import animeschedule
            dub_data = animeschedule.get_dub_time(anilist_id)
            data = {"dub_data": dub_data}
            database.update_show_data(anilist_id, data, update_time)
    else:
        dub_data = pickle.loads(show_data['data'])['dub_data']
    return dub_data
