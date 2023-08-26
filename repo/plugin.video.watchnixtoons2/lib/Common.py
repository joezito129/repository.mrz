# -*- coding: utf-8 -*-

import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json

try:
    import md5
except ImportError:
    from hashlib import md5

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')

def print(string, *args):
    for i in list(args):
        string = f'{string} {i}'
    xbmcgui.Dialog().textviewer('print', f'{string}')
    del args, string

def getWindowProperty(prop):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    data = window.getProperty(prop)
    return json.loads(data) if data else None

def setWindowProperty(prop, data):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    temp = json.dumps(data)
    window.setProperty(prop, temp)

def clearWindowProperty(prop):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    window.clearProperty(prop)

def testWindowProperty(prop):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    return window.getProperty(prop) != ''

def getRawWindowProperty(prop):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    return window.getProperty(prop)

def setRawWindowProperty(prop, data):
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    window.setProperty(prop, data)


def setViewMode():
    if ADDON.getSetting('useViewMode') == 'true':
        view_mode_id = ADDON.getSetting('viewModeID')
        if view_mode_id.isdigit():
            xbmc.executebuiltin('Container.SetViewMode(' + view_mode_id + ')')


def unescapeHTMLText(text):
    # Unescape HTML entities.
    if r'&#' in text:
        # Strings found by regex-searching on all lists in the source website.
        # It's very likely to only be these.
        text = text.replace(r'&#8216;', '‘').replace(r'&#8221;', '”').replace(r'&#8211;', '–')\
            .replace(r'&#038;', '&').replace(r'&#8217;', '’').replace(r'&#8220;', '“')\
            .replace(r'&#8230;', '…').replace(r'&#160;', ' ')

    return text.replace(r'&amp;', '&').replace(r'&quot;', '"').replace('\u2606', ' ')


def xbmcDebug(*args):
    xbmc.log('WatchNixtoons2 > ' + ' '.join((val if isinstance(val, str) else repr(val)) for val in args), xbmc.LOGWARNING)


def item_set_info(line_item, properties):
    vidtag = line_item.getVideoInfoTag()
    if properties.get('title'):
        vidtag.setTitle( properties['title'])
    if properties.get('plot'):
        vidtag.setPlot(properties['plot'])
    if properties.get('tvshowtitle'):
        vidtag.setTvShowTitle( properties['tvshowtitle'])
    if properties.get('season'):
        vidtag.setSeason(properties['season'])
    if properties.get('episode'):
        vidtag.setEpisode(properties['episode'])
    if properties.get('mediatype'):
        vidtag.setMediaType(properties['mediatype'])


# method to translate path for both PY2 & PY3
# stops all the if else statements
def translate_path(path):
    return xbmcvfs.translatePath( path )

def ensure_path_exists(path):

    """ creates path if doesn't exist """

    addon_data_path = translate_path(path)

    if os.path.exists(addon_data_path) is False:
        os.mkdir(addon_data_path)
        xbmc.sleep(1)
        return True
    return False

# generates a MD5 hash
def generateMd5(strToMd5):
    md5_instance = md5()
    strToMd5 = bytes(strToMd5, 'UTF-8')
    md5_instance.update(strToMd5)
    return md5_instance.hexdigest()

def toggle_reuselanguageinvoker(forced_state=None):
    import os
    import xbmc

    def _store_and_reload(output):
        with open(file_path, "w+") as addon_xml_:
            addon_xml_.writelines(output)
        xbmcgui.Dialog().ok(ADDON_NAME, 'Language Invoker option has been changed, reloading kodi profile')
        xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))

    file_path = os.path.join(ADDON_PATH, "addon.xml")

    with open(file_path, "r") as addon_xml:
        file_lines = addon_xml.readlines()

    for i in range(len(file_lines)):
        line_string = file_lines[i]
        if "reuselanguageinvoker" in file_lines[i]:
            if ("false" in line_string and forced_state is None) or ("false" in line_string and forced_state):
                file_lines[i] = file_lines[i].replace("false", "true")
                ADDON.setSetting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            elif ("true" in line_string and forced_state is None) or ("true" in line_string and forced_state is False):
                file_lines[i] = file_lines[i].replace("true", "false")
                ADDON.setSetting("reuselanguageinvoker.status", "Disabled")
                _store_and_reload(file_lines)
            break