import random
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import os
import sys

from urllib import parse

try:
    HANDLE = int(sys.argv[1])
except IndexError:
    HANDLE = 0

addonInfo = xbmcaddon.Addon().getAddonInfo
ADDON_ID = addonInfo('id')
ADDON = xbmcaddon.Addon(ADDON_ID)
language = ADDON.getLocalizedString
addonInfo = ADDON.getAddonInfo
ADDON_NAME = addonInfo('name')
ADDON_VERSION = addonInfo('version')
ADDON_ICON = addonInfo('icon')
FANART = addonInfo('fanart')
ADDON_PATH = ADDON.getAddonInfo('path')
dataPath = xbmcvfs.translatePath(addonInfo('profile'))
kodi_version = xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')

cacheFile = os.path.join(dataPath, 'cache.db')
searchHistoryDB = os.path.join(dataPath, 'search.db')
malSyncDB = os.path.join(dataPath, 'malSync.db')
mappingDB = os.path.join(dataPath, 'mappings.db')

maldubFile = os.path.join(dataPath, 'mal_dub.json')
downloads_json = os.path.join(dataPath, 'downloads.json')
completed_json = os.path.join(dataPath, 'completed.json')

COMMON_PATH = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'common')
LOGO_SMALL = os.path.join(COMMON_PATH, 'trans-goku-small.png')
LOGO_MEDIUM = os.path.join(COMMON_PATH, 'trans-goku.png')
ICONS_PATH = os.path.join(ADDON_PATH, 'resources', 'images', 'icons', ADDON.getSetting("interface.icons"))

dialogWindow = xbmcgui.WindowDialog
execute = xbmc.executebuiltin
progressDialog = xbmcgui.DialogProgress()
playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)


def closeBusyDialog() -> None:
    if xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        execute('Dialog.Close(busydialog)')
    if xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
        execute('Dialog.Close(busydialognocancel)')


def log(msg: str, level: str = "info") -> None:
    if level == 'info':
        level = xbmc.LOGINFO
    elif level == 'warning':
        level = xbmc.LOGWARNING
    elif level == 'error':
        level = xbmc.LOGERROR
    else:
        level = xbmc.LOGNONE
    xbmc.log(f'{ADDON_NAME.upper()} ({HANDLE}): {msg}', level)


def real_debrid_enabled() -> bool:
    return True if getSetting('rd.auth') != '' and getBool('rd.enabled') else False


def debrid_link_enabled() -> bool:
    return True if getSetting('dl.auth') != '' and getBool('dl.enabled') else False


def all_debrid_enabled() -> bool:
    return True if getSetting('alldebrid.apikey') != '' and getBool('alldebrid.enabled') else False


def premiumize_enabled() -> bool:
    return True if getSetting('premiumize.token') != '' and getBool('premiumize.enabled') else False


def myanimelist_enabled() -> bool:
    return True if getSetting('mal.token') != '' and getBool('mal.enabled') else False


def kitsu_enabled() -> bool:
    return True if getSetting('kitsu.token') != '' and getBool('kitsu.enabled') else False


def anilist_enabled() -> bool:
    return True if getSetting('anilist.token') != '' and getBool('anilist.enabled') else False


def simkl_enabled() -> bool:
    return True if getSetting('simkl.token') != '' and getBool('simkl.enabled') else False


def watchlist_to_update() -> str:
    if getBool('watchlist.update.enabled'):
        flavor = getSetting('watchlist.update.flavor').lower()
        if getBool('%s.enabled' % flavor):
            return flavor


def copy2clip(txt: str) -> bool:
    platform = sys.platform
    if platform == 'win32':
        try:
            os.system('echo %s|clip' % txt)
            return True
        except AttributeError:
            pass
    return False


def colorstr(text, color: str = 'deepskyblue') -> str:
    return f"[COLOR {color}]{text}[/COLOR]"


def refresh() -> None:
    execute('Container.Refresh')


def getSetting(key: str) -> str:
    return ADDON.getSetting(key)


def getBool(key: str) -> bool:
    return ADDON.getSettingBool(key)


def getInt(key: str) -> int:
    return ADDON.getSettingInt(key)


def getString(key: str) -> str:
    return ADDON.getSettingString(key)


def setSetting(settingid: str, value: str) -> None:
    ADDON.setSetting(settingid, value)


def setBool(settingid: str, value: bool) -> bool:
    return ADDON.setSettingBool(settingid, value)


def setInt(settingid: str, value: int) -> bool:
    return ADDON.setSettingInt(settingid, value)


def lang(x: int) -> str:
    return language(x)


def addon_url(url: str) -> str:
    return f'plugin://{ADDON_ID}/{url}'


def get_plugin_url() -> str:
    addon_base = addon_url('')
    return sys.argv[0][len(addon_base):]


def get_plugin_params() -> dict:
    return dict(parse.parse_qsl(sys.argv[2].replace('?', '')))


def exit_code() -> None:
    if getSetting('reuselanguageinvoker.status') == 'Enabled':
        exit_(1)


def keyboard(title: str, text: str = '') -> str:
    keyboard_ = xbmc.Keyboard(text, title, False)
    keyboard_.doModal()
    return keyboard_.getText() if keyboard_.isConfirmed() else ""


def closeAllDialogs() -> None:
    execute('Dialog.Close(all,true)')


def ok_dialog(title: str, text: str) -> bool:
    return xbmcgui.Dialog().ok(title, text)


def textviewer_dialog(title: str, text: str) -> None:
    xbmcgui.Dialog().textviewer(title, text)


def yesno_dialog(title: str, text: str, nolabel: str = '', yeslabel: str = '') -> bool:
    return xbmcgui.Dialog().yesno(title, text, nolabel, yeslabel)


def yesnocustom_dialog(title: str, text: str, customlabel: str = '', nolabel: str = '', yeslabel: str = '', autoclose: int = 0, defaultbutton: int = 0) -> int:
    return xbmcgui.Dialog().yesnocustom(title, text, customlabel, nolabel, yeslabel, autoclose, defaultbutton)


def notify(title: str, text: str, icon: str = LOGO_MEDIUM, time: int = 5000, sound: bool = True) -> None:
    xbmcgui.Dialog().notification(title, text, icon, time, sound)


def multiselect_dialog(title: str, dialog_list: list) -> list[int]:
    return xbmcgui.Dialog().multiselect(title, dialog_list)


def select_dialog(title: str, dialog_list: list) -> int:
    return xbmcgui.Dialog().select(title, dialog_list)


def context_menu(context_list: list) -> int:
    return xbmcgui.Dialog().contextmenu(context_list)


def browse(type_: int, heading: str, shares: str, mask: str = '') -> str:
    return xbmcgui.Dialog().browse(type_, heading, shares, mask)


def set_videotags(li, info: dict) -> None:
    vinfo = li.getVideoInfoTag()
    if title := info.get('title'):
        vinfo.setTitle(title)
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
    if season := info.get('season'):
        vinfo.setSeason(season)
    if episode := info.get('episode'):
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
    # if info.get('resume'):
    #     vinfo.setResumePoint(info['resume'], 0)


def xbmc_add_dir(name: str, url: str, art, info: dict, draw_cm: list, bulk_add: bool, isfolder: bool, isplayable: bool):
    u = addon_url(url)
    liz = xbmcgui.ListItem(name, offscreen=True)
    if info:
        set_videotags(liz, info)
    if draw_cm:
        cm = [(x[0], f'RunPlugin(plugin://{ADDON_ID}/{x[1]}/{url})') for x in draw_cm]
        liz.addContextMenuItems(cm)
    if not art.get('fanart') or settingids.fanart_disable:
        art['fanart'] = FANART
    else:
        if isinstance(art['fanart'], list):
            if settingids.fanart_select:
                if info.get('UniqueIDs', {}).get('mal_id'):
                    fanart_select = getSetting(f'fanart.select.{info["UniqueIDs"]["mal_id"]}')
                    art['fanart'] = fanart_select if fanart_select else random.choice(art['fanart'])
                else:
                    art['fanart'] = FANART
            else:
                art['fanart'] = random.choice(art['fanart'])

    if settingids.clearlogo_disable:
        art['clearlogo'] = ICONS_PATH
    if isplayable:
        art['tvshow.poster'] = art.pop('poster')
        liz.setProperties({'Video': 'true', 'IsPlayable': 'true'})
    liz.setArt(art)
    return u, liz, isfolder if bulk_add else xbmcplugin.addDirectoryItem(HANDLE, u, liz, isfolder)


def bulk_draw_items(video_data: list, draw_cm: list) -> bool:
    list_items = [xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, True, vid['isfolder'], vid['isplayable']) for vid in video_data if vid]
    return xbmcplugin.addDirectoryItems(HANDLE, list_items)


def draw_items(video_data: list, content_type: str = '', draw_cm: list = None) -> None:
    if not draw_cm:
        draw_cm = []
    if len(video_data) > 99:
        bulk_draw_items(video_data, draw_cm)
    else:
        for vid in video_data:
            if vid:
                xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, False, vid['isfolder'], vid['isplayable'])
    if content_type:
        xbmcplugin.setContent(HANDLE, content_type)
    if content_type == 'episodes':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%H. %T", "%R | %P")
    elif content_type == 'tvshows':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%L", "%R")
    xbmcplugin.endOfDirectory(HANDLE, True, False, True)
    xbmc.sleep(100)
    if content_type == 'episodes':
        for _ in range(20):
            if xbmc.getCondVisibility("Container.HasFiles"):
                break
            xbmc.sleep(100)
    if getBool('interface.viewtypes.bool'):
        if content_type == 'tvshows':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.tvshows')))
        elif content_type == 'episodes':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.episodes')))
        else:
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.general')))

    # move to episode position currently watching
    if content_type == "episodes" and getBool('general.smart.scroll.enable'):
        try:
            num_watched = int(xbmc.getInfoLabel("Container.TotalWatched"))
            total_ep = int(xbmc.getInfoLabel('Container(id).NumItems'))
            total_items = int(xbmc.getInfoLabel('Container(id).NumAllItems'))
            if total_items == total_ep + 1:
                num_watched += 1
                total_ep += 1
        except ValueError:
            return
        if total_ep > num_watched > 0:
            xbmc.executebuiltin('Action(firstpage)')
            for _ in range(num_watched):
                xbmc.executebuiltin('Action(Down)')


def bulk_player_list(video_data: list, draw_cm: list = None, bulk_add: bool = True) -> list:
    return [xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, bulk_add, vid['isfolder'], vid['isplayable']) for vid in video_data if vid]


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


def exit_(code: int) -> None:
    sys.exit(code)


def is_addon_visible() -> bool:
    return xbmc.getInfoLabel('Container.PluginName') == 'plugin.video.otaku'


def abort_requested() -> bool:
    monitor = xbmc.Monitor()
    abort_requested_ = monitor.abortRequested()
    del monitor
    return abort_requested_


def wait_for_abort(timeout: float = 1.0) -> bool:
    monitor = xbmc.Monitor()
    abort_requested_ = monitor.waitForAbort(timeout)
    del monitor
    return abort_requested_


def print(string, *args) -> None:
    for i in list(args):
        string = f'{string} {i}'
    textviewer_dialog('print', f'{string}')
    del args, string


class SettingIDs:
    def __init__(self):
        # Bools
        self.showuncached = getBool('show.uncached')
        self.clearlogo_disable = getBool('interface.clearlogo.disable')
        self.fanart_disable = getBool('interface.fanart.disable')
        self.filler = getBool('jz.filler')
        self.clean_titles = getBool('interface.cleantitles')
        self.dubonly = getBool("divflavors.dubonly")
        self.showdub = getBool("divflavors.showdub")
        self.watchlist_data = getBool('interface.watchlist.data')
        self.fanart_select = getBool('context.otaku.fanartselect')

        # Ints

        # Str


settingids = SettingIDs()
