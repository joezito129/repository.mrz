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

import pickle

from resources.lib.AniListBrowser import AniListBrowser
from resources.lib import OtakuBrowser
from resources.lib.ui import control, database, player, utils
from resources.lib.ui.router import route, router_process
from resources.lib.WatchlistIntegration import add_watchlist, watchlist_update_episode


_ANILIST_BROWSER = AniListBrowser(int(control.getSetting("titlelanguage")))


def add_last_watched(items):
    anilist_id = control.getSetting("addon.last_watched")
    try:
        kodi_meta = pickle.loads(database.get_show(anilist_id)['kodi_meta'])
        last_watched = kodi_meta.get('title_userPreferred')
        items.insert(0, (f'{control.lang(30000)}[I]{last_watched}[/I]', f'animes/{anilist_id}///', kodi_meta['poster']))
    except TypeError:
        pass
    return items


@route('find_recommendations/*')
def FIND_RECOMMENDATIONS(payload, params):
    payload_list = payload.rsplit("/")[1:]
    if len(payload_list) == 4:
        path, anilist_id, mal_id, kitsu_id = payload_list
    else:
        path, anilist_id, mal_id, kitsu_id, eps_watched = payload_list

    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']
    control.draw_items(_ANILIST_BROWSER.get_recommendations(anilist_id))


# next page for find_recommendations
@route('recommendations_next/*')
def RECOMMENDATIONS_NEXT(payload, params):
    anilist_id, page = payload.rsplit("/")
    control.draw_items(_ANILIST_BROWSER.get_recommendations(anilist_id, int(page)))


@route('find_relations/*')
def FIND_RELATIONS(payload, params):
    payload_list = payload.rsplit("/")[1:]
    if len(payload_list) == 4:
        path, anilist_id, mal_id, kitsu_id = payload_list
    else:
        path, anilist_id, mal_id, kitsu_id, eps_watched = payload_list
    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']
    control.draw_items(_ANILIST_BROWSER.get_relations(anilist_id))


@route('animes/*')
def ANIMES_PAGE(payload, params):
    payload_list = payload.rsplit("/")
    if len(payload_list) == 3:
        anilist_id, mal_id, kitsu_id = payload_list
    else:
        from resources.lib.WatchlistFlavor import WatchlistFlavor
        anilist_id, mal_id, kitsu_id, null = payload_list
        flavor = WatchlistFlavor.get_update_flavor()
        if flavor:
            try:
                data = flavor.get_watchlist_anime_entry(anilist_id)
                show_meta = database.get_show(anilist_id)
                kodi_meta = pickle.loads(show_meta['kodi_meta'])
                kodi_meta['eps_watched'] = data.get('eps_watched', 0)
                database.update_kodi_meta(anilist_id, kodi_meta)
            except KeyError:
                pass
    anime_general, content = OtakuBrowser.get_anime_init(anilist_id)
    control.draw_items(anime_general, content)


@route('anilist_airing_anime')
def ANILIST_AIRING_ANIME(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_airing_anime())


# next page for anilist_airing_anime
@route('anilist_airing_anime/*')
def ANILIST_AIRING_ANIME(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_airing_anime(int(payload)))


@route('anilist_upcoming_next_season')
def ANILIST_UPCOMING_NEXT_SEASON(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_upcoming_next_season())


# next page for anilist_upcoming_next_season
@route('anilist_upcoming_next_season/*')
def ANILIST_UPCOMING_NEXT_SEASON(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_upcoming_next_season(int(payload)))


@route('anilist_top_100_anime')
def ANILIST_TOP_100_ANIME(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_top_100_anime())


# next page for anilist_top_100_anime
@route('anilist_top_100_anime/*')
def ANILIST_TOP_100_ANIME_PAGES(payload, params):
    return control.draw_items(_ANILIST_BROWSER.get_top_100_anime(int(payload)))


@route('anilist_genres')
def ANILIST_GENRES(payload, params):
    control.draw_items(_ANILIST_BROWSER.get_genres(lambda grenre_dialog: control.multiselect_dialog(control.lang(50010), grenre_dialog)))


# next page for anilist_genres
@route('anilist_genres/*')
def ANILIST_GENRES_PAGES(payload, params):
    genres, tags, page = payload.split("/")[-3:]
    control.draw_items(_ANILIST_BROWSER.get_genres_page(genres, tags, int(page)))


@route('search_history')
def SEARCH_HISTORY(payload, params):
    history = database.getSearchHistory('show')
    if int(control.getSetting('searchhistory')) == 0:
        control.draw_items(OtakuBrowser.search_history(history), "addons", [('Remove from History', 'remove_search_item')])
    else:
        SEARCH(payload, params)


@route('clear_history')
def CLEAR_HISTORY(payload, params):
    database.clearSearchHistory()


@route('remove_search_item/*')
def REMOVE_SEARCH_ITEM(payload, params):
    payload_list = payload.rsplit('search/')
    if len(payload_list) >= 2:
        payload_list = payload_list[1].rsplit('/', 1)
        if len(payload_list) == 2:
            search_item, page = payload_list
            database.remove_search(table='show', value=search_item)
    else:
        control.notify(control.ADDON_NAME, "Invalid Search Item")


@route('search')
def SEARCH(payload, params):
    query = control.keyboard(control.lang(50011))
    if not query:
        import xbmcplugin
        return xbmcplugin.endOfDirectory(control.HANDLE)
    if "Yes" in control.getSetting('searchhistory'):
        database.addSearchHistory(query, 'show')
    control.draw_items(_ANILIST_BROWSER.get_search(query))


# next page for anilist_search
@route('search/*')
def SEARCH_PAGES(payload, params):
    query, page = payload.rsplit("/", 1)
    control.draw_items(_ANILIST_BROWSER.get_search(query, int(page)))


@route('search_results/*')
def SEARCH_RESULTS(payload, params):
    query = params.get('query')
    items = _ANILIST_BROWSER.get_search(query, 1)
    control.draw_items(items)


@route('play/*')
def PLAY(payload, params):
    anilist_id, episode, filter_lang = payload.rsplit("/")
    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    sources = OtakuBrowser.get_sources(anilist_id, episode, filter_lang, 'show', rescrape, source_select)
    _mock_args = {"anilist_id": anilist_id, "episode": episode}

    if control.getSetting('general.playstyle.episode') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        link = SourceSelect(*('source_select.xml', control.ADDON_PATH), actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()

    else:
        from resources.lib.windows.resolver import Resolver
        resolver = Resolver(*('resolver.xml', control.ADDON_PATH), actionArgs=_mock_args)
        link = resolver.doModal(sources, {}, False)
    player.play_source(link, anilist_id, watchlist_update_episode, OtakuBrowser.get_episodeList, int(episode), source_select=source_select, rescrape=rescrape)


@route('play_movie/*')
def PLAY_MOVIE(payload, params):
    payload_list = payload.rsplit("/")
    anilist_id, mal_id, kitsu_id = payload_list
    source_select = bool(params.get('source_select'))
    rescrape = bool(params.get('rescrape'))
    if not anilist_id:
        try:
            anilist_id = database.get_show_mal(mal_id)['anilist_id']
        except TypeError:
            from resources.lib.AniListBrowser import AniListBrowser
            show_meta = _ANILIST_BROWSER.get_mal_to_anilist(mal_id)
            anilist_id = show_meta['anilist_id']
    sources = OtakuBrowser.get_sources(anilist_id, 1, None, 'movie', rescrape, source_select)
    _mock_args = {'anilist_id': anilist_id}

    if control.getSetting('general.playstyle.movie') == '1' or source_select or rescrape:
        from resources.lib.windows.source_select import SourceSelect
        link = SourceSelect(*('source_select.xml', control.ADDON_PATH), actionArgs=_mock_args, sources=sources, rescrape=rescrape).doModal()

    else:
        from resources.lib.windows.resolver import Resolver
        resolver = Resolver(*('resolver.xml', control.ADDON_PATH), actionArgs=_mock_args)
        link = resolver.doModal(sources, {}, False)
    player.play_source(link, anilist_id, watchlist_update_episode, OtakuBrowser.get_episodeList, 1, source_select=source_select, rescrape=rescrape)


@route('marked_as_watched/*')
def MARKED_AS_WATCHED(payload, params):
    from resources.lib.WatchlistFlavor import WatchlistFlavor

    play, anilist_id, episode, filter_lang = payload.rsplit("/")
    flavor = WatchlistFlavor.get_update_flavor()
    watchlist_update_episode(anilist_id, episode)
    control.notify(control.ADDON_NAME, f'Episode #{episode} was Marked as Watched in {flavor.flavor_name}')
    show = database.get_show(anilist_id)
    kitsu_id = show['kitsu_id']     # todo if kitsu_id is None needs to be fixed
    mal_id = show['mal_id']
    control.execute(f'ActivateWindow(Videos,plugin://{control.ADDON_ID}/watchlist_to_ep/{anilist_id}/{mal_id}/{kitsu_id}/{episode})')


@route('delete_anime_database/*')
def DELETE_ANIME_DATABASE(payload, params):
    payload_list = payload.rsplit("/")
    if len(payload_list) == 4:
        path, anilist_id, mal_id, kitsu_id = payload_list
    else:
        path, anilist_id, mal_id, kitsu_id, eps_watched = payload_list
    if not anilist_id:
        anilist_id = database.get_mappings(mal_id, 'mal_id')['anilist_id']

    database.remove_episodes(anilist_id)
    database.remove_season(anilist_id)
    database.update_show_data(anilist_id)
    control.notify(control.ADDON_NAME, 'Removed from database')


@route('auth/*')
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


@route('refresh/*')
def REFRESH(payload, params):
    if payload == 'realdebrid':
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().refreshToken()
    elif payload == 'debridlink':
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().refreshToken()


@route('download_manager')
def DOWNLOAD_MANAGER(payload, params):
    from resources.lib.windows.download_manager import DownloadManager
    DownloadManager(*('download_manager.xml', control.ADDON_PATH)).doModal()


@route('settings')
def SETTINGS(payload, params):
    import xbmcaddon
    xbmcaddon.Addon().openSettings()


@route('toggleLanguageInvoker')
def TOGGLE_LANGUAGE_INVOKER(payload, params):
    control.toggle_reuselanguageinvoker()


@route('completed_sync')
def COMPLETED_SYNC(payload, params):
    from resources.lib.ui import maintenance
    maintenance.sync_watchlist()


@route('clear_cache')
def CLEAR_CACHE(payload, params):
    database.cache_clear()


@route('clear_torrent_cache')
def CLEAR_TORRENT_CACHE(payload, params):
    database.torrent_cache_clear()


@route('rebuild_database')
def REBUILD_DATABASE(payload, params):
    from resources.lib.ui.database_sync import AnilistSyncDatabase
    AnilistSyncDatabase().re_build_database()


@route('change_log')
def CHANGE_LOG(payload, params):
    control.getChangeLog()


@route('tools')
def TOOLS_MENU(payload, params):
    TOOLS_ITEMS = [
        (control.lang(30027), "change_log", 'changelog.png'),
        (control.lang(30020), "settings", 'open_settings_menu.png'),
        (control.lang(30021), "clear_cache", 'clear_cache.png'),
        (control.lang(30022), "clear_torrent_cache", 'clear_local_torrent_cache.png'),
        (control.lang(30023), "clear_history", 'clear_search_history.png'),
        (control.lang(30026), "rebuild_database", 'rebuild_database.png'),
        ("Sync Completed List", "completed_sync", "sync_completed.png"),
        ("Download Manager", 'download_manager', 'download_manager.png')
        # (control.lang(30024), "wipe_addon_data", 'wipe_addon_data.png'),
    ]
    control.draw_items([utils.allocate_item(name, url, True, image, isfolder=False) for name, url, image in TOOLS_ITEMS], "addons")


@route('')
def LIST_MENU(payload, params):
    MENU_ITEMS = [
        (control.lang(50001), "anilist_airing_anime", 'airing_anime.png'),
        (control.lang(50034), "anilist_upcoming_next_season", 'upcoming.png'),
        (control.lang(50009), "anilist_top_100_anime", 'top_100_anime.png'),
        (control.lang(50010), "anilist_genres", 'genres_&_tags.png'),
        (control.lang(50011), "search_history", 'search.png'),
        (control.lang(50012), "tools", 'tools.png')

    ]
    if control.getSetting('menu.lastwatched') == 'true':
        MENU_ITEMS = add_last_watched(MENU_ITEMS)
    MENU_ITEMS = add_watchlist(MENU_ITEMS)
    MENU_ITEMS_ = MENU_ITEMS[:]
    for i in MENU_ITEMS:
        if control.getSetting(i[1]) == 'false':
            MENU_ITEMS_.remove(i)
    control.draw_items([utils.allocate_item(name, url, True, image) for name, url, image in MENU_ITEMS_], "addons")


if __name__ == "__main__":
    router_process(control.get_plugin_url(), control.get_plugin_params())
    if len(player.playList) != 0 and not player.player().isPlaying():
        player.playList.clear()
# t1 = time.perf_counter_ns()
# totaltime = (t1-t0)/1_000_000
# control.print(totaltime, 'ms')

# todo

# get rid of client module
# get rid of bare excepts


# todo
