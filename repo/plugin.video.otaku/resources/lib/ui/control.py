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
settings = xbmcaddon.Addon(ADDON_ID)
language = settings.getLocalizedString
addonInfo = settings.getAddonInfo
ADDON_NAME = addonInfo('name')
ADDON_VERSION = addonInfo('version')
ADDON_ICON = addonInfo('icon')
OTAKU_FANART = addonInfo('fanart')
ADDON_PATH = settings.getAddonInfo('path')
dataPath = xbmcvfs.translatePath(addonInfo('profile'))
kodi_version = xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')

cacheFile = os.path.join(dataPath, 'cache.db')
searchHistoryDB = os.path.join(dataPath, 'search.db')
anilistSyncDB = os.path.join(dataPath, 'anilistSync.db')
mappingDB = os.path.join(dataPath, 'mappings.db')

maldubFile = os.path.join(dataPath, 'mal_dub.json')
downloads_json = os.path.join(dataPath, 'downloads.json')
completed_json = os.path.join(dataPath, 'completed.json')

OTAKU_LOGO2_PATH = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'common', 'trans-goku-small.png')
OTAKU_ICONS_PATH = os.path.join(ADDON_PATH, 'resources', 'images', 'icons', settings.getSetting("interface.icons"))

dialogWindow = xbmcgui.WindowDialog
xmlWindow = xbmcgui.WindowXMLDialog
menuItem = xbmcgui.ListItem
execute = xbmc.executebuiltin
progressDialog = xbmcgui.DialogProgress()
playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)


def closeBusyDialog():
    if xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        execute('Dialog.Close(busydialog)')
    if xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
        execute('Dialog.Close(busydialognocancel)')


def log(msg, level="info"):
    if level == 'info':
        level = xbmc.LOGINFO
    elif level == 'warning':
        level = xbmc.LOGWARNING
    elif level == 'error':
        level = xbmc.LOGERROR
    else:
        level = xbmc.LOGNONE
    xbmc.log(f'{ADDON_NAME.upper()} ({HANDLE}): {msg}', level)


def try_release_lock(lock):
    if lock.locked():
        lock.release()


def real_debrid_enabled():
    return True if getSetting('rd.auth') != '' and getSetting('realdebrid.enabled') == 'true' else False


def debrid_link_enabled():
    return True if getSetting('dl.auth') != '' and getSetting('dl.enabled') == 'true' else False


def all_debrid_enabled():
    return True if getSetting('alldebrid.apikey') != '' and getSetting('alldebrid.enabled') == 'true' else False


def premiumize_enabled():
    return True if getSetting('premiumize.token') != '' and getSetting('premiumize.enabled') == 'true' else False


def myanimelist_enabled():
    return True if getSetting('mal.token') != '' and getSetting('mal.enabled') == 'true' else False


def kitsu_enabled():
    return True if getSetting('kitsu.token') != '' and getSetting('kitsu.enabled') == 'true' else False


def anilist_enabled():
    return True if getSetting('anilist.token') != '' and getSetting('anilist.enabled') == 'true' else False


def simkl_enabled():
    return True if getSetting('simkl.token') != '' and getSetting('simkl.enabled') == 'true' else False


def watchlist_to_update():
    if bools.watchlist_update:
        flavor = getSetting('watchlist.update.flavor').lower()
        if getSetting('%s.enabled' % flavor) == 'true':
            return flavor


def copy2clip(txt):
    platform = sys.platform
    if platform == 'win32':
        command = 'echo %s|clip' % txt
        os.system(command)


def colorString(text, color=None):
    if color == 'default' or color == '' or color is None:
        color = 'deepskyblue'
    return f"[COLOR {color}]{text}[/COLOR]"


def refresh():
    return execute('Container.Refresh')


def getSetting(key):
    return settings.getSetting(key)


def setSetting(settingid, value):
    return settings.setSetting(settingid, value)


def lang(x):
    return language(x)


def addon_url(url):
    return f'plugin://{ADDON_ID}/{url}'


def get_plugin_url():
    addon_base = addon_url('')
    return sys.argv[0][len(addon_base):]


def get_plugin_params():
    return dict(parse.parse_qsl(sys.argv[2].replace('?', '')))


def keyboard(text):
    keyboard_ = xbmc.Keyboard('', text, False)
    keyboard_.doModal()
    if keyboard_.isConfirmed():
        return keyboard_.getText()


def closeAllDialogs():
    execute('Dialog.Close(all,true)')


def ok_dialog(title, text):
    return xbmcgui.Dialog().ok(title, text)


def textviewer_dialog(title, text):
    return xbmcgui.Dialog().textviewer(title, text)


def yesno_dialog(title, text, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(title, text, nolabel, yeslabel)


def yesnocustom_dialog(title, text, customlabel='', nolabel='', yeslabel='', autoclose=0, defaultbutton=0):
    return xbmcgui.Dialog().yesnocustom(title, text, customlabel, nolabel, yeslabel, autoclose, defaultbutton)


def notify(title, text, icon=OTAKU_LOGO2_PATH, time=5000, sound=True):
    return xbmcgui.Dialog().notification(title, text, icon, time, sound)


def multiselect_dialog(title, dialog_list):
    return xbmcgui.Dialog().multiselect(title, dialog_list)


def select_dialog(title, dialog_list):
    return xbmcgui.Dialog().select(title, dialog_list)


def context_menu(context_list):
    return xbmcgui.Dialog().contextmenu(context_list)


def set_videotags(li, info):
    vinfo = li.getVideoInfoTag()
    if info.get('title'):
        vinfo.setTitle(info['title'])
    if info.get('mediatype'):
        vinfo.setMediaType(info['mediatype'])
    if info.get('tvshowtitle'):
        vinfo.setTvShowTitle(info['tvshowtitle'])
    if info.get('plot'):
        vinfo.setPlot(info['plot'])
    if info.get('year'):
        vinfo.setYear(info['year'])
    if info.get('premiered'):
        vinfo.setPremiered(info['premiered'])
    if info.get('status'):
        vinfo.setTvShowStatus(info['status'])
    if info.get('genre'):
        vinfo.setGenres(info['genre'])
    if info.get('mpaa'):
        vinfo.setMpaa(info['mpaa'])
    if info.get('rating'):
        vinfo.setRating(info['rating'])
    if info.get('season'):
        vinfo.setSeason(info['season'])
    if info.get('episode'):
        vinfo.setEpisode(info['episode'])
    if info.get('aired'):
        vinfo.setFirstAired(info['aired'])
    if info.get('playcount'):
        vinfo.setPlaycount(info['playcount'])
    if info.get('code'):
        vinfo.setProductionCode(info['code'])
    if info.get('cast'):
        vinfo.setCast([xbmc.Actor(c['name'], c['role'], c['index'], c['thumbnail']) for c in info['cast']])
    if info.get('OriginalTitle'):
        vinfo.setOriginalTitle(info['OriginalTitle'])
    if info.get('trailer'):
        vinfo.setTrailer(info['trailer'])
    if info.get('UniqueIDs'):
        # vinfo.setUniqueIDs(info['UniqueIDs'], 'anilist_id')
        vinfo.setUniqueIDs(info['UniqueIDs'])


def xbmc_add_dir(name, url, art, info, draw_cm, bulk_add, isfolder, isplayable):
    u = addon_url(url)
    liz = xbmcgui.ListItem(name, offscreen=True)
    if info:
        set_videotags(liz, info)
    if draw_cm:
        cm = [(x[0], f'RunPlugin(plugin://{ADDON_ID}/{x[1]}/{url})') for x in draw_cm]
        liz.addContextMenuItems(cm)

    if art.get('fanart') is None or bools.fanart_disable:
        art['fanart'] = OTAKU_FANART
    else:
        if isinstance(art['fanart'], list):
            if bools.fanart_select:
                if info.get('UniqueIDs', {}).get('anilist_id'):
                    fanart_select = getSetting(f'fanart.select.anilist.{info["UniqueIDs"]["anilist_id"]}')
                    art['fanart'] = fanart_select if fanart_select else random.choice(art['fanart'])
                else:
                    art['fanart'] = OTAKU_FANART
            else:
                art['fanart'] = random.choice(art['fanart'])

    if bools.clearlogo_disable:
        art['clearlogo'] = OTAKU_ICONS_PATH
    if isplayable:
        art['tvshow.poster'] = art.pop('poster')
        liz.setProperties({'Video': 'true', 'IsPlayable': 'true'})
    liz.setArt(art)

    return u, liz, isfolder if bulk_add else xbmcplugin.addDirectoryItem(HANDLE, u, liz, isfolder)


def bulk_draw_items(video_data, draw_cm):
    list_items = [xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, True, vid['isfolder'], vid['isplayable']) for vid in video_data]
    xbmcplugin.addDirectoryItems(HANDLE, list_items)


def draw_items(video_data, content_type=None, draw_cm=None):
    if not draw_cm:
        draw_cm = []
    if content_type == 'tvshows':
        if bools.context_watchlist:
            draw_cm.append(("WatchList", "watchlist_context"))
        if bools.context_deletefromdatabase:
            draw_cm.append(("Delete from database", 'delete_anime_database'))
        if bools.fanart_select:
            draw_cm.append(('Select Fanart', 'select_fanart'))
    elif content_type == 'episodes':
        if bools.context_marked_watched:
            draw_cm.append(("Marked as Watched [COLOR blue]WatchList[/COLOR]", 'marked_as_watched'))

    # if len(video_data) > 99:
    #     bulk_draw_items(video_data, draw_cm)
    # else:
    for vid in video_data:
        xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, False, vid['isfolder'], vid['isplayable'])

    if content_type:
        xbmcplugin.setContent(HANDLE, content_type)

    if content_type == 'episodes':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%H. %T", "%R | %P")
    elif content_type == 'tvshows':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%L", "%R")
    xbmcplugin.endOfDirectory(HANDLE, True, False, True)
    if bools.viewtypes:
        if content_type == 'tvshows':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.tvshows')))
        elif content_type == 'episodes':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.episodes')))
        else:
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.general')))
    # move to episode position currently watching
    if content_type == "episodes" and bools.smart_scroll:
        xbmc.sleep(int(getSetting('general.smart.scroll.time')))
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


def bulk_player_list(video_data, draw_cm=None, bulk_add=True):
    return [xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, bulk_add, vid['isfolder'], vid['isplayable']) for vid in video_data]


def get_view_type(viewtype):
    # viewtypes = [50, 51, 53, 54, 55, 500, 501, 502]
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


def title_lang(title_key):
    title_lang_dict = ["romaji", 'english']
    return title_lang_dict[title_key]


def exit_(code):
    sys.exit(code)


def getChangeLog():
    addon_version = xbmcaddon.Addon('plugin.video.otaku').getAddonInfo('version')
    changelog_file = f'{ADDON_PATH}changelog.txt'

    # Read changelog file
    with open(changelog_file, encoding='utf-8', errors='ignore') as f:
        changelog_text = f.read()

    # Combine changelog and news text
    heading = '[B]%s -  v%s - ChangeLog[/B]' % (ADDON_NAME, addon_version)
    from resources.lib.windows.textviewer import TextViewerXML
    windows = TextViewerXML('textviewer.xml', ADDON_PATH, heading=heading, text=changelog_text)
    windows.run()
    del windows


def toggle_reuselanguageinvoker():
    def _store_and_reload(output):
        with open(file_path, "w+") as addon_xml_:
            addon_xml_.writelines(output)
        ok_dialog(ADDON_NAME, 'Language Invoker option has been changed, reloading kodi profile')
        execute('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))
    file_path = os.path.join(ADDON_PATH, "addon.xml")
    with open(file_path) as addon_xml:
        file_lines = addon_xml.readlines()
    for i in range(len(file_lines)):
        line_string = file_lines[i]
        if "reuselanguageinvoker" in file_lines[i]:
            if "false" in line_string:
                file_lines[i] = file_lines[i].replace("false", "true")
                setSetting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            elif "true" in line_string:
                file_lines[i] = file_lines[i].replace("true", "false")
                setSetting("reuselanguageinvoker.status", "Disabled")
                _store_and_reload(file_lines)
            break


def is_addon_visible():
    return xbmc.getInfoLabel('Container.PluginName') == 'plugin.video.otaku'


def abort_requested():
    monitor = xbmc.Monitor()
    abort_requested_ = monitor.abortRequested()
    del monitor
    return abort_requested_


def print(string, *args):
    for i in list(args):
        string = f'{string} {i}'
    textviewer_dialog('print', f'{string}')
    del args, string


def print_(string, *args):
    for i in list(args):
        string = f'{string} {i}'

    from resources.lib.windows.textviewer import TextViewerXML
    windows = TextViewerXML('textviewer.xml', ADDON_PATH, heading=ADDON_NAME, text=f'{string}')
    windows.run()
    del windows


class Bools:
    def __init__(self):
        self.showuncached = getSetting('show.uncached') == 'true'
        self.smart_scroll = getSetting('general.smart.scroll.enable') == 'true'
        self.viewtypes = getSetting('interface.viewtypes.bool') == 'true'
        self.clearlogo_disable = getSetting('interface.clearlogo.disable') == 'true'
        self.fanart_disable = getSetting('interface.fanart.disable') == 'true'
        self.context_marked_watched = getSetting('context.marked.watched') == 'true'
        self.context_watchlist = getSetting('context.WatchList') == 'true'
        self.context_deletefromdatabase = getSetting('context.deletefromdatabase') == 'true'
        self.context_marked_watched = getSetting('context.deletefromdatabase') == 'true'
        self.watchlist_update = getSetting('watchlist.update.enabled') == 'true'
        self.watchlist_sync = getSetting('watchlist.sync.enabled') == 'true'
        self.filler = getSetting('jz.filler') == 'true'
        self.clean_titles = getSetting('interface.cleantitles') == 'true'
        self.show_empty_eps = getSetting('interface.showemptyeps') == 'true'
        self.terminateoncloud = getSetting('general.terminate.oncloud') == 'true'
        self.div_flavor = getSetting("divflavors.bool") == "true"
        self.search_adult = getSetting('search.adult') == "true"
        self.fanart_select = getSetting('interface.fanart.select.bool') == 'true'
        self.watchlist_data = getSetting('interface.watchlist.data') == 'true'


bools = Bools()
