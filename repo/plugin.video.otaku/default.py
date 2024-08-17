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

from resources.lib.AniListBrowser import AniListBrowser
from resources.lib import OtakuBrowser
from resources.lib.ui import control, database, utils
from resources.lib.ui.router import Route, router_process
from resources.lib.WatchlistIntegration import add_watchlist, watchlist_update_episode

_ANILIST_BROWSER = AniListBrowser()


def add_last_watched(items):
    anilist_id = control.getSetting("addon.last_watched")
    try:
        kodi_meta = pickle.loads(database.get_show(anilist_id)['kodi_meta'])
        last_watched = "%s[I]%s[/I]" % (control.lang(30000), kodi_meta.get('title_userPreferred'))
        items.insert(0, (last_watched, f'animes/{anilist_id}//', kodi_meta['poster']))
    except TypeError:
        pass
    return items


@Route('animes/*')
def ANIMES_PAGE(payload, params):
    anilist_id, mal_id, eps_watched = payload.rsplit("/")
    anime_general, content = OtakuBrowser.get_anime_init(anilist_id)
    control.draw_items(anime_general, content)


@Route('find_recommendations/*')
def FIND_RECOMMENDATIONS(payload, params):
    path, anilist_id, mal_id, eps_watched = payload.rsplit("/")
    page = params.get('page', 1)
    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']
    control.draw_items(_ANILIST_BROWSER.get_recommendations(anilist_id, int(page)), 'tvshows')


@Route('find_relations/*')
def FIND_RELATIONS(payload, params):
    path, anilist_id, mal_id, eps_watched = payload.rsplit("/")
    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']
    control.draw_items(_ANILIST_BROWSER.get_relations(anilist_id), 'tvshows')


@Route('anilist_airing_anime/*')
def ANILIST_AIRING_ANIME(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_airing_anime(int(payload)), 'tvshows')


@Route('anilist_upcoming_next_season/*')
def ANILIST_UPCOMING_NEXT_SEASON(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_upcoming_next_season(int(payload)), 'tvshows')


@Route('anilist_top_100_anime/*')
def ANILIST_TOP_100_ANIME_PAGES(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_top_100_anime(int(payload)), 'tvshows')


@Route('anilist_genres/*')
def ANILIST_GENRES_PAGES(payload, params):
    genres, tags, page = payload.rsplit("/")
    if genres or tags:
        control.draw_items(_ANILIST_BROWSER.genres_payload(genres, tags, int(page)), 'tvshows')
    else:
        genre = _ANILIST_BROWSER.get_genres(lambda g: control.multiselect_dialog(control.lang(50010), g))
        control.draw_items(genre, 'tvshows')


@Route('search_history')
def SEARCH_HISTORY(payload, params):
    history = database.getSearchHistory('show')
    if int(control.getSetting('searchhistory')) == 0:
        draw_cm = [('Remove from Item', 'remove_search_item'), ("Edit Search Item...", "edit_search_item")]
        control.draw_items(OtakuBrowser.search_history(history), 'addons', draw_cm)
    else:
        SEARCH(payload, params)


@Route('search/*')
def SEARCH(payload, params):
    query, page = payload.rsplit("/", 1)
    if not query:
        query = control.keyboard(control.lang(50011))
        if not query:
            return control.draw_items([], 'tvshows')
        if int(control.getSetting('searchhistory')) == 0:
            database.addSearchHistory(query, 'show')
        control.draw_items(_ANILIST_BROWSER.get_search(query), 'tvshows')
    else:
        control.draw_items(_ANILIST_BROWSER.get_search(query, int(page)), 'tvshows')


@Route('remove_search_item/*')
def REMOVE_SEARCH_ITEM(payload, params):
    if 'search/' in payload:
        payload_list = payload.rsplit('search/')[1].rsplit('/', 1)
        if len(payload_list) == 2 and payload_list[0]:
            search_item, page = payload_list
            return database.remove_search(table='show', value=search_item)
    control.notify(control.ADDON_NAME, "Invalid Search Item")


@Route('edit_search_item/*')
def EDIT_SEARCH_ITEM(payload, params):
    if 'search/' in payload:
        payload_list = payload.rsplit('search/')[1].rsplit('/', 1)
        if len(payload_list) == 2 and payload_list[0]:
            search_item, page = payload_list
            query = control.keyboard(control.lang(50011), search_item)
            if query != search_item:
                database.remove_search(table='show', value=search_item)
                database.addSearchHistory(query, 'show')
            return
    control.notify(control.ADDON_NAME, "Invalid Search Item")


@Route('play/*')
def PLAY(payload, params):
    anilist_id, episode = payload.rsplit("/")
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
    sources = OtakuBrowser.get_sources(anilist_id, episode, 'show', rescrape, source_select)
    _mock_args = {"anilist_id": anilist_id, "episode": episode, 'play': True, 'resume_time': resume_time, 'context': rescrape or source_select}
    if control.getSetting('general.playstyle.episode') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        SourceSelect(*('source_select.xml', control.ADDON_PATH), actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()
    else:
        from resources.lib.windows.resolver import Resolver
        Resolver(*('resolver.xml', control.ADDON_PATH), actionArgs=_mock_args).doModal(sources, {}, False)
    control.exit_code()


@Route('play_movie/*')
def PLAY_MOVIE(payload, params):
    anilist_id, mal_id, eps_watched = payload.rsplit("/")
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
    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']

    sources = OtakuBrowser.get_sources(anilist_id, 1, 'movie', rescrape, source_select)
    _mock_args = {'anilist_id': anilist_id, 'episode': 1, 'play': True, 'resume_time': resume_time, 'context': rescrape or source_select}

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
    anilist_id, episode = payload.rsplit("/")
    flavor = WatchlistFlavor.get_update_flavor()
    watchlist_update_episode(anilist_id, episode)
    control.notify(control.ADDON_NAME, f'Episode #{episode} was Marked as Watched in {flavor.flavor_name}')
    show = database.get_show(anilist_id)
    mal_id = show['mal_id']
    control.execute(f'ActivateWindow(Videos,plugin://{control.ADDON_ID}/watchlist_to_ep/{anilist_id}/{mal_id}/{episode})')
    control.exit_code()


@Route('delete_anime_database/*')
def DELETE_ANIME_DATABASE(payload, params):
    path, anilist_id, mal_id, eps_watched = payload.rsplit("/")
    if not anilist_id:
        anilist_id = database.get_mappings(mal_id, 'mal_id')['anilist_id']
    database.remove_episodes(anilist_id)
    database.remove_show_data(anilist_id)
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
    path, anilist_id, mal_id, eps_watched = payload.rsplit("/")
    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']
    if not (episode := database.get_episode(anilist_id)):
        OtakuBrowser.get_anime_init(anilist_id)
        episode = database.get_episode(anilist_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random (Defualt)"]
    fanart += ["None", ""]
    control.draw_items([utils.allocate_item(f, f'fanart/{anilist_id}/{i}', False, False, f, fanart=f, landscape=f) for i, f in enumerate(fanart_display)], '')


@Route('fanart/*')
def FANART(payload, params):
    anilist_id, select = payload.rsplit('/', 2)
    episode = database.get_episode(anilist_id)
    fanart = pickle.loads(episode['kodi_meta'])['image']['fanart'] or []
    fanart_display = fanart + ["None", "Random"]
    fanart += ["None", ""]
    fanart_all = control.getSetting(f'fanart.all').split(',')
    if '' in fanart_all:
        fanart_all.remove('')
    fanart_all += [str(anilist_id)]
    control.setSetting(f'fanart.select.anilist.{anilist_id}', fanart[int(select)])
    control.setSetting(f'fanart.all', ",".join(fanart_all))
    control.ok_dialog(control.ADDON_NAME, f"Fanart Set to {fanart_display[int(select)]}")


# ### Menu Items ###
@Route('')
def LIST_MENU(payload, params):
    MENU_ITEMS = [
        (control.lang(50001), "anilist_airing_anime/1", 'airing_anime.png'),
        (control.lang(50034), "anilist_upcoming_next_season/1", 'upcoming.png'),
        (control.lang(50009), "anilist_top_100_anime/1", 'top_100_anime.png'),
        (control.lang(50010), "anilist_genres///1", 'genres_&_tags.png'),
        (control.lang(50011), "search_history", 'search.png'),
        (control.lang(50012), "tools", 'tools.png')
    ]

    if control.getBool('menu.lastwatched'):
        MENU_ITEMS = add_last_watched(MENU_ITEMS)
    MENU_ITEMS = add_watchlist(MENU_ITEMS)
    MENU_ITEMS_ = MENU_ITEMS[:]
    for i in MENU_ITEMS:
        if control.getSetting(i[1]) == 'false':
            MENU_ITEMS_.remove(i)
    control.draw_items([utils.allocate_item(name, url, True, False, image) for name, url, image in MENU_ITEMS_], 'addons')


@Route('tools')
def TOOLS_MENU(payload, params):
    TOOLS_ITEMS = [
        (control.lang(30027), "change_log", {'plot': "View Changelog"}, 'changelog.png'),
        (control.lang(30020), "settings", {'plot': "Open Settings"}, 'open_settings_menu.png'),
        (control.lang(30021), "clear_cache", {'plot': "Clear Cache"}, 'clear_cache.png'),
        (control.lang(30023), "clear_history", {'plot': "Clear Search History"}, 'clear_search_history.png'),
        (control.lang(30026), "rebuild_database", {'plot': "Rebuild Database"}, 'rebuild_database.png'),
        ("Sync Completed List", "completed_sync", {'plot': "Sync Completed Anime with Otaku"}, "sync_completed.png"),
        ("Download Manager", 'download_manager', {'plot': "Open Download Manager"}, 'download_manager.png'),
        ("Choose Sorting...", 'sort_select', {'plot': "Choose Sorting..."}, ''),
        ("Clear Selected Fanart", 'clear_slected_fanart', {'plot': "Clear All Selected Fanart"}, 'delete.png')
    ]
    control.draw_items([utils.allocate_item(name, url, False, False, image, info) for name, url, info, image in TOOLS_ITEMS], 'files')


# ### Maintenance ###
@Route('settings')
def SETTINGS(payload, params):
    import xbmcaddon
    xbmcaddon.Addon().openSettings()


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


@Route('clear_slected_fanart')
def CLEAR_SELECTED_FANART(payload, params):
    fanart_all = control.getSetting(f'fanart.all').split(',')
    for i in fanart_all:
        control.setSetting(f'fanart.select.anilist.{i}', '')
    control.setSetting('fanart.all', '')
    control.ok_dialog(control.ADDON_NAME, "Completed")
    if params.get('setting'):
        control.exit_code()


@Route('rebuild_database')
def REBUILD_DATABASE(payload, params):
    from resources.lib.ui.database_sync import AnilistSyncDatabase
    AnilistSyncDatabase().re_build_database()
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


@Route('importexport_settings')
def IMPORTEXPORT_SETTINGS(payload, params):
    import os
    import xbmcvfs

    context = control.context_menu(["Import", "Export"])
    setting_xml = os.path.join(control.dataPath, 'settings.xml')

    # Import
    if context == 0:
        import_location = control.browse(1, control.ADDON_NAME, 'files', 'settings.xml')
        if not import_location:
            return control.exit_code()
        if not import_location.endswith('settings.xml'):
            control.ok_dialog(control.ADDON_NAME, "Invalid File!")
        else:
            yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to replace settings.xml?")
            if yesno:
                xbmcvfs.delete(setting_xml)
                xbmcvfs.copy(import_location, setting_xml)
                control.ok_dialog(control.ADDON_NAME, "Replaced settings.xml")

    # Export
    elif context == 1:
        export_location = control.browse(3, control.ADDON_NAME, 'files')
        if not export_location:
            control.ok_dialog(control.ADDON_NAME, "Please Select Export Location!")
        else:
            yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to save settings.xml?")
            if yesno:
                xbmcvfs.copy(setting_xml, os.path.join(export_location, 'settings.xml'))
                control.ok_dialog(control.ADDON_NAME, "Saved settings.xml")

    return control.exit_code()

@Route('toggleLanguageInvoker')
def TOGGLE_LANGUAGE_INVOKER(payload, params):
    import service
    service.toggle_reuselanguageinvoker()


if __name__ == "__main__":
    # import time
    # t0 = time.perf_counter_ns()

    router_process(control.get_plugin_url(), control.get_plugin_params())
    if len(control.playList) > 0:
        import xbmc
        if not xbmc.Player().isPlaying():
            control.playList.clear()
    # t1 = time.perf_counter_ns()
    # totaltime = (t1-t0)/1_000_000
    # control.print(totaltime, 'ms')
