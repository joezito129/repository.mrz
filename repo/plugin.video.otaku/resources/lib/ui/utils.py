from functools import partial
from resources.lib.ui import control


def allocate_item(name: str, url: str, isfolder: bool, isplayable: bool, cm: list, image: str, info: dict,
                  fanart=None, poster=None, landscape=None, banner=None, clearart=None, clearlogo=None) -> dict:

    if image and '/' not in image:
        image = (control.ICONS_PATH / image).as_posix()
    if fanart and not isinstance(fanart, list) and '/' not in fanart:
        fanart = (control.ICONS_PATH / fanart).as_posix()
    if poster and '/' not in poster:
        poster = (control.ICONS_PATH / poster).as_posix()
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

def get_image(image, fanart, poster, landscape, banner, clearart, clearlogo) -> dict:
    params =  {
        'poster': poster or image,
        'icon': image,
        'thumb': image,
        'fanart': fanart,
        'landscape': landscape,
        'banner': banner,
        'clearart': clearart,
        'clearlogo': clearlogo
    }
    return {p: params[p] for p in params if params[p]}


def parse_history_view(res: str, cm: list) -> dict:
    return allocate_item(res, f'search/{res}', True, False, cm, '', {})


def search_history(search_array):
    cm = [('Remove from Item', 'remove_search_item'), ("Edit Search Item...", "edit_search_item")]
    result = [allocate_item("New Search", "search/", True, False, [], 'new_search.png', {})]
    mapfun = partial(parse_history_view, cm=cm)
    result += list(map(mapfun, search_array))
    result.append(allocate_item("Clear Search History...", "clear_search_history", False, False, [], 'clear_search_history.png', {}))
    return result


def parse_view(base: dict, isfolder: bool, isplayable: bool, dub: bool = False) -> dict:
    if control.settingids.showdub and dub:
        base['name'] += ' [COLOR blue](Dub)[/COLOR]'
        base['info']['title'] = base['name']
    parsed_view = allocate_item(base["name"], base["url"], isfolder, isplayable, [], base["image"], base["info"], base.get("fanart"), base["image"], base.get("landscape"), base.get("banner"), base.get("clearart"), base.get("clearlogo"))
    if control.settingids.dubonly and not dub:
        parsed_view = None
    return parsed_view


def get_season(titles_list: list) -> int:
    import re
    regexes = [r'season\s(\d+)', r'\s(\d+)st\sseason\s', r'\s(\d+)nd\sseason\s', r'\s(\d+)rd\sseason\s', r'\s(\d+)th\sseason\s']
    s_ids = []
    for regex in regexes:
        s_ids += [re.findall(regex, name, re.IGNORECASE) for name in titles_list]
    s_ids = [s[0] for s in s_ids if s]
    if not s_ids:
        regex = r'\s(\d+)$'
        cour = False
        for name in titles_list:
            if name is not None and (' part ' in name.lower() or ' cour ' in name.lower()):
                cour = True
                break
        if not cour:
            s_ids += [re.findall(regex, name, re.IGNORECASE) for name in titles_list]
    s_ids = [s[0] for s in s_ids if s]
    if not s_ids:
        seasonnum = 1
        try:
            for title in titles_list:
                try:
                    seasonnum = re.search(r' (\d)[ rnt][ sdh(]', f' {title[1]}  ').group(1)
                    break
                except AttributeError:
                    pass
        except AttributeError:
            pass
        s_ids = [seasonnum]
    season = int(s_ids[0])
    if season > 10:
        season = 1
    return season


def format_time(seconds: float) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
