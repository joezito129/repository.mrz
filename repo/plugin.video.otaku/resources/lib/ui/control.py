import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import os
import sys

from urllib import parse

try:
    HANDLE = int(sys.argv[1])
except IndexError:
    HANDLE = -1

addonInfo = xbmcaddon.Addon().getAddonInfo
ADDON_ID = addonInfo('id')
__settings__ = xbmcaddon.Addon(ADDON_ID)
__language__ = __settings__.getLocalizedString
addonInfo = __settings__.getAddonInfo
ADDON_NAME = addonInfo('name')
ADDON_ICON = addonInfo('icon')
ADDON_PATH = __settings__.getAddonInfo('path')
dataPath = xbmcvfs.translatePath(addonInfo('profile'))


cacheFile = os.path.join(dataPath, 'cache.db')
searchHistoryDB = os.path.join(dataPath, 'search.db')
anilistSyncDB = os.path.join(dataPath, 'anilistSync.db')
torrentScrapeCacheFile = os.path.join(dataPath, 'torrentScrape.db')
mappingDB = os.path.join(dataPath, 'mappings.db')

maldubFile = os.path.join(dataPath, 'mal_dub.json')
downloads_json = os.path.join(dataPath, 'downloads.json')
completed_json = os.path.join(dataPath, 'completed.json')

IMAGES_PATH = os.path.join(ADDON_PATH, 'resources', 'images')
OTAKU_FANART_PATH = os.path.join(ADDON_PATH, 'fanart.jpg')
OTAKU_LOGO2_PATH = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'common', 'trans-goku-small.png')
OTAKU_ICONS_PATH = os.path.join(IMAGES_PATH, 'icons', __settings__.getSetting("interface.icons"))

dialogWindow = xbmcgui.WindowDialog
xmlWindow = xbmcgui.WindowXMLDialog
menuItem = xbmcgui.ListItem
execute = xbmc.executebuiltin
progressDialog = xbmcgui.DialogProgress()
playList = xbmc.PlayList(1)


def closeBusyDialog():
    if xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        execute('Dialog.Close(busydialog)')
    if xbmc.getCondVisibility('Window.IsActive(busydialognocancel)'):
        execute('Dialog.Close(busydialognocancel)')


def log(msg, level="info"):
    level = xbmc.LOGINFO if level == "info" else xbmc.LOGDEBUG

    bottom_header = '##################'
    bottom_header = bottom_header.ljust(len(bottom_header) + len(msg), '#')

    top_header = ''.ljust(int(len(bottom_header) / 2), "#")
    top_header += ' Otaku log '
    top_header = top_header.ljust(len(top_header) + int(len(bottom_header) / 2), '#')
    bottom_header = bottom_header.ljust(len(bottom_header) + 11, '#')

    xbmc.log(f'''
    {top_header}

               {msg}

    {bottom_header}
''', level)


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
    if getSetting('watchlist.update.enabled') == 'true':
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
    return f'[COLOR {color}]{text}[/COLOR]'


def refresh():
    return execute('Container.Refresh')


def getSetting(key):
    return __settings__.getSetting(key)


def setSetting(settingid, value):
    return __settings__.setSetting(settingid, value)


def lang(x):
    return __language__(x)


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
        vinfo.setCast([xbmc.Actor(p['name'], p['role'], info['cast'].index(p), p['thumbnail']) for p in info['cast']])
    if info.get('OriginalTitle'):
        vinfo.setOriginalTitle(info['OriginalTitle'])
    if info.get('trailer'):
        vinfo.setTrailer(info['trailer'])


def xbmc_add_dir(name, url, art, info, draw_cm, bulk_add, isfolder, isplayable, fanart_disable=False, clearlogo_disable=False):
    u = addon_url(url)
    liz = xbmcgui.ListItem(name, offscreen=True)
    if info:
        set_videotags(liz, info)
    if draw_cm:
        cm = [(x[0], f'RunPlugin(plugin://{ADDON_ID}/{x[1]}/{url})') for x in draw_cm]
        liz.addContextMenuItems(cm)

    if art.get('fanart') is None or fanart_disable:
        art['fanart'] = OTAKU_FANART_PATH
    if clearlogo_disable:
        art['clearlogo'] = OTAKU_ICONS_PATH

    if isplayable:
        art['tvshow.poster'] = art.pop('poster')
        liz.setProperties({'Video': 'true', 'IsPlayable': 'true'})
    liz.setArt(art)

    return u, liz, isfolder if bulk_add else xbmcplugin.addDirectoryItem(HANDLE, u, liz, isfolder)


def bulk_draw_items(video_data, draw_cm, fanart_disable, clearlogo_disable):
    list_items = [xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, True, vid['isfolder'], vid['isplayable'], fanart_disable, clearlogo_disable) for vid in video_data]
    xbmcplugin.addDirectoryItems(HANDLE, list_items)


def draw_items(video_data, contentType="tvshows", draw_cm=None, bulk_add=False):
    if not draw_cm:
        draw_cm = []
    if getSetting('context.deletefromdatabase') == 'true' and contentType == 'tvshows':
        draw_cm.append(("Delete from database", 'delete_anime_database'))
    elif getSetting('context.marked.watched') == 'true' and contentType == 'episodes':
        draw_cm.append(("Marked as Watched [COLOR blue]WatchList[/COLOR]", 'marked_as_watched'))
    # for x in cm:
        #     draw_cm.append(x)
    fanart_disable = getSetting('interface.fanart.disable') == 'true'
    clearlogo_disable = getSetting('interface.clearlogo.disable') == 'true'
    if len(video_data) > 99:
        bulk_draw_items(video_data, draw_cm, fanart_disable, clearlogo_disable)
    else:
        for vid in video_data:
            xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['info'], draw_cm, bulk_add, vid['isfolder'], vid['isplayable'], fanart_disable, clearlogo_disable)

    xbmcplugin.setContent(HANDLE, contentType)
    if contentType == 'episodes':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%H. %T", "%R | %P")
    elif contentType == 'tvshows':
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE, "%L", "%R")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=True)

    if getSetting('interface.viewtypes.bool') == 'true':
        if contentType == 'addons':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.addon')))
        elif contentType == 'tvshows':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.tvshows')))
        elif contentType == 'episodes':
            xbmc.executebuiltin('Container.SetViewMode(%d)' % get_view_type(getSetting('interface.viewtypes.episodes')))

    # move to episode position currently watching
    if contentType == "episodes" and getSetting('general.smart.scroll.enable') == 'true':
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

# def append_params(url, params):
#     url_parts = list(parse.urlparse(url))
#     query = dict(parse.parse_qsl(url_parts[4]))
#     query.update(params)
#     url_parts[4] = parse.urlencode(query)
#     return parse.urlunparse(url_parts)


def toggle_reuselanguageinvoker(forced_state=None):
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
            if ("false" in line_string and forced_state is None) or ("false" in line_string and forced_state):
                file_lines[i] = file_lines[i].replace("false", "true")
                setSetting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            elif ("true" in line_string and forced_state is None) or ("true" in line_string and forced_state is False):
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


# def format_string(string, format_):
#     # format_ = B, I
#     return f'[{format_}]{string}[/{format_}]'


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
