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

import pickle
import os
import sys
import xbmcplugin
import xbmcgui

from resources.lib import OtakuBrowser
from resources.lib.ui import control, database, utils
from resources.lib.ui.router import Route, router_process
from resources.lib import WatchlistIntegration


BROWSER = OtakuBrowser.BROWSER

def add_last_watched(items: list) -> list:
    mal_id = control.getInt("addon.last_watched")
    if mal_id != -1:
        show = database.get_show(mal_id)
        if show:
            kodi_meta = pickle.loads(show['kodi_meta'])
            last_watched = f"{control.lang(30000)}[I]{kodi_meta['title_userPreferred']}[/I]"
            info = {
                'UniqueIDs': {'mal_id': str(mal_id)},
                'title': kodi_meta['title_userPreferred'],
                'plot': kodi_meta['plot'],
                'status': kodi_meta['status'],
                'rating': kodi_meta.get('rating')
            }
            if kodi_meta['format'] == 'movie':
                url = f'play_movie/{mal_id}/'
                info['mediatype'] = 'movie'
            else:
                info['mediatype'] = 'tvshow'
                url = f'animes/{mal_id}/'
            item = utils.allocate_item(last_watched, url, True, False, [], kodi_meta['poster'], info)
            items.append(item)
    return items


@Route('animes/*')
def ANIMES_PAGE(payload: str, params: dict) -> None:
    payload_split = payload.split("/", 1)
    mal_id = int(payload_split[0])
    # eps_watched = int(payload_split[1])
    control.draw_items(*database.cache(OtakuBrowser.get_anime_init, 60 * 8, False, mal_id))


@Route('find_recommendations/*')
def FIND_RECOMMENDATIONS(payload: str, params: dict) -> None:
    payload_split = payload.split("/", 2)
    # path = int(payload_split[0])
    mal_id = int(payload_split[1])
    # eps_watched = int(payload_split[2])

    page = int(params.get('page', 1))
    recommendations = BROWSER.get_recommendations(mal_id, page)
    control.draw_items(recommendations, 'tvshows')
    if recommendations and "Next Page" in recommendations[-1].get('name'):
        database.background_cache(BROWSER.recommendations, 60 * 8, mal_id, page + 1)


@Route('find_relations/*')
def FIND_RELATIONS(payload: str, params: dict) -> None:
    payload_split = payload.split("/", 2)
    # path = int(payload_split[0])
    mal_id = int(payload_split[1])
    # eps_watched = int(payload_split[2])

    control.draw_items(BROWSER.get_relations(mal_id), 'tvshows')


@Route('airing_anime')
def AIRING_ANIME(payload: str, params: dict) -> None:
    page = int(params.get('page', 1))
    airing_anime = database.cache(BROWSER.get_airing_anime, 60 * 8, False, page)
    control.draw_items(airing_anime, 'tvshows')
    if airing_anime and "Next Page" in airing_anime[-1].get('name'):
        database.background_cache(BROWSER.get_airing_anime, 60 * 8, page + 1)


@Route('upcoming_next_season')
def UPCOMING_NEXT_SEASON(payload: str, params: dict) -> None:
    page = int(params.get('page', 1))
    next_season = database.cache(BROWSER.get_upcoming_next_season, 60 * 8, False, page)
    control.draw_items(next_season, 'tvshows')
    if next_season and "Next Page" in next_season[-1].get('name'):
        database.background_cache(BROWSER.get_upcoming_next_season, 60 * 8, page + 1)


@Route('top_100_anime')
def TOP_100_ANIME_PAGES(payload: str, params: dict) -> None:
    page = int(params.get('page', 1))
    top_100 = database.cache(BROWSER.get_top_100_anime, 60 * 8, False, page)
    control.draw_items(top_100, 'tvshows')
    if top_100 and "Next Page" in top_100[-1].get('name'):
        database.background_cache(BROWSER.get_top_100_anime, 60 * 8, page + 1)


@Route('airing_calendar')
def AIRING_CALENDAR(payload: str, params: dict) -> None:
    page = int(params.get('page', 1))
    calendar = database.cache(BROWSER.get_airing_calendar, 60 * 8, False, page)
    if calendar:
        from resources.lib.windows.anichart import Anichart
        window = Anichart('anichart.xml', control.ADDON_PATH, calendar=calendar)
        window.doModal()
        del window


@Route('genres/*')
def GENRES_PAGES(payload: str, params: dict) -> None:
    genres, tags = payload.split("/", 1)
    page = int(params.get('page', 1))
    if genres or tags:
        genre_page = BROWSER.genres_payload(genres, tags, page)
        control.draw_items(genre_page, 'tvshows')
        if genre_page and "Next Page" in genre_page[-1].get('name'):
            database.background_cache(BROWSER.genres_payload, 60 * 8, genres, tags, page + 1)
    else:
        control.draw_items(BROWSER.get_genres(), 'tvshows')


@Route('search_history')
def SEARCH_HISTORY(payload: str, params: dict) -> None:
    history = database.getSearchHistory('show')
    if control.getInt('searchhistory') == 0:
        control.draw_items(utils.search_history(history), '')
    else:
        SEARCH(payload, params)


@Route('search')
def SEARCH(payload: str, params: dict) -> None:
    query = params.get('q')
    page = int(params.get('page', 1))
    if not query:
        query = control.keyboard(control.lang(30005))
        if not query:
            xbmcplugin.endOfDirectory(control.HANDLE, succeeded=False, updateListing=False)
            return None
        if control.getInt('searchhistory') == 0:
            database.addSearchHistory(query, 'show')
    search_page = database.cache(BROWSER.get_search, 60 * 8, False, query, page)
    control.draw_items(search_page, 'tvshows')
    if search_page and "Next Page" in search_page[-1].get('name'):
        database.background_cache(BROWSER.get_search, 60 * 8, query, page + 1)
    return None


@Route('remove_search_item/*')
def REMOVE_SEARCH_ITEM(payload: str, params: dict) -> None:
    query = params.get('q', '')
    if query:
        database.remove_search(table='show', value=query)
    control.exit_code()


@Route('edit_search_item/*')
def EDIT_SEARCH_ITEM(payload: str, params: dict) -> None:
    query = params.get('q', '')
    if query:
        new_query = control.keyboard(control.lang(30005), query)
        if new_query and new_query != query:
            database.remove_search(table='show', value=query)
            database.addSearchHistory(new_query, 'show')
    control.exit_code()

@Route('play/*')
def PLAY(payload: str, params: dict) -> None:
    from resources.lib import pages

    payload_split = payload.split("/", 1)
    mal_id = int(payload_split[0])
    episode = int(payload_split[1])

    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    if resume := params.get('resume', 0):
        resume = float(resume)
        context = control.context_menu([f'Resume from {utils.format_time(resume)}', 'Play from beginning'])
        if context == -1:
            return
        elif context == 1:
            resume = None
    sources = pages.get_kodi_sources(mal_id, episode, 'show', rescrape, source_select)
    if sources:
        _mock_args = {"mal_id": mal_id, "episode": episode, 'play': True, 'resume': resume, 'context': rescrape or source_select}
        if control.getInt('general.playstyle.episode') == 1 or source_select or rescrape:
            from resources.lib.windows.source_select import SourceSelect
            window = SourceSelect('source_select.xml', control.ADDON_PATH, actionArgs=_mock_args, sources=sources, rescrape=rescrape)
            window.doModal()
            del window
        else:
            from resources.lib.windows.resolver import Resolver
            window = Resolver('resolver.xml', control.ADDON_PATH, actionArgs=_mock_args)
            window.doModal(sources)
            del window
    else:
        control.notify(control.ADDON_NAME, "No Sources Found!")
        xbmcplugin.setResolvedUrl(control.HANDLE, False, xbmcgui.ListItem(path=""))
    control.exit_code()


@Route('play_movie/*')
def PLAY_MOVIE(payload: str, params: dict) -> None:
    from resources.lib import pages

    payload_split = payload.split("/", 1)
    mal_id = int(payload_split[0])
    # episode = int(payload_split[1])

    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    resume = params.get('resume', 0)
    if resume:
        resume = float(resume)
        context = control.context_menu([f'Resume from {utils.format_time(resume)}', 'Play from beginning'])
        if context == -1:
            return
        elif context == 1:
            resume = None

    sources = pages.get_kodi_sources(mal_id, 1, 'movie', rescrape, source_select)
    if sources:
        _mock_args = {'mal_id': mal_id, 'play': True, 'resume': resume, 'context': rescrape or source_select}
        if control.getInt('general.playstyle.movie') == 1 or source_select or rescrape:
            from resources.lib.windows.source_select import SourceSelect
            window = SourceSelect('source_select.xml', control.ADDON_PATH, actionArgs=_mock_args, sources=sources, rescrape=rescrape)
            window.doModal()
            del window
        else:
            from resources.lib.windows.resolver import Resolver
            window = Resolver('resolver.xml', control.ADDON_PATH, actionArgs=_mock_args)
            window.doModal(sources)
            del window
    else:
        control.notify(control.ADDON_NAME, "No Sources Found!")
        xbmcplugin.setResolvedUrl(control.HANDLE, False, xbmcgui.ListItem(path=""))
    control.exit_code()


@Route('marked_as_watched/*')
def MARKED_AS_WATCHED(payload: str, params: dict) -> None:
    from resources.lib.WatchlistFlavor import WatchlistFlavor
    payload_list = payload.split("/")
    if len(payload_list) == 2:
        mal_id = int(payload_list[0])
        episode = int(payload_list[1])
    else:
        mal_id = int(payload_list[0])
        episode = 1

    flavor = WatchlistFlavor.get_update_flavor()
    WatchlistIntegration.watchlist_update_episode(mal_id, episode)
    control.notify(control.ADDON_NAME, f'Episode #{episode} was Marked as Watched in {flavor.flavor_name}')
    control.refresh()
    control.exit_code()



@Route('delete_anime_database/*')
def DELETE_ANIME_DATABASE(payload: str, params: dict) -> None:
    payload_split = payload.split("/", 2)
    # path = int(payload_split[0])
    mal_id = int(payload_split[1])
    # eps_watched = int(payload_split[2])

    database.remove_from_database('shows', mal_id)
    database.remove_from_database('episodes', mal_id)
    database.remove_from_database('show_data', mal_id)
    database.remove_from_database('shows_meta', mal_id)
    control.notify(control.ADDON_NAME, 'Removed from database')
    control.exit_code()


@Route('auth/*')
def AUTH(payload: str, params: dict) -> None:
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
    elif payload == 'torbox':
        from resources.lib.debrid.torbox import Torbox
        Torbox().auth()



@Route('refresh/*')
def REFRESH(payload: str, params: dict) -> None:
    if payload == 'realdebrid':
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().refreshToken()
    elif payload == 'debridlink':
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().refreshToken()


@Route('fanart_select/*')
def FANART_SELECT(payload: str, params: dict) -> None:
    payload_split = payload.split("/", 2)
    # path = int(payload_split[0])
    mal_id = int(payload_split[1])
    # eps_watched = int(payload_split[2])

    if not (episode := database.get_episode(mal_id)):
        OtakuBrowser.get_anime_init(mal_id)
        episode = database.get_episode(mal_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random (Defualt)"]
    fanart += ["None", ""]
    control.draw_items([utils.allocate_item(f, f'fanart/{mal_id}/{i}', False, False, [], f, {}, fanart=f, landscape=f) for i, f in enumerate(fanart_display)], '')


@Route('fanart/*')
def FANART(payload: str, params: dict) -> None:
    payload_list = payload.split("/", 1)
    mal_id = int(payload_list[0])
    select = int(payload_list[1])

    episode = database.get_episode(mal_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random"]
    fanart += ["None", ""]
    fanart_all = control.getStringList(f'fanart.all')
    fanart_all.append(str(mal_id))
    control.setSetting(f'fanart.select.{mal_id}', fanart[select])
    control.setStringList(f'fanart.all', fanart_all)
    control.ok_dialog(control.ADDON_NAME, f"Fanart Set to {fanart_display[select]}")


# ### Menu Items ###
@Route('')
def LIST_MENU(payload: str, params: dict) -> None:
    MENU_ITEMS = [
        (30001, "airing_anime", True, 'airing_anime.png'),
        (30007, 'airing_calendar', False, 'airing_anime_calendar.png'),
        (30002, "upcoming_next_season", True, 'upcoming.png'),
        (30003, "top_100_anime", True, 'top_100_anime.png'),
        (30004, "genres//", True, 'genres_&_tags.png'),
        (30005, "search_history", True, 'search.png'),
        (30006, "tools", True, 'tools.png')
        # ("test", "test", 'tools.png')
    ]

    items = []
    items = WatchlistIntegration.add_watchlists(items)
    if control.getBool('menu.lastwatched'):
        items = add_last_watched(items)
    for lang_id, url, isfolder, image  in MENU_ITEMS:
        if control.getBool(url):
            name = control.lang(lang_id)
            items.append(utils.allocate_item(name, url, isfolder, False, [], image, {}))
    control.draw_items(items, '')


@Route('tools')
def TOOLS_MENU(payload: str, params: dict) -> None:
    TOOLS_ITEMS = [
        (control.lang(30010), "change_log", 'changelog.png', {'plot': "View Changelog"}),
        (control.lang(30011), "settings", 'open_settings_menu.png', {'plot': "Open Settings"}),
        (control.lang(30012), "clear_cache", 'clear_cache.png', {'plot': "Clear Cache"}),
        (control.lang(30013), "clear_search_history", 'clear_search_history.png', {'plot': "Clear Search History"}),
        (control.lang(30014), "rebuild_database", 'rebuild_database.png', {'plot': "Rebuild Database"}),
        (control.lang(30015), "completed_sync", "sync_completed.png", {'plot': "Sync Completed Anime with Otaku"}),
        (control.lang(30016), 'download_manager', 'download_manager.png', {'plot': "Open Download Manager"}),
        (control.lang(30017), 'sort_select', 'sort_select.png', {'plot': "Choose Sorting..."}),
        (control.lang(30018), 'clear_selected_fanart', 'delete.png', {'plot': "Clear All Selected Fanart"})
        # ("install Packages", 'install_packages', '', {'plot': "Install Custom Packages"})
    ]
    control.draw_items([utils.allocate_item(name, url, False, False, [], image, info) for name, url, image, info in TOOLS_ITEMS], '')


# ### Maintenance ###
@Route('settings')
def SETTINGS(payload: str, params: dict) -> None:
    control.ADDON.openSettings()


@Route('change_log')
def CHANGE_LOG(payload: str, params: dict) -> None:
    import service
    service.getchangelog()
    if params.get('setting'):
        control.exit_code()

@Route('clear_cache')
def CLEAR_CACHE(payload: str, params: dict) -> None:
    database.cache_clear()
    if params.get('setting'):
        control.exit_code()


@Route('clear_search_history')
def CLEAR_SEARCH_HISTORY(payload: str, params: dict) -> None:
    database.clearSearchHistory('show')
    control.refresh()
    if params.get('setting'):
        control.exit_code()


@Route('rebuild_database')
def REBUILD_DATABASE(payload: str, params: dict) -> None:
    from resources.lib.ui.database_sync import SyncDatabase
    SyncDatabase().re_build_database()
    if params.get('setting'):
        control.exit_code()


@Route('completed_sync')
def COMPLETED_SYNC(payload: str, params: dict) -> None:
    import service
    service.sync_watchlist()
    if params.get('setting'):
        control.exit_code()


@Route('download_manager')
def DOWNLOAD_MANAGER(payload: str, params: dict) -> None:
    from resources.lib.windows.download_manager import DownloadManager
    window = DownloadManager('download_manager.xml', control.ADDON_PATH)
    window.doModal()
    del window
    if params.get('setting'):
        control.exit_code()


@Route('clear_selected_fanart')
def CLEAR_SELECTED_FANART(payload: str, params: dict) -> None:
    fanart_all = control.getStringList(f'fanart.all')
    for i in fanart_all:
        control.setSetting(f'fanart.select.{i}', '')
    control.setStringList('fanart.all', [])
    control.ok_dialog(control.ADDON_NAME, "Completed")
    if params.get('setting'):
        control.exit_code()


@Route('sort_select')
def SORT_SELECT(payload: str, params: dict) -> None:
    from resources.lib.windows.sort_select import SortSelect
    window = SortSelect('sort_select.xml', control.ADDON_PATH)
    window.doModal()
    del window
    if params.get('setting'):
        control.exit_code()

@Route('install_packages')
def INSTALL_PACKAGES(payload: str, params: dict) -> None:
    from resources.lib.pages import custom_providers
    custom_providers.main()
    control.print('installed_packages')


@Route('toggleLanguageInvoker')
def TOGGLE_LANGUAGE_INVOKER(payload: str, params: dict) -> None:
    import service
    service.toggle_reuselanguageinvoker()


@Route('import_settings')
def IMPORT_SETTINGS(payload: str, params: dict) -> None:
    import xbmcvfs

    setting_xml = os.path.join(control.dataPath, 'settings.xml')
    import_location = control.browse(1, f"{control.ADDON_NAME}:  Import Setting", 'files', 'settings.xml')
    if import_location:
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
def IMPORT_SETTINGS(payload: str, params: dict) -> None:
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


@Route('test')
def TEST(payload: str, params: dict) -> None:
    pass


if __name__ == "__main__":
    plugin_url = control.get_plugin_url(sys.argv[0])
    plugin_params = control.get_plugin_params(sys.argv[2])
    router_process(plugin_url, plugin_params)
    # control.log(f'Finished Running: {plugin_url=} {plugin_params=}')