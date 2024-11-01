# -*- coding: utf-8 -*-
"""
    Otaku Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# import time
# t0 = time.perf_counter_ns()

from resources.lib import OtakuBrowser
from resources.lib.ui import control, database, utils
from resources.lib.ui.router import Route, router_process
from resources.lib.WatchlistIntegration import add_watchlist

BROWSER = OtakuBrowser.BROWSER


def add_last_watched(items):
    import pickle
    mal_id = control.getSetting("addon.last_watched")
    try:
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        last_watched = "%s[I]%s[/I]" % (control.lang(30000), kodi_meta.get('title_userPreferred'))
        items.append((last_watched, f'animes/{mal_id}/', kodi_meta['poster']))
    except TypeError:
        pass
    return items


@Route('animes/*')
def ANIMES_PAGE(payload, params):
    mal_id, eps_watched = payload.rsplit("/")
    anime_general, content = OtakuBrowser.get_anime_init(mal_id)
    control.draw_items(anime_general, content)


@Route('find_recommendations/*')
def FIND_RECOMMENDATIONS(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_recommendations(mal_id, page), 'tvshows')


@Route('find_relations/*')
def FIND_RELATIONS(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    control.draw_items(BROWSER.get_relations(mal_id), 'tvshows')


@Route('airing_anime')
def AIRING_ANIME(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_airing_anime(page), 'tvshows')


@Route('upcoming_next_season')
def UPCOMING_NEXT_SEASON(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_upcoming_next_season(page), 'tvshows')


@Route('top_100_anime')
def TOP_100_ANIME_PAGES(payload, params):
    page = int(params.get('page', 1))
    control.draw_items(BROWSER.get_top_100_anime(page), 'tvshows')


@Route('genres/*')
def GENRES_PAGES(payload, params):
    genres, tags = payload.rsplit("/")
    page = int(params.get('page', 1))
    if genres or tags:
        control.draw_items(BROWSER.genres_payload(genres, tags, page), 'tvshows')
    else:
        control.draw_items(BROWSER.get_genres(), 'tvshows')


@Route('search_history')
def SEARCH_HISTORY(payload, params):
    history = database.getSearchHistory('show')
    if control.getInt('searchhistory') == 0:
        draw_cm = [('Remove from Item', 'remove_search_item'), ("Edit Search Item...", "edit_search_item")]
        control.draw_items(OtakuBrowser.search_history(history), 'addons', draw_cm)
    else:
        SEARCH(payload, params)


@Route('search/*')
def SEARCH(payload, params):
    query = payload
    page = int(params.get('page', 1))
    if not query:
        query = control.keyboard(control.lang(30005))
        if not query:
            return control.draw_items([], 'tvshows')
        if control.getInt('searchhistory') == 0:
            database.addSearchHistory(query, 'show')
        control.draw_items(BROWSER.get_search(query), 'tvshows')
    else:
        control.draw_items(BROWSER.get_search(query, page), 'tvshows')


@Route('remove_search_item/*')
def REMOVE_SEARCH_ITEM(payload, params):
    if 'search/' in payload:
        search_item = payload.rsplit('search/')[1]
        database.remove_search(table='show', value=search_item)
    control.exit_code()

@Route('edit_search_item/*')
def EDIT_SEARCH_ITEM(payload, params):
    if 'search/' in payload:
        search_item = payload.rsplit('search/')[1]
        if search_item:
            query = control.keyboard(control.lang(30005), search_item)
            if query and query != search_item:
                database.remove_search(table='show', value=search_item)
                database.addSearchHistory(query, 'show')
    control.exit_code()

@Route('play/*')
def PLAY(payload, params):
    mal_id, episode = payload.rsplit("/")
    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    resume_time = params.get('resume')
    if resume_time:
        resume_time = float(resume_time)
        context = control.context_menu([f'Resume from {utils.format_time(resume_time)}', 'Play from beginning'])
        if context == -1:
            return control.exit_code()
        elif context == 1:
            resume_time = None

    sources = OtakuBrowser.get_sources(mal_id, episode, 'show', rescrape, source_select)
    _mock_args = {"mal_id": mal_id, "episode": episode, 'play': True, 'resume_time': resume_time, 'context': rescrape or source_select}
    if control.getSetting('general.playstyle.episode') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        SourceSelect(*('source_select.xml', control.ADDON_PATH), actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
    else:
        from resources.lib.windows.resolver import Resolver
        Resolver(*('resolver.xml', control.ADDON_PATH), actionArgs=_mock_args).doModal(sources, {}, False)
    control.exit_code()


@Route('play_movie/*')
def PLAY_MOVIE(payload, params):
    mal_id, eps_watched = payload.rsplit("/")
    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    resume_time = params.get('resume')
    if resume_time:
        resume_time = float(resume_time)
        context = control.context_menu([f'Resume from {utils.format_time(resume_time)}', 'Play from beginning'])
        if context == -1:
            return
        elif context == 1:
            resume_time = None

    sources = OtakuBrowser.get_sources(mal_id, 1, 'movie', rescrape, source_select)
    _mock_args = {'mal_id': mal_id, 'play': True, 'resume_time': resume_time, 'context': rescrape or source_select}
    control.playList.clear()
    if control.getSetting('general.playstyle.movie') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        SourceSelect(*('source_select.xml', control.ADDON_PATH), actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
    else:
        from resources.lib.windows.resolver import Resolver
        Resolver(*('resolver.xml', control.ADDON_PATH), actionArgs=_mock_args).doModal(sources, {}, False)
    control.exit_code()


@Route('marked_as_watched/*')
def MARKED_AS_WATCHED(payload, params):
    from resources.lib.WatchlistFlavor import WatchlistFlavor
    from resources.lib.WatchlistIntegration import watchlist_update_episode

    mal_id, episode = payload.rsplit("/")
    flavor = WatchlistFlavor.get_update_flavor()
    watchlist_update_episode(mal_id, episode)
    control.notify(control.ADDON_NAME, f'Episode #{episode} was Marked as Watched in {flavor.flavor_name}')
    control.execute(f'ActivateWindow(Videos,plugin://{control.ADDON_ID}/watchlist_to_ep/{mal_id}/{episode})')
    control.exit_code()


@Route('delete_anime_database/*')
def DELETE_ANIME_DATABASE(payload, params):
    path, mal_id, eps_watched = payload.rsplit("/")
    database.remove_from_database('shows', mal_id)
    database.remove_from_database('episodes', mal_id)
    database.remove_from_database('show_data', mal_id)
    database.remove_from_database('shows_meta', mal_id)
    control.notify(control.ADDON_NAME, 'Removed from database')
    control.exit_code()


@Route('auth/*')
def AUTH(payload, params):
    if payload == 'realdebrid':
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().auth()
    elif payload == 'alldebrid':
        from resources.lib.debrid.all_debrid import AllDebrid
        AllDebrid().auth()
    elif payload == 'premiumize':
        from resources.lib.debrid.premiumize import Premiumize
        Premiumize().auth()
    elif payload == 'debridlink':
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().auth()


@Route('refresh/*')
def REFRESH(payload, params):
    if payload == 'realdebrid':
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().refreshToken()
    elif payload == 'debridlink':
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().refreshToken()


@Route('fanart_select/*')
def FANART_SELECT(payload, params):
    import pickle
    path, mal_id, eps_watched = payload.rsplit("/")
    if not (episode := database.get_episode(mal_id)):
        OtakuBrowser.get_anime_init(mal_id)
        episode = database.get_episode(mal_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random (Defualt)"]
    fanart += ["None", ""]
    control.draw_items([utils.allocate_item(f, f'fanart/{mal_id}/{i}', False, False, f, fanart=f, landscape=f) for i, f in enumerate(fanart_display)], '')


@Route('fanart/*')
def FANART(payload, params):
    import pickle
    mal_id, select = payload.rsplit('/', 2)
    episode = database.get_episode(mal_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random"]
    fanart += ["None", ""]
    fanart_all = control.getSetting(f'fanart.all').split(',')
    if '' in fanart_all:
        fanart_all.remove('')
    fanart_all += [str(mal_id)]
    control.setSetting(f'fanart.select.{mal_id}', fanart[int(select)])
    control.setSetting(f'fanart.all', ",".join(fanart_all))
    control.ok_dialog(control.ADDON_NAME, f"Fanart Set to {fanart_display[int(select)]}")


# ### Menu Items ###
@Route('')
def LIST_MENU(payload, params):
    MENU_ITEMS = [
        (control.lang(30001), "airing_anime", 'airing_anime.png'),
        (control.lang(30002), "upcoming_next_season", 'upcoming.png'),
        (control.lang(30003), "top_100_anime", 'top_100_anime.png'),
        (control.lang(30004), "genres//", 'genres_&_tags.png'),
        (control.lang(30005), "search_history", 'search.png'),
        (control.lang(30006), "tools", 'tools.png')
    ]
    NEW_MENU_ITEMS = []
    NEW_MENU_ITEMS = add_watchlist(NEW_MENU_ITEMS)
    if control.getBool('menu.lastwatched'):
        NEW_MENU_ITEMS = add_last_watched(NEW_MENU_ITEMS)
    for i in MENU_ITEMS:
        if control.getBool(i[1]):
            NEW_MENU_ITEMS.append(i)
    control.draw_items([utils.allocate_item(name, url, True, False, image) for name, url, image in NEW_MENU_ITEMS], 'addons')


@Route('tools')
def TOOLS_MENU(payload, params):
    TOOLS_ITEMS = [
        (control.lang(30010), "change_log", {'plot': "View Changelog"}, 'changelog.png'),
        (control.lang(30011), "settings", {'plot': "Open Settings"}, 'open_settings_menu.png'),
        (control.lang(30012), "clear_cache", {'plot': "Clear Cache"}, 'clear_cache.png'),
        (control.lang(30013), "clear_search_history", {'plot': "Clear Search History"}, 'clear_search_history.png'),
        (control.lang(30014), "rebuild_database", {'plot': "Rebuild Database"}, 'rebuild_database.png'),
        (control.lang(30015), "completed_sync", {'plot': "Sync Completed Anime with Otaku"}, "sync_completed.png"),
        (control.lang(30016), 'download_manager', {'plot': "Open Download Manager"}, 'download_manager.png'),
        (control.lang(30017), 'sort_select', {'plot': "Choose Sorting..."}, ''),
        (control.lang(30018), 'clear_slected_fanart', {'plot': "Clear All Selected Fanart"}, 'delete.png')
    ]
    control.draw_items([utils.allocate_item(name, url, False, False, image, info) for name, url, info, image in TOOLS_ITEMS], 'addons')


# ### Maintenance ###
@Route('settings')
def SETTINGS(payload, params):
    control.ADDON.openSettings()


@Route('change_log')
def CHANGE_LOG(payload, params):
    import service
    service.getChangeLog()
    if params.get('setting'):
        control.exit_code()


@Route('clear_cache')
def CLEAR_CACHE(payload, params):
    database.cache_clear()
    if params.get('setting'):
        control.exit_code()


@Route('clear_search_history')
def CLEAR_SEARCH_HISTORY(payload, params):
    database.clearSearchHistory()
    control.refresh()
    if params.get('setting'):
        control.exit_code()


@Route('clear_selected_fanart')
def CLEAR_SELECTED_FANART(payload, params):
    fanart_all = control.getSetting(f'fanart.all').split(',')
    for i in fanart_all:
        control.setSetting(f'fanart.select.{i}', '')
    control.setSetting('fanart.all', '')
    control.ok_dialog(control.ADDON_NAME, "Completed")
    if params.get('setting'):
        control.exit_code()


@Route('rebuild_database')
def REBUILD_DATABASE(payload, params):
    from resources.lib.ui.database_sync import SyncDatabase
    SyncDatabase().re_build_database()
    if params.get('setting'):
        control.exit_code()


@Route('completed_sync')
def COMPLETED_SYNC(payload, params):
    import service
    service.sync_watchlist()
    if params.get('setting'):
        control.exit_code()


@Route('sort_select')
def SORT_SELECT(payload, params):
    from resources.lib.windows.sort_select import SortSelect
    SortSelect(*('sort_select.xml', control.ADDON_PATH)).doModal()


@Route('download_manager')
def DOWNLOAD_MANAGER(payload, params):
    from resources.lib.windows.download_manager import DownloadManager
    DownloadManager(*('download_manager.xml', control.ADDON_PATH)).doModal()


@Route('import_settings')
def IMPORT_SETTINGS(payload, params):
    import os
    import xbmcvfs
    setting_xml = os.path.join(control.dataPath, 'settings.xml')

    import_location = control.browse(1, f"{control.ADDON_NAME}:  Import Setting", 'files', 'settings.xml')
    if not import_location:
        return control.exit_code()
    if not import_location.endswith('settings.xml'):
        control.ok_dialog(control.ADDON_NAME, "Invalid File!")
    else:
        yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to replace settings.xml?")
        if yesno:
            if xbmcvfs.delete(setting_xml) and xbmcvfs.copy(import_location, setting_xml):
                control.ok_dialog(control.ADDON_NAME, "Replaced settings.xml")
            else:
                control.ok_dialog(control.ADDON_NAME, "Could Not Import File!")
    control.exit_code()

@Route('export_settings')
def IMPORT_SETTINGS(payload, params):
    import os
    import xbmcvfs

    setting_xml = os.path.join(control.dataPath, 'settings.xml')
    export_location = control.browse(3, f"{control.ADDON_NAME}: Export Location", 'files')

    if not export_location:
        control.ok_dialog(control.ADDON_NAME, "Please Select Export Location!")
    else:
        yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to save settings.xml?")
        if yesno:
            if xbmcvfs.copy(setting_xml, os.path.join(export_location, 'settings.xml')):
                control.ok_dialog(control.ADDON_NAME, "Saved settings.xml")
            else:
                control.ok_dialog(control.ADDON_NAME, "Could Not Export File!")
    control.exit_code()

@Route('toggleLanguageInvoker')
def TOGGLE_LANGUAGE_INVOKER(payload, params):
    import service
    service.toggle_reuselanguageinvoker()


if __name__ == "__main__":
    router_process(control.get_plugin_url(), control.get_plugin_params())
    if len(control.playList) > 0:
        import xbmc
        if not xbmc.Player().isPlaying():
            control.playList.clear()

# t1 = time.perf_counter_ns()
# totaltime = (t1-t0)/1_000_000
# control.print(totaltime, 'ms')
