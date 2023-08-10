# -*- coding: utf-8 -*-

import sys

BASEURL = 'https://www.wcofun.org'
IMAGES_URL = 'https://cdn.animationexplore.com'

THUMBS_BASEURL = 'https://doko-desuka.github.io/128h/'

PLUGIN_ID = int(sys.argv[1])
PLUGIN_URL = sys.argv[0]
PLUGIN_NAME = PLUGIN_URL.replace("plugin://","")
PLUGIN_TITLE = 'WatchNixtoons2'
PROPERTY_CATALOG_PATH = 'wnt2.catalogPath'
PROPERTY_CATALOG = 'wnt2.catalog'
PROPERTY_EPISODE_LIST_URL = 'wnt2.listURL'
PROPERTY_EPISODE_LIST_DATA = 'wnt2.listData'
PROPERTY_LATEST_MOVIES = 'wnt2.latestMovies'
PROPERTY_INFO_ITEMS = 'wnt2.infoItems'
PROPERTY_SESSION_COOKIE = 'wnt2.cookie'

# Fake user-agent to get past some cloudflare checks :(
WNT2_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
