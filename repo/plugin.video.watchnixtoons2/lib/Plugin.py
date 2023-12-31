# -*- coding: utf-8 -*-
import re, requests
import six

from itertools import chain
from base64 import b64decode
from time import time, sleep
from six.moves import urllib_parse
from string import ascii_uppercase

import xbmcplugin
import ssl

from lib.constants import *
from lib.Common import *
from lib.SimpleTrakt import SimpleTrakt
from lib.recently_watched import recently_watched_load, recently_watched_add, recently_watched_remove

# Disable urllib3's "InsecureRequestWarning: Unverified HTTPS request is being made" warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter


class TLS11HttpAdapter(HTTPAdapter):
    # "Transport adapter" that allows us to use TLSv1.1
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_version=ssl.PROTOCOL_TLSv1_1)


class TLS12HttpAdapter(HTTPAdapter):
    # "Transport adapter" that allows us to use TLSv1.2
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_version=ssl.PROTOCOL_TLSv1_2)

s = requests.session()
tls_adapters = [TLS12HttpAdapter(), TLS11HttpAdapter()]

ADDON = xbmcaddon.Addon()
#language
__language__ = ADDON.getLocalizedString
# Show catalog: whether to show the catalog categories or to go straight to the "ALL" section with all items visible.
ADDON_SHOW_CATALOG = ADDON.getSetting('showCatalog') == 'true'
# Use Latest Releases date: whether to sort the Latest Releases items by their date, or with a catalog.
ADDON_LATEST_DATE = ADDON.getSetting('useLatestDate') == 'true'
# Use Latest Releases thumbs: whether to show a little thumbnail available for the Latest Releases items only.
ADDON_LATEST_THUMBS = ADDON.getSetting('showLatestThumbs') == 'true'
# Use poster images for each catalog folder. Makes for a better experience on custom Kodi skins.
ADDON_CATALOG_THUMBS = ADDON.getSetting('showCatalogThumbs') == 'true'
# Uses ids from files for the ongoing & popular to show the thumbnails
ADDON_POPULAR_THUMBS = ADDON.getSetting('showPopularThumbs') == 'true'
# Uses ids from files for the series to show the thumbnails
ADDON_SERIES_THUMBS = ADDON.getSetting('showSeriesThumbs') == 'true'
# Uses URL to get fan art for videos
ADDON_VIDEO_FANART = ADDON.getSetting('showVideoFanart') == 'true'

ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_ICON_DICT = {'icon': ADDON_ICON, 'thumb': ADDON_ICON, 'poster': ADDON_ICON}
RESOURCE_URL = 'special://home/addons/{0}resources/'.format(PLUGIN_NAME)
ADDON_TRAKT_ICON = RESOURCE_URL + 'media/traktIcon.png'

# Initialized in 'actionResolve()'.
MEDIA_HEADERS = None

# Url paths: paths to parts of the website, to be added to the BASEURL url.
# Also used to tell what kind of catalog is loaded in memory.
# In case they change in the future it'll be easier to modify in here.
URL_PATHS = {
    'latest': 'latest', # No path used, 'makeLatestCatalog()' uses the homepage of the mobile website.
    'popular': 'popular', # No path used, 'makePopularCatalog()' uses the hompage of the desktop website.
    'dubbed': '/dubbed-anime-list',
    'cartoons': '/cartoon-list',
    'subbed': '/subbed-anime-list',
    'movies': '/movie-list',
    'latestmovies': '/anime/movies',
    'ova': '/ova-list',
    'search': '/search',
    'genre': '/search-by-genre'
}


def actionMenu(params):

    def _menuItem(title, data, color):
        item = xbmcgui.ListItem('[B][COLOR ' + color + ']' + title + '[/COLOR][/B]', label2 = title)
        item.setArt(ADDON_ICON_DICT)
        item_set_info( item, {'title': title, 'plot': title} )
        return (buildURL(data), item, True)

    xbmcplugin.addDirectoryItems(
        PLUGIN_ID,
        (
            # Latest
            _menuItem( __language__(30050), {'action': 'actionCatalogMenu', 'path': URL_PATHS['latest']}, 'mediumaquamarine' ),
            # Latest Movies - Make the Latest Movies menu go straight to the item list, no catalog.
            _menuItem( __language__(30051), {'action': 'actionLatestMoviesMenu', 'path': URL_PATHS['latestmovies']}, 'mediumaquamarine'),
            # Ongoing & Popular
            _menuItem( __language__(30052), {'action': 'actionCatalogMenu', 'path': URL_PATHS['popular']}, 'mediumaquamarine'),
            # Dubbed
            _menuItem( __language__(30053), {'action': 'actionCatalogMenu', 'path': URL_PATHS['dubbed']}, 'lightgreen'),
            # Cartoons
            _menuItem( __language__(30054), {'action': 'actionCatalogMenu', 'path': URL_PATHS['cartoons']}, 'lightgreen'),
            # Subbed
            _menuItem( __language__(30055), {'action': 'actionCatalogMenu', 'path': URL_PATHS['subbed']}, 'lightgreen'),
            # Movies
            _menuItem( xbmc.getLocalizedString(342), {'action': 'actionCatalogMenu', 'path': URL_PATHS['movies']}, 'lightgreen'),
            # OVAs
            _menuItem( __language__(30056), {'action': 'actionCatalogMenu', 'path': URL_PATHS['ova']}, 'lightgreen'),
            # Recently Watched
            _menuItem( __language__(30057), {'action': 'actionRecentlyWatchedMenu', 'path': 'recently_watched'}, 'orange'),
            # Search - Non-web path.
            _menuItem( xbmc.getLocalizedString(137), {'action': 'actionSearchMenu',  'path': 'search'}, 'lavender'),
            # Settings - Non-web path.
            _menuItem( xbmc.getLocalizedString(1390), {'action': 'actionShowSettings','path': 'settings'}, 'lavender')
        )
    )
    xbmcplugin.endOfDirectory(PLUGIN_ID)


def actionCatalogMenu(params):
    xbmcplugin.setContent(PLUGIN_ID, 'tvshows')
    catalog = getCatalogProperty(params)

    if ADDON_SHOW_CATALOG:
        def _catalogMenuItemsMake():
            items = [ ]
            if ADDON_CATALOG_THUMBS:
                # The catalog folders will each get a letter image, taken from the web (this way
                # these images don't have to be distributed w/ the add-on, if they're not needed).
                # After they're downloaded, the images exist in Kodi's image cache folders.
                artDict = {'thumb': None}
                for sectionName in sorted(catalog.keys()):
                    if catalog[sectionName]:
                        item = xbmcgui.ListItem(sectionName)
                        # Correct the address for the '#' (miscellaneous, non-letter) category.
                        artDict['thumb'] = THUMBS_BASEURL + ('0' if sectionName == '#' else sectionName) + '.png'
                        item.setArt(artDict)
                        item_set_info( item, {'plot': sectionName} )
                        items.append(
                            (
                                buildURL({'action': 'actionCatalogSection', 'path': params['path'], 'section': sectionName}),
                                item,
                                True
                            )
                        )
            else:
                items = [
                    (
                        buildURL({'action': 'actionCatalogSection', 'path': params['path'], 'section': sectionName}),
                        xbmcgui.ListItem(sectionName),
                        True
                    )
                    for sectionName in sorted(catalog.keys()) if len(catalog[sectionName])
                ]
            # See if an "All" folder is necessary (when there's more than one folder in the catalog).
            if len(items) > 1:
                sectionAll = (
                    buildURL({'action': 'actionCatalogSection', 'path': params['path'], 'section': 'ALL'}),
                    xbmcgui.ListItem('All'),
                    True
                )
                if ADDON_CATALOG_THUMBS:
                    artDict['thumb'] = THUMBS_BASEURL + 'ALL.png'
                    sectionAll[1].setArt(artDict)
                    item_set_info( sectionAll[1], {'plot': 'All'} )
                return [sectionAll] + items
            else:
                return items

        items = _catalogMenuItemsMake()
        if items:
            if len(items) > 1:
                xbmcplugin.addDirectoryItems(PLUGIN_ID, items)
            else:
                # Conveniency when a search leads to only 1 result, show it already without the catalog screen.
                params['section'] = 'ALL'
                actionCatalogSection(params)
                return
        else:
            xbmcplugin.addDirectoryItem(PLUGIN_ID, '', xbmcgui.ListItem('(No Results)'), isFolder=False)
        xbmcplugin.endOfDirectory(PLUGIN_ID)
        setViewMode()
    else:
        params['section'] = 'ALL'
        actionCatalogSection(params)


def actionCatalogSection(params):

    catalog = getCatalogProperty(params)
    path = params['path']

    # Set up a boolean indicating if the catalog items are already playable, instead of being folders
    # with more items inside.
    # This is true for the OVA, movies, latest-episodes, movie-search and episode-search catalogs.
    # Items in these catalogs link to the video player pages already.
    isSpecial = (
        path in {URL_PATHS['ova'], URL_PATHS['movies'], URL_PATHS['latest']}
        or params.get('searchType', 'series') not in {'series', 'genres'} # not series = movies or episodes search
    )

    if isSpecial:
        action = 'actionResolve'
        isFolder = False
    else:
        action = 'actionEpisodesMenu'
        isFolder = True

    thumb = params.get('thumb', ADDON_ICON)
    if path != URL_PATHS['latest'] or not ADDON_LATEST_THUMBS:
        artDict = {'icon': thumb, 'thumb': thumb, 'poster': thumb} if thumb else None
    else:
        artDict = {'icon': thumb, 'thumb': 'DefaultVideo.png', 'poster': 'DefaultVideo.png'} if thumb else None

    # Persistent property with item metadata, used with the "Show Information" context menu.
    infoItems = getWindowProperty(PROPERTY_INFO_ITEMS) or { }

    if 'query' not in params and ADDON.getSetting('cleanupEpisodes') == 'true':
        listItemFunc = makeListItemClean
    else:
        listItemFunc = makeListItem

    if params['section'] == 'ALL':
        sectionItems = chain.from_iterable(catalog[sectionName] for sectionName in sorted(catalog))
    else:
        sectionItems = catalog[params['section']]

    def _sectionItemsGen():

        # init variables for deciding how list items are going to be displayed
        remove_base = False
        show_thumbs = False
        show_fanart = False
        from_hash = False

        if path == URL_PATHS['latest']:

            if ADDON_LATEST_THUMBS:
                show_thumbs = True

            if ADDON_VIDEO_FANART:
                show_fanart = True

        elif ADDON_POPULAR_THUMBS and path == URL_PATHS['popular']:

            remove_base = True
            show_thumbs = True
            from_hash = True
            hashes = {}

            # get all hash files and combine as could be in any of them
            for path_tmp in [ URL_PATHS['dubbed'], URL_PATHS['cartoons'], URL_PATHS['subbed'] ]:

                f = open( translate_path( RESOURCE_URL + 'data/' + path_tmp.replace('/','') + '.json' ) )
                hashes.update( json.load(f) )

        elif ADDON_SERIES_THUMBS and path in [ URL_PATHS['dubbed'], URL_PATHS['cartoons'], URL_PATHS['subbed'] ]:

            show_thumbs = True
            from_hash = True

            # get required hash file for thumbnails
            f = open( translate_path( RESOURCE_URL + 'data/' + path.replace('/','') + '.json' ) )
            hashes = json.load(f)

        elif path in [ URL_PATHS['movies'], URL_PATHS['ova'] ]:

            remove_base = True

            if ADDON_SERIES_THUMBS:

                show_thumbs = True
                from_hash = True

                # get required hash file for thumbnails
                f = open( translate_path( RESOURCE_URL + 'data/' + path.replace('/','') + '.json' ) )
                hashes = json.load(f)

            # we can also use the fanart for movies and OVAs
            if ADDON_VIDEO_FANART:
                show_fanart = True

        # loop through entries and decide what to show
        for entry in sectionItems:

            entryURL = entry[0]

            if remove_base:
                # removes base so can be used in hash table
                entryURL = entryURL.replace( BASEURL, '' )

            # If there's metadata for this entry (requested by the user with "Show Information"), use it.
            if entryURL in infoItems:
                entryParams = None
                itemPlot, itemThumb = infoItems[entryURL]
                entryArt = {'icon': ADDON_ICON, 'thumb': itemThumb, 'poster': itemThumb}
            else:

                # do this here so we only need to create a hash once per entry
                if show_thumbs and from_hash:
                    hashURL = generateMd5( entryURL )

                # Decide what artwork to show
                if show_thumbs and from_hash is False:
                    entryArt = {'icon':ADDON_ICON,'thumb':entry[2],'poster':entry[2]}
                elif show_thumbs and from_hash and hashes.get( hashURL, False ):
                    thumb_from_hash = IMAGES_URL + '/catimg/' + hashes.get( hashURL, '' ) + '.jpg'
                    entryArt = {'icon': ADDON_ICON, 'thumb': thumb_from_hash, 'poster': thumb_from_hash}
                else:
                    entryArt = artDict

                itemPlot = ''
                entryParams = params

            # add fanart if option is selected
            # this is addded last as is not affected by anything else
            if show_fanart:
                entryArt['fanart'] = IMAGES_URL + '/thumbs' + entryURL + '.jpg'

            yield (
                buildURL({'action': action, 'url': entryURL}),
                listItemFunc(entry[1], entryURL, entryArt, itemPlot, isFolder, isSpecial, entryParams),
                isFolder
            )

    xbmcplugin.addDirectoryItems(PLUGIN_ID, tuple(_sectionItemsGen()))
    xbmcplugin.endOfDirectory(PLUGIN_ID)
    setViewMode() # Set the skin layout mode if the option is enabled.


def actionEpisodesMenu(params):
    xbmcplugin.setContent(PLUGIN_ID, 'episodes')

    # Memory-cache the last episode list, to help when the user goes back and forth while watching
    # multiple episodes of the same show. This way only one web request is needed for the same show.
    lastListURL = getRawWindowProperty(PROPERTY_EPISODE_LIST_URL)
    if lastListURL and lastListURL == params['url']:
        listData = getWindowProperty(PROPERTY_EPISODE_LIST_DATA)
    else:
        # New domain safety replace, in case the user is coming in from an old Kodi favorite item.
        url = params['url'].replace('wcofun.com', 'wcofun.org', 1)
        r = requestHelper(url if url.startswith('http') else BASEURL + url)
        html = r.text

        plot, thumb = getPageMetadata(html)

        dataStartIndex = html.find('"sidebar_right3"')
        if dataStartIndex == -1:
            raise Exception('Episode list scrape fail: ' + url)

        # Episode list data: a tuple with the thumb, plot and an inner tuple of per-episode data.
        listData = (
            thumb,
            plot,
            tuple(
                match.groups()
                for match in re.finditer(
                    '''<a href="([^"]+).*?>([^<]+)''', html[dataStartIndex : html.find('"sidebar-all"')]
                )
            )
        )
        setRawWindowProperty(PROPERTY_EPISODE_LIST_URL, params['url'])
        setWindowProperty(PROPERTY_EPISODE_LIST_DATA, listData)

    def _episodeItemsGen():
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        showURL = params['url']
        thumb = listData[0]
        artDict = {'icon': thumb, 'thumb': thumb, 'poster': thumb} if thumb else None
        plot = listData[1]

        listItemFunc = makeListItemClean if ADDON.getSetting('cleanupEpisodes') == 'true' else makeListItem

        itemParams = {'action': 'actionResolve', 'url': None}
        listIter = iter(listData[2]) if ADDON.getSetting('reverseEpisodes') == 'true' else reversed(listData[2])

        for URL, title in listIter:

            # add fanart if option is selected
            if ADDON_VIDEO_FANART:
                artDict['fanart'] = URL.replace( BASEURL, IMAGES_URL + '/thumbs' ) + '.jpg'

            item = listItemFunc(title, URL, artDict, plot, isFolder=False, isSpecial=False, oldParams=None)
            itemParams['url'] = URL
            itemURL = buildURL(itemParams)
            playlist.add(itemURL, item)
            yield (itemURL, item, False)

    xbmcplugin.addDirectoryItems(PLUGIN_ID, tuple(_episodeItemsGen()))
    xbmcplugin.endOfDirectory(PLUGIN_ID)


def actionLatestMoviesMenu(params):
    # Returns a list of links from a hidden "/anime/movies" area.
    # Since this page is large, we memory cache it after it's been requested.
    html = getRawWindowProperty(PROPERTY_LATEST_MOVIES)
    if not html:
        r = requestHelper(BASEURL + params['path'])
        html = r.text
        setRawWindowProperty(PROPERTY_LATEST_MOVIES, html)

    # Similar scraping logic to 'actionEpisodesMenu()'.

    dataStartIndex = html.find('"sidebar_right3"')
    if dataStartIndex == -1:
        raise Exception('Latest movies scrape fail')

    # Persistent property with item metadata.
    infoItems = getWindowProperty(PROPERTY_INFO_ITEMS) or { }

    if ADDON_SERIES_THUMBS:
        # get required hash file for thumbnails
        f = open( translate_path( RESOURCE_URL + 'data/movie-list.json' ) )
        hashes = json.load(f)

    def _movieItemsGen():

        reIter = re.finditer(
            '''<a href="([^"]+).*?>([^<]+)''', html[dataStartIndex : html.find('"sidebar-all"')]
        )

        # The page has like 6000 items going back to 2010, so we limit to only the latest 200.
        for x in range(200):

            # use default addon dict by default
            artDict = ADDON_ICON_DICT

            entryURL, entryTitle = next(reIter).groups()

            if ADDON_SERIES_THUMBS:
                entryHash = generateMd5( entryURL.replace( BASEURL, '' ) )
                if entryHash in hashes.keys():
                    thumb_from_hash = IMAGES_URL + '/catimg/' + hashes[ entryHash ] + '.jpg'
                    artDict = {'icon': ADDON_ICON, 'thumb': thumb_from_hash, 'poster': thumb_from_hash}

            if entryURL in infoItems:
                entryPlot, entryThumb = infoItems[entryURL]
                artDict = {'icon': ADDON_ICON, 'thumb': entryThumb, 'poster': entryThumb}
                entryParams = None
            else:
                entryPlot = ''
                entryParams = params

            # add fanart if option is selected
            if ADDON_VIDEO_FANART:
                artDict['fanart'] = entryURL.replace( BASEURL, IMAGES_URL + '/thumbs' ) + '.jpg'

            yield (
                buildURL({'action': 'actionResolve', 'url': entryURL}),
                makeListItem(
                    unescapeHTMLText(entryTitle),
                    entryURL,
                    artDict,
                    entryPlot,
                    isFolder = False,
                    isSpecial = True,
                    oldParams = entryParams
                ),
                False
            )

    xbmcplugin.addDirectoryItems(PLUGIN_ID, tuple(_movieItemsGen()))
    xbmcplugin.endOfDirectory(PLUGIN_ID)
    setViewMode()

def actionRecentlyWatchedMenu(params):

    data = recently_watched_load()

    # Persistent property with item metadata.
    infoItems = getWindowProperty(PROPERTY_INFO_ITEMS) or { }

    if ADDON_SERIES_THUMBS:
        hashes = {}

        # get all hash files and combine as could be in any of them
        for path_tmp in [ URL_PATHS['dubbed'], URL_PATHS['cartoons'], URL_PATHS['subbed'] ]:

            f = open( translate_path( RESOURCE_URL + 'data/' + path_tmp.replace('/','') + '.json' ) )
            hashes.update( json.load(f) )

    def _recentlyWatchedItemsGen():
        for title_hash, title_data in reversed(data.items()):

            itemPlot = ''

            # If there's metadata for this entry (requested by the user with "Show Information"), use it.
            if title_data[ 'url' ] in infoItems:
                itemPlot, itemThumb = infoItems[title_data[ 'url' ]]
                artDict = {'icon': ADDON_ICON, 'thumb': itemThumb, 'poster': itemThumb}
            else:

                # use default addon dict by default
                artDict = ADDON_ICON_DICT

                if ADDON_SERIES_THUMBS and title_hash in hashes.keys():
                    thumb_from_hash = IMAGES_URL + '/catimg/' + hashes[ title_hash ] + '.jpg'
                    artDict = {'icon': ADDON_ICON, 'thumb': thumb_from_hash, 'poster': thumb_from_hash}

            yield (
                buildURL({'action': 'actionEpisodesMenu', 'url': title_data[ 'url' ]}),
                makeListItem(title_data[ 'name' ], title_data[ 'url' ], artDict, itemPlot, True, None, None, True),
                True
            )

    xbmcplugin.addDirectoryItems(PLUGIN_ID, tuple(_recentlyWatchedItemsGen()))
    xbmcplugin.endOfDirectory(PLUGIN_ID)
    setViewMode() # Set the skin layout mode if the option is enabled.


# A sub menu, lists search options.
def actionSearchMenu(params):

    def _modalKeyboard(heading):
        kb = xbmc.Keyboard('', heading)
        kb.doModal()
        return kb.getText() if kb.isConfirmed() else ''

    if 'searchType' in params:
        # Support for the 'actionShowInfo()' function reloading this route, sending it an already searched query.
        # This also supports external query calls, like from OpenMeta.
        if 'query' in params:
            query = params['query']
        else:
            query = _modalKeyboard(params.get('searchTitle', 'Search'))

        if query:
            historyTypeIDs = {'series':'0', 'movies':'1', 'episodes':'2'}
            previousHistory = ADDON.getSetting('searchHistory')
            if previousHistory:
                # Limit search history to 40 items.
                if previousHistory.count('\n') == 40:
                    previousHistory = previousHistory[:previousHistory.rfind('\n')] # Forget the oldest search result.
                ADDON.setSetting('searchHistory', historyTypeIDs[params['searchType']] + query + '\n' + previousHistory)
            else:
                ADDON.setSetting('searchHistory', historyTypeIDs[params['searchType']] + query)

            params['query'] = query
            params['section'] = 'ALL' # Force an uncategorized display (results are usually few).
            actionCatalogSection(params) # Send the search type and query for the catalog functions to use.
        return

    xbmcplugin.addDirectoryItems(
        # URL_PATHS['search'] - special, non-web path used by 'getCatalogProperty()'.
        PLUGIN_ID,
        (
            (
                buildURL({
                    'action': 'actionSearchMenu',
                    'path': URL_PATHS['search'],
                    'searchType': 'series',
                    'searchTitle': __language__(30100)
                }),
                xbmcgui.ListItem('[COLOR lavender][B]' + __language__(30100) + '[/B][/COLOR]'),
                True
            ),
            (
                buildURL({
                    'action': 'actionSearchMenu',
                    'path': URL_PATHS['search'],
                    'searchType': 'movies',
                    'searchTitle': __language__(30101)
                }),
                xbmcgui.ListItem('[COLOR lavender][B]' + __language__(30101) + '[/B][/COLOR]'),
                True
            ),
            (
                buildURL({
                    'action': 'actionSearchMenu',
                    'path': URL_PATHS['search'],
                    'searchType': 'episodes',
                    'searchTitle': __language__(30102)
                }),
                xbmcgui.ListItem('[COLOR lavender][B]' + __language__(30102) + '[/B][/COLOR]'),
                True
            ),
            (
                buildURL({'action': 'actionGenresMenu', 'path': URL_PATHS['genre']}),
                xbmcgui.ListItem('[COLOR lavender][B]' + __language__(30103) + '[/B][/COLOR]'),
                True
            ),
            (
                buildURL({'action': 'actionTraktMenu', 'path': 'trakt'}),
                xbmcgui.ListItem('[COLOR lavender][B]' + __language__(30104) + '[/B][/COLOR]'),
                True
            ),
            (
                buildURL({'action': 'actionSearchHistory', 'path': 'searchHistory'}),
                xbmcgui.ListItem('[COLOR lavender][B]' + __language__(30105) + '[/B][/COLOR]'),
                True
            )
        )
    )

    xbmcplugin.endOfDirectory(PLUGIN_ID)


# A sub menu, lists all previous searches along with their categories.
def actionSearchHistory(params):

    # Non-UI setting, it's just a big string.
    history = ADDON.getSetting('searchHistory').split('\n')

    # A blank string split creates a list with a blank string inside
    # so test if the first item is valid.
    if history[0]:
        # Use list indexes to map to 'searchType' and a label prefix.
        historyTypeNames = ['series', 'movies', 'episodes']
        historyPrefixes = ['(Cartoon/Anime)', '(Movie)', '(Episode)']

        searchPath = URL_PATHS['search']

        historyItems = tuple(
            (
                buildURL({
                    'query': itemQuery,
                    'searchType': historyTypeNames[itemType],
                    'path': searchPath,
                    'section': 'ALL',
                    'action': 'actionCatalogSection'
                }),
                xbmcgui.ListItem('[B]%s[/B] "%s"' % (historyPrefixes[itemType], itemQuery)),
                True
            )
            for itemType, itemQuery in (
                (int(itemString[0]), itemString[1:]) for itemString in history
            )
        )
        clearHistoryItem = (
            buildURL({'action': 'actionSearchHistoryClear'}), xbmcgui.ListItem('[B]Clear History...[/B]'), False
        )
        xbmcplugin.addDirectoryItems(PLUGIN_ID, (clearHistoryItem,) + historyItems)
    else:
        xbmcplugin.addDirectoryItem(PLUGIN_ID, '', xbmcgui.ListItem('(No History)'), isFolder=False)
    xbmcplugin.endOfDirectory(PLUGIN_ID)


def actionSearchHistoryClear(params):
    dialog = xbmcgui.Dialog()
    if dialog.yesno('Clear Search History', 'Are you sure?'):
        ADDON.setSetting('searchHistory', '')
        dialog.notification(PLUGIN_TITLE, 'Search history cleared', xbmcgui.NOTIFICATION_INFO, 3000, False)
        # Show the search menu afterwards.
        xbmc.executebuiltin('Container.Update(' + PLUGIN_URL + '?action=actionSearchMenu,replace)')


# A sub menu, lists the genre categories in the genre search.
def actionGenresMenu(params):
    r = requestHelper(BASEURL + URL_PATHS['genre'])
    html = r.text

    dataStartIndex = html.find(r'ddmcc">')
    if dataStartIndex == -1:
        raise Exception('Genres list scrape fail')

    xbmcplugin.addDirectoryItems(
        PLUGIN_ID,
        tuple(
            (
                buildURL({
                    'action': 'actionCatalogMenu',
                    'path': '/search-by-genre/page/' + match.group(1).rsplit('/', 1)[1],
                    'searchType': 'genres'
                }),
                xbmcgui.ListItem(match.group(2)),
                True
            )
            for match in re.finditer('''<a.*?"([^"]+).*?>(.*?)</''', html[dataStartIndex : html.find(r'</div></div>')])
        )
    )
    xbmcplugin.endOfDirectory(PLUGIN_ID)


def actionTraktMenu(params):
    instance = SimpleTrakt.getInstance()
    if instance.ensureAuthorized(ADDON):

        def _traktMenuItemsGen():
            traktIconDict = {'icon': ADDON_TRAKT_ICON, 'thumb': ADDON_TRAKT_ICON, 'poster': ADDON_TRAKT_ICON}
            for listName, listURL, listDescription in instance.getUserLists(ADDON):
                item = xbmcgui.ListItem(listName)
                item.setArt(traktIconDict)
                item_set_info( item, {'title': listName, 'plot': listDescription} )
                yield (
                    buildURL({'action': 'actionTraktList', 'listURL': listURL}),
                    item,
                    True
                )

        xbmcplugin.addDirectoryItems(PLUGIN_ID, tuple(_traktMenuItemsGen()))
        xbmcplugin.endOfDirectory(PLUGIN_ID) # Only finish the directory if the user is authorized it.


def actionTraktList(params):
    instance = SimpleTrakt.getInstance()
    if instance.ensureAuthorized(ADDON):

        def _traktListItemsGen():
            traktIconDict = {'icon': ADDON_TRAKT_ICON, 'thumb': ADDON_TRAKT_ICON, 'poster': ADDON_TRAKT_ICON}
            for itemName, overview, searchType, query in sorted(instance.getListItems(params['listURL'], ADDON)):
                item = xbmcgui.ListItem(itemName)
                item_set_info( item, {'title': itemName, 'plot': overview} )
                item.setArt(traktIconDict)
                yield (
                    # Trakt items will lead straight to a show name search.
                    buildURL({
                        'action': 'actionCatalogMenu',
                        'path': URL_PATHS['search'],
                        'query': query,
                        'searchType': searchType,
                    }),
                    item,
                    True
                )

        xbmcplugin.addDirectoryItems(PLUGIN_ID, tuple(_traktListItemsGen()))
    xbmcplugin.endOfDirectory(PLUGIN_ID)


def actionTraktAbout(params):
    xbmcgui.Dialog().ok(
        PLUGIN_TITLE,
        'To search for items in your Trakt lists in WNT2, go to [B]Search > Search by Trakt List[/B] and pair your ' \
        'account. Searching for an item this way does a name search, same as if you went and searched for that ' \
        'name manually.'
    )


def actionClearTrakt(params):
    if 'watchnixtoons2' in xbmc.getInfoLabel('Container.PluginName'):
        xbmc.executebuiltin('Dialog.Close(all)')

    # Kinda buggy behavior.
    # Need to wait a bit and recreate the xbmcaddon.Addon() reference,
    # otherwise the settings don't seem to be changed.
    # See https://forum.kodi.tv/showthread.php?tid=290353&pid=2425543#pid2425543
    global ADDON
    xbmc.sleep(500)
    if SimpleTrakt.clearTokens(ADDON):
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Trakt tokens cleared', xbmcgui.NOTIFICATION_INFO, 3500, False)
    else:
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Trakt tokens already cleared', xbmcgui.NOTIFICATION_INFO, 3500, False)
    ADDON = xbmcaddon.Addon()

def actionRecentlyWatchedRemove(params):

    """ Removes from recently watched """

    if recently_watched_remove( params['url'] ):
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Removed from recently watched', xbmcgui.NOTIFICATION_INFO, 3000, True)

    return


def actionRestoreDatabase(params):

    if not xbmcgui.Dialog().yesno(
        PLUGIN_TITLE,
        'This will update the Kodi database to remember any WatchNixtoons2 episodes that were already watched, ' \
        'but forgotten after an add-on update.\nProceed?',
        nolabel = 'Cancel',
        yeslabel = 'Ok'
    ):
        return

    # Action called from the settings dialog.
    # This will update all the WatchNixtoons2 'strFilename' columns of table 'files' of Kodi's MyVideos###.db
    # with the new BASEURL used by the add-on so that episodes are still considered as watched (playcount >= 1).

    try:
        import sqlite3
    except Exception:
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'sqlite3 not found', xbmcgui.NOTIFICATION_WARNING, 3000, True)
        return

    # Find the 'MyVideos###.db' file.
    dirs, files = xbmcvfs.listdir('special://database')
    for file in files:
        if 'MyVideos' in file and file.endswith('.db'):
            path = translate_path('special://database/' + file)
            break
    else:
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'MyVideos database file not found', xbmcgui.NOTIFICATION_WARNING, 3000, True)
        return

    # Update the database.

    OLD_DOMAINS = getOldDomains()
    NEW_DOMAIN = BASEURL.replace('https://', '', 1) # Make sure to strip the scheme from the current address.
    replaceDomainFunc = lambda original, oldDomain: original.replace(oldDomain, NEW_DOMAIN)
    totalUpdates = 0

    try:
        connection = sqlite3.connect(path)
    except Exception as e:
        xbmcDebug(e)
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Unable to connect to MyVideos database', xbmcgui.NOTIFICATION_WARNING, 3000, True)
        return

    if six.PY3:
        from functools import reduce

    getCursor = connection.cursor()
    setCursor = connection.cursor()
    pattern = PLUGIN_URL + '%actionResolve%'
    for idFile, strFilename in getCursor.execute(
        "SELECT idFile,strFilename FROM files WHERE strFilename LIKE '%s'" % pattern
    ):
        if any(oldDomain in strFilename for oldDomain in OLD_DOMAINS):
            strFilename = reduce(replaceDomainFunc, OLD_DOMAINS, strFilename)
            setCursor.execute("UPDATE files SET strFilename=? WHERE idFile=?", (strFilename, idFile))
            totalUpdates += 1

    try:
        if totalUpdates:
            connection.commit() # Only commit if needed.
        connection.close()
    except Exception:
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Unable to update the database (file permission error?)', xbmcgui.NOTIFICATION_WARNING, 3000, True)
        return

    # Bring a notification before finishing.
    if totalUpdates:
        xbmcgui.Dialog().ok(PLUGIN_TITLE, 'Database update complete (%i items updated).' % totalUpdates)
    else:
        xbmcgui.Dialog().ok(PLUGIN_TITLE, 'Finished. No updates needed (0 items updated).')


def actionUpdateFavourites(params):

    if not xbmcgui.Dialog().yesno(
        PLUGIN_TITLE,
        'This will update any of your Kodi Favourites created with older versions of WatchNixtoons2 so they can point ' \
        'to the latest web address that the add-on uses.\nProceed?',
        nolabel = 'Cancel',
        yeslabel = 'Ok'
    ):
        return

    # Action called from the settings dialog.
    # This will update all the Kodi favourites that use WatchNixtoons2 so that they use the new BASEURL.

    FAVOURITES_PATH = 'special://userdata/favourites.xml'

    file = xbmcvfs.File(FAVOURITES_PATH)
    favoritesText = file.read()
    file.close()
    originalText = favoritesText[:] # Get a backup copy of the content.

    OLD_DOMAINS = getOldDomains()
    NEW_DOMAIN = BASEURL.replace('https://', '', 1) # Make sure to strip the scheme.
    replaceDomainFunc = lambda original, oldDomain: original.replace(oldDomain, NEW_DOMAIN)

    if any(oldDomain in originalText for oldDomain in OLD_DOMAINS):

        if six.PY3:
            from functools import reduce

        favoritesText = reduce(replaceDomainFunc, getOldDomains(), favoritesText)

        try:
            file = xbmcvfs.File(FAVOURITES_PATH, 'w')
            file.write(favoritesText)
            file.close()
        except Exception:
            try:
                # Try again, in case this was some weird encoding error and not a write-permission error.
                file = xbmcvfs.File(FAVOURITES_PATH, 'w')
                file.write(originalText)
                file.close()
                detail = ' (original was restored)'
            except Exception:
                detail = ''

            xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Error while writing to file' + detail, xbmcgui.NOTIFICATION_WARNING, 3000, True)
            return

        if 'watchnixtoons2' in xbmc.getInfoLabel('Container.PluginName'):
            xbmc.executebuiltin('Dialog.Close(all)')

        xbmcgui.Dialog().ok(PLUGIN_TITLE, 'One or more items updated succesfully. Kodi will now reload the Favourites file...')
        xbmc.executebuiltin('LoadProfile(%s)' % xbmc.getInfoLabel('System.ProfileName')) # Reloads 'favourites.xml'.
    else:
        xbmcgui.Dialog().ok(PLUGIN_TITLE, 'Finished. No old favorites found.')


def actionShowSettings(params):

    # Modal dialog, so the program won't continue from this point until user closes\confirms it.
    ADDON.openSettings()

    # So right after it is a good time to update any settings globals.
    global ADDON_SHOW_CATALOG
    ADDON_SHOW_CATALOG = ADDON.getSetting('showCatalog') == 'true'

    global ADDON_LATEST_DATE
    # Set the catalog to be reloaded in case the user changed the "Order 'Latest Releases' By Date" setting.
    newLatestDate = ADDON.getSetting('useLatestDate') == 'true'
    if ADDON_LATEST_DATE != newLatestDate and URL_PATHS['latest'] in getRawWindowProperty(PROPERTY_CATALOG_PATH):
        setRawWindowProperty(PROPERTY_CATALOG_PATH, '')
    ADDON_LATEST_DATE = newLatestDate

    global ADDON_LATEST_THUMBS
    ADDON_LATEST_THUMBS = ADDON.getSetting('showLatestThumbs') == 'true'


def getPageMetadata(html):
    # If we're on an episode or (old) movie page, see if there's a parent page with the actual metadata.
    stringStartIndex = html.find('"header-tag"')
    if stringStartIndex != -1:
        parentURL = re.search('href="([^"]+)', html[stringStartIndex:]).group(1)
        if '/anime/movies' not in parentURL:
            r = requestHelper(parentURL if parentURL.startswith('http') else BASEURL + parentURL)
            if r.ok:
                html = r.text

    # Thumbnail scraping.
    thumb = ''
    stringStartIndex = html.find('og:image" content="')
    if stringStartIndex != -1:
        # 19 = len('og:image" content="')
        thumbPath = html[stringStartIndex+19 : html.find('"', stringStartIndex+19)]
        if thumbPath:
            if thumbPath.startswith('http'):
                thumb = thumbPath + getThumbnailHeaders()
            elif thumbPath.startswith('/'):
                thumb = BASEURL + thumbPath + getThumbnailHeaders()

    if thumb:
        # animationexplore seems more reliable
        # since it now seems to be the default on the site this can be removed in the future
        thumb = thumb.replace( BASEURL + '/wp-content', IMAGES_URL )

    # (Show) plot scraping.
    plot = ''
    stringStartIndex = html.find('Info:')
    if stringStartIndex != -1:
        match = re.search('</h3>\s*<p>(.*?)</p>', html[stringStartIndex:], re.DOTALL)
        plot = unescapeHTMLText(match.group(1).strip()) if match else ''

    return plot, thumb


def actionShowInfo(params):
    xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Requesting info...', ADDON_ICON, 2000, False)

    # Get the desktop page for the item, whatever it is.
    url = params['url'].replace('/m.', '/www.', 1) # Make sure the URL points to the desktop site.
    r = requestHelper(url if url.startswith('http') else BASEURL + url)
    html = r.text

    plot, thumb = getPageMetadata(html)

    # Use a persistent memory property holding a dictionary, and refresh the directory listing.
    if plot or thumb:
        infoItems = getWindowProperty(PROPERTY_INFO_ITEMS) or { }
        infoItems[url] = (plot, (thumb or 'DefaultVideo.png'))
        setWindowProperty(PROPERTY_INFO_ITEMS, infoItems)
        xbmc.executebuiltin('Container.Update(%s,replace)' % (PLUGIN_URL + '?' + params['oldParams']))
    else:
        xbmcgui.Dialog().notification(PLUGIN_TITLE, 'No info found', ADDON_ICON, 1500, False)


def getTitleInfo(unescapedTitle):
    # We need to interpret the full title of each episode's link's string
    # for information like episode number, season and show title.
    season = None
    episode = None
    multiPart = None
    showTitle = unescapedTitle
    episodeTitle = ''

    seasonIndex = unescapedTitle.find('Season ') # 7 characters long.
    if seasonIndex != -1:
        season = unescapedTitle[seasonIndex+7 : unescapedTitle.find(' ', seasonIndex+7)]
        if not season.isdigit():
            # Handle inconsistently formatted episode title, with possibly ordinal season before or after
            # the word "Season" (case unknown, inconsistent).
            if season == 'Episode':
                # Find the word to the left of "Season ", separated by spaces (spaces not included in the result).
                season = unescapedTitle[unescapedTitle.rfind(' ', 0, seasonIndex-1) + 1 : seasonIndex-1]
                showTitle = unescapedTitle[:seasonIndex+7].strip(' -–:') # Include the "nth Season" term in the title.
            else:
                showTitle = unescapedTitle[:seasonIndex].strip(' -–:')
            season = {'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5'}.get(season.lower(), '')
        else:
            showTitle = unescapedTitle[:seasonIndex].strip(' -–:')

    episodeIndex = unescapedTitle.find(' Episode ') # 9 characters long.
    if episodeIndex != -1:
        spaceIndex = unescapedTitle.find(' ', episodeIndex+9)
        if spaceIndex > episodeIndex:
            episodeSplit = unescapedTitle[episodeIndex+9 : spaceIndex].split('-') # For multipart episodes, like "42-43".
            episode = filter(str.isdigit, episodeSplit[0])
            multiPart = filter(str.isdigit, episodeSplit[1]) if len(episodeSplit) > 1 else None

            # Get the episode title string (stripped of spaces, hyphens and en-dashes).
            englishIndex = unescapedTitle.rfind(' English', spaceIndex)
            if englishIndex != -1:
                episodeTitle = unescapedTitle[spaceIndex+1 : englishIndex].strip(' -–:')
            else:
                episodeTitle = unescapedTitle[spaceIndex+1:].strip(' -–:')
            # Safeguard for when season 1 is ocasionally omitted in the title.
            if not season:
                season = '1'

    if episode:
        return (showTitle[:episodeIndex].strip(' -'), season, episode, multiPart, episodeTitle.strip(' /'))
    else:
        englishIndex = unescapedTitle.rfind(' English')
        if englishIndex != -1:
            return (unescapedTitle[:englishIndex].strip(' -'), None, None, None, '')
        else:
            return (unescapedTitle.strip(' -'), None, None, None, '')


def makeListItem(title, url, artDict, plot, isFolder, isSpecial, oldParams, isRecent=False):

    unescapedTitle = unescapeHTMLText(title)
    plot = unescapeHTMLText(plot)
    item = xbmcgui.ListItem(unescapedTitle)
    isPlayable = False

    if not (isFolder or isSpecial):
        title, season, episode, multiPart, episodeTitle = getTitleInfo(unescapedTitle)
        # Playable content.
        isPlayable = True
        itemInfo = {
            'mediatype': 'episode' if episode else 'tvshow',
            'tvshowtitle': title,
            'title': episodeTitle,
            'plot': plot
        }

        if six.PY3:
            episode = str(episode)

        if episode and episode.isdigit():
            itemInfo['season'] = int(season) if season.isdigit() else -1
            itemInfo['episode'] = int(episode)

        item_set_info( item, itemInfo )

    elif isSpecial:
        isPlayable = True
        item_set_info( item, {'mediatype': 'movie', 'title': unescapedTitle, 'plot': plot} )
    else:
        item_set_info( item, {'mediatype': 'tvshow', 'title': unescapedTitle, 'plot': plot} )

    if artDict:
        item.setArt(artDict)

    # Add the context menu items, if necessary.
    context_menu_list = []
    if oldParams:
        context_menu_list.append(
            (
                'Nixtoons Information',
                'RunPlugin('+PLUGIN_URL+'?action=actionShowInfo&url='+urllib_parse.quote_plus(url)+'&oldParams='+urllib_parse.quote_plus(urllib_parse.urlencode(oldParams))+')'
            )
        )
    if isPlayable:
        # Allows the checkmark to be placed on watched episodes.
        item.setProperty('IsPlayable', 'true')
        # add content menu to play chapters
        context_menu_list.append(
            (
                'Play Chapters',
                'PlayMedia('+PLUGIN_URL+'?action=actionResolve&url='+urllib_parse.quote_plus(url)+'&playChapters=1)'
            )
        )
    if isRecent:
        # So item can be removed
        context_menu_list.append(
            (
                'Remove',
                'PlayMedia('+PLUGIN_URL+'?action=actionRecentlyWatchedRemove&url='+urllib_parse.quote_plus(url)+')'
            )
        )

    if context_menu_list:
        item.addContextMenuItems(context_menu_list)

    return item


# Variant of the 'makeListItem()' function
# tries to format the item label using the season and episode.
def makeListItemClean(title, url, artDict, plot, isFolder, isSpecial, oldParams):

    unescapedTitle = unescapeHTMLText(title)
    plot = unescapeHTMLText(plot)
    isPlayable = False

    if isFolder or isSpecial:
        item = xbmcgui.ListItem(unescapedTitle)
        if isSpecial:
            isPlayable = True
            item_set_info( item, {'mediatype': 'video', 'title': unescapedTitle} )
    else:
        title, season, episode, multiPart, episodeTitle = getTitleInfo(unescapedTitle)

        # dirty way to ensure is a string
        # this is due to filters being used, todo for clean-up
        if six.PY3:
            if episode:
                episode = "".join(episode)
            if season:
                season = "".join(season)
            if multiPart:
                multiPart = "".join(multiPart)

        if episode and episode.isdigit():
            # The clean episode label will have this format: "SxEE Episode Name", with S and EE standing for digits.
            item = xbmcgui.ListItem(
                '[B]' + season + 'x' + episode.zfill(2) + ('-' + multiPart if multiPart else '') + '[/B] '
                + (episodeTitle or title)
            )
            itemInfo = {
                'mediatype': 'episode',
                'tvshowtitle': title,
                'title': title,
                'plot': plot,
                'season': int(season) if season.isdigit() else -1,
                'episode': int(episode)
            }
        else:
            item = xbmcgui.ListItem(title)
            itemInfo = {
                'mediatype': 'tvshow',
                'tvshowtitle': title,
                'title': title,
                'plot': plot
            }
        item_set_info( item, itemInfo )
        isPlayable = True

    if artDict:
        item.setArt(artDict)

    # Add the context menu items, if necessary.
    context_menu_list = []
    if oldParams:
        context_menu_list.append(
            (
                'Show Information',
                'RunPlugin('+PLUGIN_URL+'?action=actionShowInfo&url='+urllib_parse.quote_plus(url)+'&oldParams='+urllib_parse.quote_plus(urllib_parse.urlencode(oldParams))+')'
            )
        )
    if isPlayable:
        # Allows the checkmark to be placed on watched episodes.
        item.setProperty('IsPlayable', 'true')
        # add content menu to play chapters
        context_menu_list.append(
            (
                'Play Chapters',
                'PlayMedia('+PLUGIN_URL+'?action=actionResolve&url='+urllib_parse.quote_plus(url)+'&playChapters=1)'
            )
        )

    if context_menu_list:
        item.addContextMenuItems(context_menu_list)

    return item


# Manually sorts items from an iterable into an alphabetised catalog.
# Iterable contains (URL, name) pairs that might refer to a series, episode, ova or movie.
def catalogFromIterable(iterable):
    catalog = {key: [ ] for key in ascii_uppercase}
    miscSection = catalog['#'] = [ ]
    for item in iterable:
        key = item[1][0].upper()
        if key in catalog:
            catalog[key].append(item)
        else:
            miscSection.append(item)
    return catalog


def makeLatestCatalog(params):

    # Returns a list of links from the "Latest 50 Releases" area
    r = requestHelper(BASEURL + '/last-50-recent-release')
    html = r.text

    dataStartIndex = html.find('fourteen columns')
    if dataStartIndex == -1:
        raise Exception('Latest catalog scrape fail')

    #latest now using external site
    #thumbHeaders = getThumbnailHeaders()

    if ADDON_LATEST_DATE:
        # Make the catalog dict only have a single section, "LATEST", with items listed as they are.
        # This way the actionCatalogMenu() function will show this single section directly, with no alphabet categories.
        return {
            'LATEST': tuple(
                (match.group(1), match.group(3), "https:" + match.group(2))
                for match in re.finditer(
                    r'''<div class=\"img\">\s+?<a href=\"([^\"]+)\">\s+?<img class=\"hover-img1\" src=\"([^\"]+)\">\s+?</a>\s+?</div>\s+?<div class=\"recent-release-episodes\"><a href=\".*?\" rel=\"bookmark\">(.*?)</a''', html[dataStartIndex : html.find('</ul>', dataStartIndex)]
                )
            )
        }
    else:
        return catalogFromIterable(
            (match.group(1), match.group(3), "https:" + match.group(2))
            for match in re.finditer(
                r'''<div class=\"img\">\s+?<a href=\"([^\"]+)\">\s+?<img class=\"hover-img1\" src=\"([^\"]+)\">\s+?</a>\s+?</div>\s+?<div class=\"recent-release-episodes\"><a href=\".*?\" rel=\"bookmark\">(.*?)</a''', html[dataStartIndex : html.find('</ul>', dataStartIndex)]
            )
        )


def makePopularCatalog(params):
    # Scrape from the sidebar content on the homepage to get popular list
    r = requestHelper(BASEURL)
    html = r.text

    dataStartIndex = html.find('"sidebar-titles"')
    if dataStartIndex == -1:
        raise Exception('Popular catalog scrape fail: ' + params['path'])

    return catalogFromIterable(
        match.groups()
        for match in re.finditer(
            '''<a href="([^"]+).*?>([^<]+)''', html[dataStartIndex : html.find('</div>', dataStartIndex)]
        )
    )


def makeSeriesSearchCatalog(params):
    r = requestHelper(
        BASEURL+'/search',
        data={'catara': params['query'], 'konuara': 'series'},
        extraHeaders={'Referer': BASEURL+'/'}
    )
    html = r.text

    dataStartIndex = html.find('submit')
    if dataStartIndex == -1:
        raise Exception('Series search scrape fail: ' + params['query'])

    return catalogFromIterable(
        match.groups()
        for match in re.finditer(
            '''<a href="([^"]+)[^>]*>([^<]+)</a''',
            html[dataStartIndex : html.find('cizgiyazisi', dataStartIndex)]
        )
    )


def makeMoviesSearchCatalog(params):
    # Try a movie category search (same code as in 'makeGenericCatalog()').
    r = requestHelper(BASEURL + URL_PATHS['movies'])
    html = r.text

    dataStartIndex = html.find('"ddmcc"')
    if dataStartIndex == -1:
        raise Exception('Movies search scrape fail: ' + params['query'])

    lowerQuery = params['query'].lower()

    return catalogFromIterable(
        match.groups()
        for match in re.finditer(
            '''<a href="([^"]+).*?>([^<]+)''', html[dataStartIndex : html.find('/ul></ul', dataStartIndex)]
        )
        if lowerQuery in match.group(2).lower()
    )


def makeEpisodesSearchCatalog(params):
    r = requestHelper(
        BASEURL+'/search',
        data={'catara': params['query'], 'konuara': 'episodes'},
        extraHeaders={'Referer': BASEURL+'/'}
    )
    html = r.text

    dataStartIndex = html.find('submit')
    if dataStartIndex == -1:
        raise Exception('Episode search scrape fail: ' + params['query'])

    return catalogFromIterable(
        match.groups()
        for match in re.finditer(
            '''<a href="([^"]+)[^>]*>([^<]+)</a''',
            html[dataStartIndex : html.find('cizgiyazisi', dataStartIndex)],
            re.DOTALL
        )
    )


def makeSearchCatalog(params):
    search_type = params.get('searchType', 'series')
    if search_type == 'series':
        return makeSeriesSearchCatalog(params)
    if search_type == 'movies':
        return makeMoviesSearchCatalog(params)
    return makeEpisodesSearchCatalog(params)


def makeGenericCatalog(params):

    # (full website) in here.
    r = requestHelper(BASEURL + params['path'])
    html = r.text

    dataStartIndex = html.find('"ddmcc"')
    if dataStartIndex == -1:
        raise Exception('Generic catalog scrape fail: ' + params['path'])

    return catalogFromIterable(
        match.groups()
        for match in re.finditer(
            '''<li(?:\sdata\-id=\"[0-9]+\")?>\s*<a href="([^"]+).*?>([^<]+)''', html[dataStartIndex : html.find('<script>', dataStartIndex)]
        )
    )


# Retrieves the catalog from a persistent XBMC window property between different add-on
# directories, or recreates the catalog based on one of the catalog functions.
def getCatalogProperty(params):
    path = params['path']

    def _rebuildCatalog():
        func = CATALOG_FUNCS.get(path, makeGenericCatalog)
        catalog = func(params)
        setWindowProperty(PROPERTY_CATALOG, catalog)
        if 'query' in params:
            # For searches, store the query and search type in the catalog path so we can identify
            # this particular search attempt.
            setRawWindowProperty(PROPERTY_CATALOG_PATH, path + params['query'] + params['searchType'])
        else:
            setRawWindowProperty(PROPERTY_CATALOG_PATH, path)
        setRawWindowProperty(PROPERTY_INFO_ITEMS, '') # Clear any previous info.
        return catalog

    # If these properties are empty (like when coming in from a favourites menu), or if
    # a different catalog (a different URL path) is stored in this property, then reload it.
    currentPath = getRawWindowProperty(PROPERTY_CATALOG_PATH)
    if (
        # "If we're coming in from a search and the search query and type are different, or if we're not
        # coming in from a search and the paths are simply different, rebuild the catalog."
        ('query' in params and (params['query'] not in currentPath or params['searchType'] not in currentPath))
        or ('query' not in params and currentPath != path)
    ):
        catalog = _rebuildCatalog()
    else:
        catalog = getWindowProperty(PROPERTY_CATALOG)
        if not catalog:
            catalog = _rebuildCatalog()
    return catalog

def get_page_parent(html):
    stringStartIndex = html.find('"header-tag"')
    match = re.search('<h2><a href=\"([^\"]+)\"(?:[^\>]+)>([^/<]+)</a>', html[stringStartIndex:], re.DOTALL)
    url = match.group(1).strip() if match else ''
    name = unescapeHTMLText(match.group(2).strip()) if match else ''

    return { 'name': name, 'url': url }

def actionResolve(params):
    # Needs to be the BASEURL domain to get multiple video qualities.
    url = params['url']
    # Sanitize the URL since on some occasions it's a path instead of full address.
    url = url if url.startswith('http') else (BASEURL + (url if url.startswith('/') else '/' + url))
    r = requestHelper(url.replace('wcofun.com', 'wcofun.org', 1)) # New domain safety replace.
    content = r.content

    if six.PY3:
        content = content.decode('utf-8')

    # get data & mark as recently watched
    parent = get_page_parent( content )
    recently_watched_add( parent['name'], parent['url'] )

    def _decodeSource(subContent):
        if six.PY3:
            subContent = str(subContent)

        try:
            chars = subContent[subContent.find('[') : subContent.find(']')]
            spread = int(re.search(r' - (\d+)\)\; }', subContent[subContent.find(' - '):]).group(1))
            xbmc.log( chars, level=xbmc.LOGINFO )
            xbmc.log( str(spread), level=xbmc.LOGINFO )
            iframe = ''.join(
                chr(
                    int(''.join(c for c in str(b64decode(char)) if c.isdigit())) - spread
                )
                for char in chars.replace('"', '').split(',')
            )
        except Exception:
            # quick dirty fix
            iframe = subContent
        try:
            returnUrl = re.search(r'src="([^"]+)', iframe).group(1)
            if not returnUrl.startswith('\\') and not returnUrl.startswith('http'):
                returnUrl = BASEURL + returnUrl
            return returnUrl
        except:
            return None # Probably a temporary block, or change in embedded code.

    embedURL = None

    # On rare cases an episode might have several "chapters", which are video players on the page.
    embedURLPattern = r'onclick="myFunction'
    embedURLIndex = content.find(embedURLPattern)
    if 'playChapters' in params or ADDON.getSetting('chapterEpisodes') == 'true':
        # Multi-chapter episode found (that is, multiple embedURLPattern statements found).
        # Extract all chapters from the page.
        embedURLPatternLen = len(embedURLPattern)
        currentPlayerIndex = embedURLIndex
        dataIndices = []
        while currentPlayerIndex != -1:
            dataIndices.append(currentPlayerIndex)
            currentPlayerIndex = content.find(embedURLPattern, currentPlayerIndex + embedURLPatternLen)

        # If more than one "embedURL" statement found
        # make a selection dialog and call them "chapters".
        if len(dataIndices) > 1:
            selectedIndex = xbmcgui.Dialog().select('Select Chapter', ['Chapter '+str(n) for n in range(1, len(dataIndices)+1)])
        else:
            selectedIndex = 0

        if selectedIndex != -1:
            embedURL = _decodeSource(content[dataIndices[selectedIndex]:])
        else:
            # User cancelled the chapter selection.
            return
    else:
        # back-up search index
        if embedURLIndex <= 0:
            embedURLPattern = r'class="episode-descp"'
            embedURLIndex = content.find(embedURLPattern)
        # Normal / single-chapter episode.
        embedURL = _decodeSource(content[embedURLIndex:])
        # User asked to play multiple chapters, but only one chapter/video player found.
        if embedURL and 'playChapters' in params:
            xbmcgui.Dialog().notification(PLUGIN_TITLE, 'Only 1 chapter found...', ADDON_ICON, 2000, False)

    # Notify a failure in solving the player obfuscation.
    if not embedURL:
        xbmcgui.Dialog().ok(PLUGIN_TITLE, 'Unable to find a playable source')
        return

    # Request the embedded player page.
    r2 = requestHelper(
        unescapeHTMLText(embedURL), # Sometimes a '&#038;' symbol is present in this URL.
            data = None,
            extraHeaders = {
                'User-Agent': WNT2_USER_AGENT, 'Accept': '*/*', 'Referer': embedURL, 'X-Requested-With': 'XMLHttpRequest'
            }
    )
    html = r2.text

    # Notify about temporary blocks / failures.
    if 'high volume of requests' in html:
        xbmcgui.Dialog().ok(
            PLUGIN_TITLE + ' Fail (Server Response)',
            '"We are getting extremely high volume of requests on our video servers so that we temporarily block for free videos for free users. I apologize for the inconvenience."'
        )
        return

    # Find the stream URLs.
    if 'getvid?evid' in html:

        # Query-style stream getting.
        sourceURL = re.search(r'"(/inc/embed/getvidlink[^"]+)', html, re.DOTALL).group(1)

        # Inline code similar to 'requestHelper()'.
        # The User-Agent for this next request is somehow encoded into the media tokens, so we make sure to use
        # the EXACT SAME value later, when playing the media, or else we get a HTTP 404 / 500 error.
        r3 = requestHelper(
            BASEURL + sourceURL,
            data = None,
            extraHeaders = {
                'User-Agent': WNT2_USER_AGENT, 'Accept': '*/*',
                'Referer': embedURL,
                'X-Requested-With': 'XMLHttpRequest'
            }
        )
        if not r3.ok:
            raise Exception('Sources XMLHttpRequest request failed')
        jsonData = r3.json()

        # Only two qualities are ever available: 480p ("SD") and 720p ("HD").
        sourceURLs = [ ]
        sdToken = jsonData.get('enc', '')
        hdToken = jsonData.get('hd', '')
        sourceBaseURL = jsonData.get('server', '') + '/getvid?evid='
        if sdToken:
            # Order the items as (LABEL, URL).
            sourceURLs.append(('480 (SD)', sourceBaseURL + sdToken))
        if hdToken:
            sourceURLs.append(('720 (HD)', sourceBaseURL + hdToken))
        # Use the same backup stream method as the source: cdn domain + SD stream.
        backupURL = jsonData.get('cdn', '') + '/getvid?evid=' + (sdToken or hdToken)
    else:
        # Alternative video player page, with plain stream links in the JWPlayer javascript.
        sourcesBlock = re.search('sources:\s*?\[(.*?)\]', html, re.DOTALL).group(1)
        streamPattern = re.compile('\{\s*?file:\s*?"(.*?)"(?:,\s*?label:\s*?"(.*?)")?')
        sourceURLs = [
            # Order the items as (LABEL (or empty string), URL).
            (sourceMatch.group(2), sourceMatch.group(1))
            for sourceMatch in streamPattern.finditer(sourcesBlock)
        ]
        # Use the backup link in the 'onError' handler of the 'jw' player.
        backupMatch = streamPattern.search(html[html.find(b'jw.onError'):])
        backupURL = backupMatch.group(1) if backupMatch else ''

    mediaURL = None
    if len(sourceURLs) == 1: # Only one quality available.
        mediaURL = sourceURLs[0][1]
    elif len(sourceURLs) > 0:
        # Always force "select quality" for now.
        playbackMethod = ADDON.getSetting('playbackMethod')
        if playbackMethod == '0': # Select quality.
            selectedIndex = xbmcgui.Dialog().select(
                'Select Quality', [(sourceItem[0] or '?') for sourceItem in sourceURLs]
            )
            if selectedIndex != -1:
                mediaURL = sourceURLs[selectedIndex][1]
        else: # Auto-play user choice.
            sortedSources = sorted(sourceURLs)
            mediaURL = sortedSources[-1][1] if playbackMethod == '1' else sortedSources[0][1]

    if mediaURL:
        # Kodi headers for playing web streamed media.
        global MEDIA_HEADERS
        if not MEDIA_HEADERS:
            MEDIA_HEADERS = {
                'User-Agent': WNT2_USER_AGENT,
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                #'Connection': 'keep-alive', # The source website uses HTTP/1.1, where this value is the default.
                'Referer': BASEURL + '/'
            }

        # Try to un-redirect the chosen media URL.
        # If it fails, try to un-resolve the backup URL.
        # If not even the backup URL is working, abort playing.
        mediaHead = solveMediaRedirect(mediaURL, MEDIA_HEADERS)
        if not mediaHead:
            mediaHead = solveMediaRedirect(backupURL, MEDIA_HEADERS)
        if not mediaHead:
            return xbmcplugin.setResolvedUrl(PLUGIN_ID, False, xbmcgui.ListItem())

        # Enforce the add-on debug setting to use HTTP access on the stream.
        if ADDON.getSetting('useHTTP') == 'true':
            # This is now being used for the fact that sometimes the SSL certificate is sometimes not renewed on the media servers
            streamURL = mediaHead.url.replace('https://', 'http://', 1)
        else:
            streamURL = mediaHead.url

        # Need to use the exact same ListItem name & infolabels when playing or else Kodi replaces that item
        # in the UI listing.
        item = xbmcgui.ListItem(xbmc.getInfoLabel('ListItem.Label'))
        item.setPath(streamURL + '|' + '&'.join(key+'='+urllib_parse.quote_plus(val) for key, val in MEDIA_HEADERS.items()))

        # Disable Kodi's MIME-type request, since we already know what it is.
        item.setMimeType(mediaHead.headers.get('Content-Type', 'video/mp4'))
        item.setContentLookup(False)

        # When coming in from a Favourite item, there will be no metadata. Try to get at least a title.
        itemTitle = xbmc.getInfoLabel('ListItem.Title')
        if not itemTitle:
            match = re.search(r'<h1[^>]+>([^<]+)</h1', content)
            if match:
                if six.PY3:
                    itemTitle = str(match.group(1)).replace(' English Subbed', '', 1).replace( 'English Dubbed', '', 1)
                else:
                    itemTitle = match.group(1).replace(' English Subbed', '', 1).replace( 'English Dubbed', '', 1)
            else:
                itemTitle = ''

        episodeString = xbmc.getInfoLabel('ListItem.Episode')
        if episodeString != '' and episodeString != '-1':
            seasonInfoLabel = xbmc.getInfoLabel('ListItem.Season')
            item_set_info( item,
                {
                    'tvshowtitle': xbmc.getInfoLabel('ListItem.TVShowTitle'),
                    'title': unescapeHTMLText(itemTitle),
                    'season': int(seasonInfoLabel) if seasonInfoLabel.isdigit() else -1,
                    'episode': int(episodeString),
                    'plot': xbmc.getInfoLabel('ListItem.Plot'),
                    'mediatype': 'episode'
                }
            )
        else:
            item_set_info( item,
                {
                    'title': unescapeHTMLText(itemTitle),
                    'plot': xbmc.getInfoLabel('ListItem.Plot'),
                    'mediatype': 'movie'
                }
            )

        #xbmc.Player().play(listitem=item) # Alternative play method, lets you extend the Player class with your own.
        xbmcplugin.setResolvedUrl(PLUGIN_ID, True, item)
    else:
        # Failed. No source found, or the user didn't select one from the dialog.
        xbmcplugin.setResolvedUrl(PLUGIN_ID, False, xbmcgui.ListItem())


# Helper function to build a Kodi xbmcgui.ListItem URL.
# :param query: Dictionary of url parameters to put in the URL.
# :returns: A formatted and urlencoded URL string.
def buildURL(query):
    return PLUGIN_URL + '?' + \
        urllib_parse.urlencode({k: v.encode('utf-8') if isinstance(v, six.text_type)
            else unicode(v, errors='ignore').encode('utf-8')
            for k, v in query.items()})


# Thumbnail HTTP headers for Kodi to use when grabbing thumbnail images.
def getThumbnailHeaders():
    # Original code:
    #return (
    #    '|User-Agent='+urllib_parse.quote_plus(WNT2_USER_AGENT)
    #    + '&Accept='+urllib_parse.quote_plus('image/webp,*/*')
    #    + '&Referer='+urllib_parse.quote_plus(BASEURL+'/')
    #)
    cookieProperty = getRawWindowProperty(PROPERTY_SESSION_COOKIE)
    cookies = ('&Cookie=' + urllib_parse.quote_plus(cookieProperty)) if cookieProperty else ''

    # Since it's a constant value, it can be precomputed.
    return '|User-Agent=' + urllib_parse.quote_plus(WNT2_USER_AGENT) + \
        '&Accept=image%2Fwebp%2C%2A%2F%2A&Referer=' + urllib_parse.quote_plus(BASEURL+'/') + cookies


def getOldDomains():
    # Old possible domains, in the order of likeliness.
    return (
        'www.wcofun.com',
        'www.wcofun.net',
        'www.wcostream.com',
        'm.wcostream.com',
        'www.watchcartoononline.io',
        'm.watchcartoononline.io',
        'www.thewatchcartoononline.tv'
    )


def solveMediaRedirect(url, headers):
    # Use (streamed, headers-only) GET requests to fulfill possible 3xx redirections.
    # Returns the (headers-only) final response, or None.
    while True:
        try:
            mediaHead = s.get(
                url, stream=True, headers=headers, allow_redirects=False, verify=False, timeout=10
            )
            if 'Location' in mediaHead.headers:
                url = mediaHead.headers['Location'] # Change the URL to the redirected location.
            else:
                mediaHead.raise_for_status()
                return mediaHead # Return the response.
        except:
            return None # Return nothing on failure.


def requestHelper(url, data=None, extraHeaders=None):
    myHeaders = {
        'User-Agent': WNT2_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml,application/json;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'DNT': '1'
    }
    if extraHeaders:
        myHeaders.update(extraHeaders)

    # At the moment it's a single response cookie, "__cfduid". Other cookies are set w/ Javascript by ads.
    cookieProperty = getRawWindowProperty(PROPERTY_SESSION_COOKIE)
    if cookieProperty:
        cookieDict = dict(pair.split('=') for pair in cookieProperty.split('; '))
    else:
        cookieDict = None

    start_time = time()

    status = 0
    i = 0
    while status != 200 and i < 2:
        if data:
            response = s.post(url, data=data, headers=myHeaders, verify=False, cookies=cookieDict, timeout=10)
        else:
            response = s.get(url, headers=myHeaders, verify=False, cookies=cookieDict, timeout=10)

        status = response.status_code
        if status != 200:
            if status == 403 and response.headers.get('server', '') == 'cloudflare':
                s.mount(BASEURL, tls_adapters[i])
            i += 1

    # Store the session cookie(s), if any.
    if not cookieProperty and response.cookies:
        setRawWindowProperty(
            PROPERTY_SESSION_COOKIE, '; '.join(pair[0]+'='+pair[1] for pair in response.cookies.get_dict().items())
        )

    elapsed = time() - start_time
    if elapsed < 1.5:
        sleep(1.5 - elapsed)

    return response

def toggleLanguageInvoker(params):
    toggle_reuselanguageinvoker()

# Defined after all the functions exist.
CATALOG_FUNCS = {
    URL_PATHS['latest']: makeLatestCatalog,
    URL_PATHS['popular']: makePopularCatalog,
    URL_PATHS['search']: makeSearchCatalog
}


# Main add-on routing function, calls a certain action (function).
def main():
    # The 'action' parameter is the direct name of the function.
    params = dict(urllib_parse.parse_qsl(sys.argv[2][1:], keep_blank_values=True))
    # Defaults to 'actionMenu()'.
    globals()[params.get('action', 'actionMenu')](params)
