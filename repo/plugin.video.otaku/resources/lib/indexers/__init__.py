import datetime

from functools import partial
from resources.lib import endpoint
from resources.lib.ui import database, control, utils
from resources.packages import msgpack

def parse_episodes(res, eps_watched: int, dub_data=None) -> dict:
    parsed = msgpack.loads(res['kodi_meta'])
    if eps_watched >= res['number']:
        parsed['info']['playcount'] = 1
    if control.getBool('interface.cleantitles') and parsed['info'].get('playcount') != 1:
        parsed['info']['title'] = f'Episode {res["number"]}'
        parsed['info']['plot'] = None
    code = endpoint.get_second_label(parsed['info'], dub_data, res.get('filler'))
    parsed['info']['code'] = code
    return parsed


def process_episodes(episodes, eps_watched, dub_data=None) -> list:
    mapfunc = partial(parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
    all_results = list(map(mapfunc, episodes))
    return all_results


def process_dub(mal_id: int, ename: str) -> list:
    update_time = datetime.date.today().isoformat()
    if (show_data := database.get_show_data(mal_id)) is None or show_data['last_updated'] != update_time:
        if control.getInt('jz.dub.api') == 0:
            from resources.lib.endpoint import teamup
            dub_data = teamup.get_dub_data(mal_id, ename)
            database.update_show_data(mal_id, dub_data, update_time)
        else:
            from resources.lib.endpoint import animeschedule
            dub_data = animeschedule.get_dub_time(mal_id)
            database.update_show_data(mal_id, dub_data, update_time)
    else:
        dub_data = msgpack.loads(show_data['dub_data'])
    return dub_data


def get_diff(episodes_0) -> tuple:
    update_time = datetime.date.today().isoformat()
    last_updated = utils.strp_time(episodes_0.get('last_updated'), "%Y-%m-%d")
    diff = (datetime.datetime.today() - last_updated).days
    return update_time, diff
