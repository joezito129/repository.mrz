import xbmcgui, xbmcaddon, xbmcplugin
import sys
import os

from urllib import parse

try:
    HANDLE = int(sys.argv[1])
except IndexError:
    HANDLE = -1

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
__settings__ = xbmcaddon.Addon(ADDON_ID)
ADDON_NAME = __settings__.getAddonInfo('name')
ADDON_PATH = __settings__.getAddonInfo('path')

IMAGES_PATH = os.path.join(ADDON_PATH, 'resources', 'images')
ICONS_PATH = os.path.join(IMAGES_PATH, 'icons')

ADDVANCEDSETTINGS_PATH = f'{ADDON_PATH[:(-len(ADDON_ID)-8)]}userdata/advancedsettings.xml'


def setting(setting_id):
    return __settings__.getSetting(setting_id)

def opensettings():
    return ADDON.openSettings()

def textviewr_dialog(title, text):
    return xbmcgui.Dialog().textviewer(title, text)


def input_dialog(title, text=''):
    return xbmcgui.Dialog().input(title, text)


def select_dialog(title, select_list):
    return xbmcgui.Dialog().select(title, select_list)


def ok_dialog(title, text):
    return xbmcgui.Dialog().ok(title, text)


def yesno_dialog(title, text, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(title, text, nolabel=nolabel, yeslabel=yeslabel)


def multiselect_dialog(title, _list):
    return xbmcgui.Dialog().multiselect(title, _list)


def addon_url(url=''):
    return f'plugin://{ADDON_ID}/{url}'


def get_plugin_url():
    addon_base = addon_url()
    assert sys.argv[0].startswith(addon_base), "something bad happened in here"
    return sys.argv[0][len(addon_base):]


def get_plugin_params():
    return dict(parse.parse_qsl(sys.argv[2].replace('?', '')))


def xbmc_add_player_item(name, url, art=None, info=None):
    u = addon_url(url)
    liz = xbmcgui.ListItem(name)
    if info:
        liz.setInfo('video', infoLabels=info)
    if art:
        liz.setArt(art)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=u, listitem=liz, isFolder=False)


def xbmc_add_dir(name, url, art=None, info=None, draw_cm=None):
    u = addon_url(url)
    cm = (addon_url, name) if draw_cm else []

    liz = xbmcgui.ListItem(name)
    if info:
        liz.setInfo('video', info)
    if art:
        liz.setArt(art)
    if cm:
        liz.addContextMenuItems(cm)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=u, listitem=liz, isFolder=True)


def draw_items(video_data, contentType="files"):
    for vid in video_data:
        if vid['is_dir']:
            xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'])
        else:
            xbmc_add_player_item(vid['name'], vid['url'], vid['image'], vid['info'])

    xbmcplugin.setContent(HANDLE, contentType)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=True)
    return True


def allocate_item(name, url, is_dir=False, image='', info='', fanart=None, poster=None, cast=None, landscape=None,
                  banner=None, clearart=None, clearlogo=None):
    if image and '/' not in image:
        image = os.path.join(ICONS_PATH, image)

    return {
        'is_dir': is_dir,
        'image': {
            'poster': poster or image,
            'icon': image,
            'thumb': image,
            'fanart': fanart,
            'landscape': landscape,
            'banner': banner,
            'clearart': clearart,
            'clearlogo': clearlogo
        },
        'name': name,
        'url': url,
        'info': info,
        'cast': cast
    }


def print(string, *args):
    for i in list(args):
        string = f'{string} {i}'
    xbmcgui.Dialog().textviewer('print', f'{string}')
    del args, string

