import pickle

from datetime import date
from functools import partial
from resources.lib import endpoint
from resources.lib.ui import database, control, utils


def parse_episodes(res, eps_watched, dub_data=None):
    parsed = pickle.loads(res['kodi_meta'])
    if eps_watched and int(eps_watched) >= res['number']:
        parsed['info']['playcount'] = 1
    if control.settingids.clean_titles and parsed['info'].get('playcount') != 1:
        parsed['info']['title'] = f'Episode {res["number"]}'
        parsed['info']['plot'] = None
    code = endpoint.get_second_label(parsed['info'], dub_data, res.get('filler'))
    parsed['info']['code'] = code
    return parsed


def process_episodes(episodes, eps_watched, dub_data=None):
    mapfunc = partial(parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
    all_results = list(map(mapfunc, episodes))
    return all_results


def process_dub(mal_id, ename):
    update_time = date.today().isoformat()
    if not (show_data := database.get_show_data(mal_id)) or show_data['last_updated'] != update_time:
        if control.getInt('jz.dub.api') == 0:
            from resources.lib.endpoint import teamup
            dub_data = teamup.get_dub_data(ename)
            data = {"dub_data": dub_data}
            database.update_show_data(mal_id, data, update_time)
        else:
            from resources.lib.endpoint import animeschedule
            dub_data = animeschedule.get_dub_time(mal_id)
            data = {"dub_data": dub_data}
            database.update_show_data(mal_id, data, update_time)
    else:
        dub_data = pickle.loads(show_data['data'])['dub_data']
    return dub_data


def get_diff(episodes_0):
    import datetime
    update_time = datetime.date.today().isoformat()
    try:
        last_updated = datetime.datetime.strptime(episodes_0.get('last_updated'), "%Y-%m-%d")
    except:
        import time
        control.log('Unsupported strptime using fromtimestamp', 'warning')
        last_updated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(episodes_0.get('last_updated'), '%Y-%m-%d')))
    diff = (datetime.datetime.today() - last_updated).days
    return update_time, diff

def update_database(mal_id, update_time, res, url, image, info, season, episode, episodes, title, fanart, poster, dub_data, filler, anidb_ep_id):
    filler = control.colorstr(filler, color="red") if filler == 'Filler' else filler

    parsed = utils.allocate_item(title, f"play/{url}", False, True, [], image, info, fanart, poster)
    kodi_meta = pickle.dumps(parsed)
    if not episodes or len(episodes) <= episode:
        database.create_episode(mal_id, episode, update_time, season, kodi_meta, filler, anidb_ep_id)
    elif kodi_meta != episodes[episode - 1]['kodi_meta']:
        database.update_episode_column(mal_id, episode, 'kodi_meta', kodi_meta)

    if control.settingids.clean_titles and info.get('playcount') != 1:
        parsed['info']['title'] = f'Episode {res["episode"]}'
        parsed['info']['plot'] = None

    code = endpoint.get_second_label(info, dub_data, filler)
    parsed['info']['code'] = code

    return parsed