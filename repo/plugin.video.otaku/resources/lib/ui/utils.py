import os
import random
import requests
import xbmcvfs

from resources.lib.ui import control


def allocate_item(name, url, isfolder, image='', info='', fanart=None, poster=None, cast=None, landscape=None, banner=None, isplayable=False, clearart=None, clearlogo=None):
    if not cast:
        cast = []
    if image and '/' not in image:
        image = os.path.join(control.OTAKU_ICONS_PATH, image)
    if fanart:
        fanart = random.choice(fanart)
        if '/' not in fanart:
            fanart = os.path.join(control.OTAKU_ICONS_PATH, fanart)
    if poster and '/' not in poster:
        poster = os.path.join(control.OTAKU_ICONS_PATH, poster)

    new_res = {
        'isfolder': isfolder,
        'isplayable': isplayable,
        'name': name,
        'url': url,
        'info': info,
        'cast': cast,
        'image': {
                'poster': poster,
                'icon': image,
                'thumb': image,
                'fanart': fanart,
                'landscape': landscape,
                'banner': banner,
                'clearart': clearart,
                'clearlogo': clearlogo
        }
    }
    return new_res


def parse_view(base, is_dir=True, dub=False, dubsub_filter=None):
    if dubsub_filter == 'Dub':
        if dub:
            parsed_view = [allocate_item(
                "%s" % base["name"],
                base["url"] + '0',
                is_dir,
                image=base["image"],
                info=base["info"],
                fanart=base.get("fanart"),
                poster=base["image"],
                landscape=base.get("landscape"),
                banner=base.get("banner"),
                clearart=base.get("clearart"),
                clearlogo=base.get("clearlogo")
            )]
        else:
            parsed_view = []
    elif dubsub_filter == 'Both':
        if dub:
            base['name'] += ' [COLOR blue](Dub)[/COLOR]'
            base['info']['title'] = base['name']
        parsed_view = [allocate_item(
            base["name"],
            base["url"],
            isfolder=is_dir,
            image=base["image"],
            info=base["info"],
            fanart=base.get("fanart"),
            poster=base["image"],
            landscape=base.get("landscape"),
            banner=base.get("banner"),
            clearart=base.get("clearart"),
            clearlogo=base.get("clearlogo")
        )]
    else:
        parsed_view = [allocate_item(
            base["name"],
            base["url"],
            isfolder=is_dir,
            image=base["image"],
            info=base["info"],
            fanart=base.get("fanart"),
            poster=base["image"],
            landscape=base.get("landscape"),
            banner=base.get("banner"),
            clearart=base.get("clearart"),
            clearlogo=base.get("clearlogo")
        )]
    return parsed_view


def get_sub(sub_url, sub_lang):
    content = requests.get(sub_url).text
    subtitle = xbmcvfs.translatePath('special://temp/')
    fname = 'TemporarySubs.{0}.srt'.format(sub_lang)
    fpath = os.path.join(subtitle, fname)
    if sub_url.endswith('.vtt'):
        fname = fname.replace('.srt', '.vtt')
        fpath = fpath.replace('.srt', '.vtt')

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    return 'special://temp/%s' % fname


def del_subs():
    dirs, files = xbmcvfs.listdir('special://temp/')
    for fname in files:
        if fname.startswith('TemporarySubs'):
            xbmcvfs.delete('special://temp/%s' % fname)


def get_season(titles_list):
    import re
    regexes = [r'season\s(\d+)', r'\s(\d+)st\sseason\s', r'\s(\d+)nd\sseason\s',
               r'\s(\d+)rd\sseason\s', r'\s(\d+)th\sseason\s']
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
    return int(s_ids[0])
