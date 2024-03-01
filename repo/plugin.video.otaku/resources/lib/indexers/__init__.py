import pickle

from functools import partial
from resources import jz


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


def process_episodes(episodes, eps_watched, dub_data=None, filler_enable=False, title_disable=False):
    mapfunc = partial(parse_episodes, eps_watched=eps_watched, dub_data=dub_data, filler_enable=filler_enable,
                      title_disable=title_disable)
    all_results = list(map(mapfunc, episodes))
    return all_results
