import os

from functools import partial
from resources.lib.ui import control, database
from datetime import datetime

def allocate_item(name: str, url: str, isfolder: bool, isplayable: bool, cm: list, image: str, info: dict,
                  fanart='', poster='', landscape='', banner='', clearart='', clearlogo='') -> dict:
    if image and '/' not in image:
        image = os.path.join(control.ICONS_PATH, image)
    if fanart and not isinstance(fanart, list) and '/' not in fanart:
        fanart = os.path.join(control.ICONS_PATH, fanart)
    if poster and '/' not in poster:
        poster = os.path.join(control.ICONS_PATH, poster)
    return {
        'isfolder': isfolder,
        'isplayable': isplayable,
        'name': name,
        'url': url,
        'info': info,
        'cm': cm,
        'image': {
                'poster': poster or image,
                'icon': image,
                'thumb': image,
                'fanart': fanart,
                'landscape': landscape,
                'banner': banner,
                'clearart': clearart,
                'clearlogo': clearlogo
        }
    }


def parse_history_view(q: str, cm: list) -> dict:
    return allocate_item(q, f'search?q={q}', True, False, cm, 'new_search.png', {})


def search_history(search_array):
    cm = [('Remove from Item', 'remove_search_item'), ("Edit Search Item...", "edit_search_item")]
    result = [allocate_item("New Search", "search", True, False, [], 'new_search.png', {})]
    mapfun = partial(parse_history_view, cm=cm)
    result += list(map(mapfun, search_array))
    result.append(allocate_item("Clear Search History...", "clear_search_history", False, False, [], 'clear_search_history.png', {}))
    return result


def parse_view(base: dict, isfolder: bool, isplayable: bool, dub: bool = False) -> dict:
    if control.getBool("divflavors.showdub") and dub:
        base['name'] += ' [COLOR blue](Dub)[/COLOR]'
        base['info']['title'] = base['name']
    parsed_view = allocate_item(base["name"], base["url"], isfolder, isplayable, [], base["image"], base["info"], base.get("fanart", ''), base["image"], base.get("landscape", ''), base.get("banner", ''), base.get("clearart", ''), base.get("clearlogo", ''))
    if control.getBool("divflavors.dubonly") and not dub:
        parsed_view = {}
    return parsed_view


def get_season(titles_list: list, mal_id) -> int:
    import re
    meta_ids = database.get_mappings(mal_id, 'mal_id')
    if season := meta_ids.get('thetvdb_season'):
        if not isinstance(season, int):
            season = 1
    else:
        regexes = [r'season\s(\d+)', r'\s(\d+)st\sseason\s', r'\s(\d+)nd\sseason\s', r'\s(\d+)rd\sseason\s', r'\s(\d+)th\sseason\s']
        s_ids = []
        for regex in regexes:
            compiled_re = re.compile(regex, flags=re.IGNORECASE)
            for name in titles_list:
                found = compiled_re.findall(name)
                if found is not None:
                    s_ids.extend(found)
        if not s_ids:
            cour = True if any(x in ' '.join(titles_list).lower() for x in [' part ', ' cour ']) else False
            if not cour:
                regex = r'\s(\d+)$'
                compiled_re = re.compile(regex, flags=re.IGNORECASE)
                for name in titles_list:
                    found = compiled_re.findall(name)
                    if found is not None:
                        s_ids.extend(found)
        if not s_ids:
            seasonnum = 1
            regex = r' (\d)[ rnt][ sdh(]'
            compiled_re = re.compile(regex, flags=re.IGNORECASE)
            for title in titles_list:
                search_ = compiled_re.search(f' {title[1]}  ')
                if search_ is not None:
                    seasonnum = search_.group(1)
                    break
            s_ids = [seasonnum]
        season = int(s_ids[0])
        if season > 10:
            season = 1
    return season


def format_time(seconds: float) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

def strp_time(string_time: str, str_format: str):
    try:
        time_format = datetime.strptime(string_time, str_format)
    except TypeError:
        import time
        control.log('Unsupported strptime using fromtimestamp', 'warning')
        try:
            time_format = datetime.fromtimestamp(time.mktime(time.strptime(string_time, str_format)))
        except Exception as e:
            control.log(f'Failed to strip_time {e}', 'warning')
            time_format = None
    return time_format
