import os
import random
import requests
import xbmcvfs

from resources.lib.ui import control

def allocate_item(name, url, is_dir=False, image='', info='', fanart=None, poster=None, cast=[], landscape=None, banner=None, clearart=None, clearlogo=None):
    if image and '/' not in image:
        # image = f'{control.OTAKU_ICONS_PATH}\{image}'
        image = os.path.join(control.OTAKU_ICONS_PATH, image)
    if fanart:
        fanart = random.choice(fanart)
        if '/' not in fanart:
            # fanart = f'{control.OTAKU_ICONS_PATH}\{fanart}'
            fanart = os.path.join(control.OTAKU_ICONS_PATH, fanart)
    new_res = {
        'is_dir': is_dir,
        'name': name,
        'url': url,
        'info': info,
        'cast': cast,
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
    return new_res


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

def get_season(res):
    import re
    regexes = [r'season\s(\d+)', r'\s(\d+)st\sseason\s', r'\s(\d+)nd\sseason\s',
               r'\s(\d+)rd\sseason\s', r'\s(\d+)th\sseason\s']
    s_ids = []
    if res.get('title'):
        for regex in regexes:
            if isinstance(res['title'], dict):
                s_ids += [re.findall(regex, name, re.IGNORECASE) for lang, name in res['title'].items() if name is not None]
            else:
                s_ids += [re.findall(regex, name, re.IGNORECASE) for name in res['title']]
            s_ids += [re.findall(regex, name, re.IGNORECASE) for name in res.get('synonyms')]
        s_ids = [s[0] for s in s_ids if s]
        if not s_ids:
            regex = r'\s(\d+)$'
            cour = False
            if isinstance(res['title'], dict):
                for lang, name in res['title'].items():
                    if name is not None and (' part ' in name.lower() or ' cour ' in name.lower()):
                        cour = True
                        break
                if not cour:
                    s_ids += [re.findall(regex, name, re.IGNORECASE) for lang, name in res['title'].items() if name is not None]
                    s_ids += [re.findall(regex, name, re.IGNORECASE) for name in res.get('synonyms')]
            else:
                for name in res['title']:
                    if ' part ' in name.lower() or ' cour ' in name.lower():
                        cour = True
                        break
                if not cour:
                    s_ids += [re.findall(regex, name, re.IGNORECASE) for name in res['title']]
                    s_ids += [re.findall(regex, name, re.IGNORECASE) for name in res.get('synonyms')]
            s_ids = [s[0] for s in s_ids if s]
        if not s_ids:
            seasonnum = 1
            for title in res['title'].items():
                try:
                    seasonnum = re.search(r' (\d)[ rnt][ sdh(]', f' {title[1]}  ').group(1)
                    break
                except AttributeError:
                    pass
            s_ids = [seasonnum]
    return s_ids

