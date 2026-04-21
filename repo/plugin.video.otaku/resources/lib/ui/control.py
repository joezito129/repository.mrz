import json
import random
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import sys
import os

from functools import partial
from urllib import parse
from concurrent.futures import ThreadPoolExecutor


try:
    HANDLE = int(sys.argv[1])
except IndexError:
    HANDLE = 0

addonInfo = xbmcaddon.Addon().getAddonInfo
ADDON_ID = addonInfo('id')
ADDON = xbmcaddon.Addon(ADDON_ID)
Settings = ADDON.getSettings()
lang = ADDON.getLocalizedString
addonInfo = ADDON.getAddonInfo
ADDON_NAME = addonInfo('name')
ADDON_VERSION = addonInfo('version')
ADDON_ICON = addonInfo('icon')
FANART = addonInfo('fanart')
ADDON_PATH = ADDON.getAddonInfo('path')
dataPath = xbmcvfs.translatePath(addonInfo('profile'))
# sys.path.append(dataPath)
kodi_version = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4])

cacheFile = os.path.join(dataPath, 'cache.db')
searchHistoryDB = os.path.join(dataPath, 'search.db')
malSyncDB = os.path.join(dataPath, 'malSync.db')
mappingDB = os.path.join(dataPath, 'mappings.db')
maldubDB = os.path.join(dataPath, 'mal_dub.db')

downloads_json = os.path.join(dataPath, 'downloads.json')
completed_json = os.path.join(dataPath, 'completed.json')

COMMON_PATH = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'common')
LOGO_SMALL = os.path.join(COMMON_PATH, 'trans-goku-small.png')
LOGO_MEDIUM = os.path.join(COMMON_PATH, 'trans-goku.png')
ICONS_PATH = os.path.join(ADDON_PATH, 'resources', 'images', 'icons', ADDON.getSetting("interface.icons"))

progressDialog = xbmcgui.DialogProgress()
playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
window = xbmcgui.Window(10000)
max_threads = os.cpu_count()

intro_keywords = ['intro', 'opening', 'op']
outro_keywords = ['credits']

bool_cache = {}
int_cache = {}
str_cache = {}

def closeBusyDialog() -> None:
    if xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        xbmc.executebuiltin('Dialog.Close(busydialog)')
    if xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')


def log(msg, level="info") -> None:
    if level == 'info':
        level = xbmc.LOGINFO
    elif level == 'debug':
        level = xbmc.LOGDEBUG
    elif level == 'warning':
        level = xbmc.LOGWARNING
    elif level == 'error':
        level = xbmc.LOGERROR
    elif level == 'fatal':
        level = xbmc.LOGFATAL
        # SAVE THE KIDS THE PLANE IS GOING DOWN!!
    else:
        level = xbmc.LOGNONE
    xbmc.log(f'{ADDON_NAME.upper()} ({HANDLE}): {msg}', level)


def enabled_debrid() -> list:
    debrids = ['real_debrid', 'debrid_link', 'alldebrid', 'premiumize', 'torbox']
    return [x for x in debrids if getString(f'{x}.token') != '' and getBool(f'{x}.enabled')]


def enabled_watchlists() -> list:
    watchlists = ['mal', 'anilist', 'simkl', 'kitsu']
    return [x for x in watchlists if getString(f'{x}.token') != '' and getBool(f'{x}.enabled')]


def watchlist_to_update():
    if getBool('watchlist.update.enabled'):
        flavor = getString('watchlist.update.flavor')
        if getBool(f"{flavor}.enabled"):
            return flavor
    return None


def copy2clip(txt: str) -> bool:
    import subprocess
    platform = sys.platform
    try:
        if platform == 'win32':
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=txt)
            return True
        elif platform == 'darwin':  # macOS
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=txt)
            return True
        elif platform == 'linux':
            # Linux requires xclip or xsel to be installed
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=txt)
            return True
    except Exception as e:
        log(e)
    return False


def colorstr(text, color: str = 'deepskyblue') -> str:
    return f"[COLOR {color}]{text}[/COLOR]"


def refresh() -> None:
    xbmc.executebuiltin('Container.Refresh')


def getBool(key: str) -> bool:
    if key in bool_cache:
        return bool_cache[key]
    prop_val = window.getProperty(f'{ADDON_ID}_{key}')
    if prop_val != '':
        cache = prop_val == 'true'
    else:
        cache = Settings.getBool(key)
    bool_cache[key] = cache
    return cache


def getInt(key: str) -> int:
    if key in int_cache:
        return int_cache[key]
    prop_val = window.getProperty(f'{ADDON_ID}_{key}')
    cache = int(prop_val) if prop_val else Settings.getInt(key)
    int_cache[key] = cache
    return cache


def getString(key: str) -> str:
    if key in str_cache:
        return str_cache[key]
    prop_val = window.getProperty(f'{ADDON_ID}_{key}')
    cache = prop_val if prop_val else Settings.getString(key)
    str_cache[key] = cache
    return cache

def getStringList(settingid: str) -> list:
    return Settings.getStringList(settingid)


def setSetting(settingid: str, value: str) -> None:
    ADDON.setSetting(settingid, value)


def setBool(settingid: str, value: bool) -> None:
    Settings.setBool(settingid, value)


def setInt(settingid: str, value: int) -> None:
    Settings.setInt(settingid, value)


def setString(settingid: str, value: str) -> None:
    Settings.setString(settingid, value)


def setStringList(settingid: str, value: list):
    Settings.setStringList(settingid, value)


def addon_url(url: str) -> str:
    return f"plugin://{ADDON_ID}/{url}"


def get_plugin_url(url: str) -> str:
    addon_base = addon_url('')
    return url[len(addon_base):]


def get_plugin_params(param: str) -> dict:
    return dict(parse.parse_qsl(param.replace('?', '')))


def get_payload_params(url: str) -> tuple:
    url_list = url.rsplit('?', 1)
    if len(url_list) == 1:
        url_list.append('')
    payload, params = url_list
    return get_plugin_url(payload), get_plugin_params(params)


def exit_code() -> None:
    if getString('reuselanguageinvoker.status') == 'Enabled':
        sys.exit(1)


def keyboard(title: str, text: str = '') -> str:
    keyboard_ = xbmc.Keyboard(text, title, False)
    keyboard_.doModal()
    return keyboard_.getText() if keyboard_.isConfirmed() else ""


def closeAllDialogs() -> None:
    xbmc.executebuiltin('Dialog.Close(all,true)')


def ok_dialog(title: str, text: str) -> bool:
    return xbmcgui.Dialog().ok(title, text)


def textviewer_dialog(title: str, text: str) -> None:
    xbmcgui.Dialog().textviewer(title, text)


def yesno_dialog(title: str, text: str, nolabel: str = '', yeslabel: str = '') -> bool:
    return xbmcgui.Dialog().yesno(title, text, nolabel, yeslabel)


def yesnocustom_dialog(title: str, text: str, customlabel: str = '', nolabel: str = '', yeslabel: str = '', autoclose: int = 0, defaultbutton: int = 0) -> int:
    return xbmcgui.Dialog().yesnocustom(title, text, customlabel, nolabel, yeslabel, autoclose, defaultbutton)


def notify(title: str, text: str, icon: str = LOGO_MEDIUM, time: int = 10, sound: bool = True) -> None:
    xbmcgui.Dialog().notification(title, text, icon, time, sound)


def input_dialog(title: str, input_: str = '', option: int = 0) -> str:
    return xbmcgui.Dialog().input(title, input_, option=option)


def multiselect_dialog(title: str, dialog_list: list) -> list:
    return xbmcgui.Dialog().multiselect(title, dialog_list)


def select_dialog(title: str, dialog_list: list) -> int:
    return xbmcgui.Dialog().select(title, dialog_list)


def context_menu(context_list: list) -> int:
    return xbmcgui.Dialog().contextmenu(context_list)


def browse(type_: int, heading: str, shares: str, mask: str = ''):
    return xbmcgui.Dialog().browse(type_, heading, shares, mask)


def handle_set_fanart(art: dict, fanart_disable: bool) -> dict:
    if not (image := art.get('fanart')) or fanart_disable:
        art['fanart'] = FANART
    else:
        if isinstance(image, list):
            art['fanart'] = random.choice(image)
    return art


def set_videotags(li, info) -> None:
    vinfo: xbmc.InfoTagVideo = li.getVideoInfoTag()
    try:
        vinfo.setTitle(info['title'])
    except KeyError:
        pass

    if media_type := info.get('mediatype'):
        vinfo.setMediaType(media_type)
    if tvshow_title := info.get('tvshowtitle'):
        vinfo.setTvShowTitle(tvshow_title)
    if plot := info.get('plot'):
        vinfo.setPlot(plot)
    if year := info.get('year'):
        vinfo.setYear(year)
    if premiered := info.get('premiered'):
        vinfo.setPremiered(premiered)
    if status := info.get('status'):
        vinfo.setTvShowStatus(status)
    if genre := info.get('genre'):
        vinfo.setGenres(genre)
    if mpaa := info.get('mpaa'):
        vinfo.setMpaa(mpaa)
    if rating := info.get('rating'):
        vinfo.setRating(rating.get('score', 0), rating.get('votes', 0))
    if (season := info.get('season')) is not None:
        vinfo.setSeason(season)
    if (episode := info.get('episode')) is not None:
        vinfo.setEpisode(episode)
    if aired := info.get('aired'):
        vinfo.setFirstAired(aired)
    if playcount := info.get('playcount'):
        vinfo.setPlaycount(playcount)
    if duration := info.get('duration'):
        vinfo.setDuration(duration)
    if code := info.get('code'):
        vinfo.setProductionCode(code)
    if studio := info.get('studio'):
        vinfo.setStudios(studio)
    if cast := info.get('cast'):
        vinfo.setCast([xbmc.Actor(c['name'], c['role'], c['index'], c['thumbnail']) for c in cast])
    if originaltitle := info.get('OriginalTitle'):
        vinfo.setOriginalTitle(originaltitle)
    if trailer := info.get('trailer'):
        vinfo.setTrailer(trailer)
    if uniqueids := info.get('UniqueIDs'):
        vinfo.setUniqueIDs(uniqueids)
    if resume := info.get('resume'):
        vinfo.setResumePoint(float(resume), 1)
    if properties := info.get('properties'):
        li.setProperties(properties)

def jsonrpc(json_data: dict) -> dict:
    return json.loads(xbmc.executeJSONRPC(json.dumps(json_data)))


def xbmc_add_dir(data: dict, clear_logo_disable: bool, fanart_disable: bool) -> tuple:
    url = data['url']
    u = addon_url(url)
    liz = xbmcgui.ListItem(data['name'], offscreen=True)
    if info := data['info']:
        set_videotags(liz, info)
    if draw_cm := data['cm']:
        cm = [(x[0], f'RunPlugin(plugin://{ADDON_ID}/{x[1]}/{url})') for x in draw_cm]
        liz.addContextMenuItems(cm)

    art = handle_set_fanart(data['image'], fanart_disable)

    if clear_logo_disable:
        art['clearlogo'] = ICONS_PATH
    if data['isplayable']:
        art['tvshow.poster'] = art.pop('poster')
        liz.setProperties({'Video': 'true', 'IsPlayable': 'true'})
    liz.setArt(art)
    return u, liz, data['isfolder']


def bulk_draw_items(video_data: list) -> bool:
    list_items = bulk_dir_list(video_data)
    return xbmcplugin.addDirectoryItems(HANDLE, list_items)

def wait_loop(step: int, timeout: int, path: str, path2: str=''):
    """
    :param step: Step wait time in ms
    :param timeout: max timeout time in ms
    :param path: path to match Container.FolderPath
    :param path2: path2 to match Container.FolderPath

    """
    max_loop = int(timeout / step)
    for i in range(max_loop):
        xbmc.sleep(step)
        if xbmcgui.getCurrentWindowId() == 10025:
            kodi_path = xbmc.getInfoLabel('Container.FolderPath')
            if path in kodi_path or path2 in kodi_path:
                if not xbmc.getCondVisibility("Container.IsUpdating"):
                    # log(f"Waited ({(i + 1) * step}ms) for path {kodi_path}")
                    break
    else:
        log(f"Waited ({step * max_loop}ms) for path {xbmc.getInfoLabel('Container.FolderPath')}")

def draw_items(video_data: list, content_type: str = '') -> None:
    bulk_draw_items(video_data)
    if content_type:
        xbmcplugin.setContent(HANDLE, content_type)
    if content_type == 'episodes':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%H. %T", "%R | %P")
    elif content_type == 'tvshows':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%L", "%R")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
    closeAllDialogs()
    if getBool('interface.viewtypes.bool'):
        wait_loop(100, 250, 'plugin://plugin.video.otaku/')
        if content_type == 'tvshows':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getString('interface.viewtypes.tvshows')))
        elif content_type == 'episodes':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getString('interface.viewtypes.episodes')))
        else:
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getString('interface.viewtypes.general')))

    # move to episode position currently watching
    if content_type == "episodes" and getBool('general.smart.scroll.enable'):
        wait_loop(10, 250, "plugin://plugin.video.otaku/animes", 'plugin://plugin.video.otaku/watchlist_to_ep')
        wid = xbmcgui.getCurrentWindowId()
        current_window = xbmcgui.Window(wid)
        active_id = current_window.getFocusId()
        try:
            num_watched = int(xbmc.getInfoLabel("Container.TotalWatched"))
            total_ep = int(xbmc.getInfoLabel('Container.NumItems'))
            all_items = int(xbmc.getInfoLabel('Container.NumAllItems'))
            offset = 1 if all_items > total_ep else 0
            target_index = num_watched + offset
        except ValueError:
            return
        if 0 < target_index < all_items:
            xbmc.executebuiltin('Action(firstpage)')
            xbmc.executebuiltin(f'Control.SetFocus({active_id}, {target_index})')


def bulk_dir_list(video_data: list) -> list:
    clear_logo_disable = getBool('interface.clearlogo.disable')
    fanart_disable = getBool('interface.fanart.disable')
    mapfunc = partial(xbmc_add_dir, clear_logo_disable=clear_logo_disable, fanart_disable=fanart_disable)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        list_items = list(executor.map(mapfunc, filter(None, video_data)))
    return list_items


def get_view_type(viewtype: str) -> int:
    viewTypes = {
        'Default': 50,
        'Poster': 51,
        'Icon Wall': 52,
        'Shift': 53,
        'Info Wall': 54,
        'Wide List': 55,
        'Wall': 500,
        'Banner': 501,
        'Fanart': 502,
        'List': 0
    }
    return viewTypes[viewtype]

def is_addon_visible() -> bool:
    return xbmc.getInfoLabel('Container.PluginName') == 'plugin.video.otaku'


def is_video_window_open():
    return False if xbmcgui.getCurrentWindowId() != 12005 else True


def json_res(response):
    try:
        response = response.json()
    except:
        response = {}
    return response


def process_context():
    context_settings = [
        "context.otaku.findrecommendations",
        "context.otaku.findrelations",
        "context.otaku.rescrape",
        "context.otaku.sourceselect",
        "context.otaku.logout",
        'context.otaku.deletefromdatabase',
        'context.otaku.watchlist',
        'context.otaku.markedaswatched'
    ]
    for s_id in context_settings:
        try:
            cache_val = window.getProperty(s_id)
            val = ADDON.getSettingBool(s_id)
            if cache_val != val:
                window.setProperty(s_id, str(val))
        except:
            log(s_id, 'error')


# def print(string, *args) -> None:
#     for i in list(args):
#         string = f'{string} {i}'
#     textviewer_dialog('print', f'{string}')
#     del args, string

def timeIt(func):
    # Thanks to 123Venom
    import time
    def wrap(*args, **kwargs):
        started_at = time.perf_counter()
        result = func(*args, **kwargs)
        log(f">> {__name__}.{func.__name__} <<: {time.perf_counter() - started_at}")
        return result
    return wrap
