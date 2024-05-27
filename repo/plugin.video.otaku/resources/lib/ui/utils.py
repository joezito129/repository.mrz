import os
import random
import requests
import xbmcvfs

from resources.lib.ui import control


def allocate_item(name, url, is_dir=False, image='', info='', fanart=None, poster=None, cast=[], landscape=None,
                  banner=None, clearart=None, clearlogo=None):
    if image and '/' not in image:
        image = os.path.join(control.OTAKU_ICONS_PATH, image)
    if fanart:
        fanart = random.choice(fanart)
        if '/' not in fanart:
            fanart = os.path.join(control.OTAKU_ICONS_PATH, fanart)
    # if poster and '/' not in poster:
    #     poster = os.path.join(control.OTAKU_ICONS_PATH, poster)
    new_res = {
        'is_dir': is_dir,
        'name': name,
        'url': url,
        'info': info,
        'cast': cast,
        'image': {
                'poster': image,
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
            is_dir=is_dir,
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
            is_dir=is_dir,
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
    subtitle = control.TRANSLATEPATH('special://temp/')
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


def database_request_post(url, headers=None, data=None, timeout=None):
    r = requests.post(url, headers=headers, data=data, timeout=timeout)
    if r.ok:
        return r.json()


def database_request_get(url, params=None, headers=None, timeout=None, text=False):
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    if r.ok:
        if text:
            return r.text
        return r.json()


def randomagent():
    _agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:56.0) Gecko/20100101 Firefox/56.0',
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36 OPR/43.0.2442.991',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:54.0) Gecko/20100101 Firefox/54.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    ]
    return random.choice(_agents)


def randommobileagent():
    _mobagents = [
        'Mozilla/5.0 (Linux; Android 7.1; vivo 1716 Build/N2G47H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.98 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; U; Android 6.0.1; zh-CN; F5121 Build/34.0.A.1.247) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/40.0.2214.89 UCBrowser/11.5.1.944 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 7.0; SAMSUNG SM-N920C Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/6.2 Chrome/56.0.2924.87 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 11_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Version/10.0 Mobile/14D27 Safari/602.1'
    ]
    return random.choice(_mobagents)
