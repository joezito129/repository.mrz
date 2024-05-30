import time

from resources.lib.ui import control


def refresh_apis():
    rd_token = control.getSetting('rd.auth')
    dl_token = control.getSetting('dl.auth')

    kitsu_token = control.getSetting('kitsu.token')
    mal_token = control.getSetting('mal.token')

    if rd_token != '':
        rd_expiry = int(float(control.getSetting('rd.expiry')))
        if time.time() > (rd_expiry - 1200):
            from resources.lib.debrid import real_debrid
            real_debrid.RealDebrid().refreshToken()

    if dl_token != '':
        dl_expiry = int(control.getSetting('dl.expiry'))
        if time.time() > (dl_expiry - 600):
            from resources.lib.debrid import debrid_link
            debrid_link.DebridLink().refreshToken()

    if kitsu_token != '':
        kitsu_expiry = int(float(control.getSetting('kitsu.expiry')))
        if time.time() > (kitsu_expiry - 600):
            from resources.lib.WatchlistFlavor import Kitsu
            Kitsu.KitsuWLF().refresh_token()

    if mal_token != '':
        mal_expiry = int(float(control.getSetting('mal.expiry')))
        if time.time() > (mal_expiry - 600):
            from resources.lib.WatchlistFlavor import MyAnimeList
            MyAnimeList.MyAnimeListWLF().refresh_token()


def update_mappings_db():
    import time
    import requests
    import os

    control.setSetting('mappingsdb.time', str(int(time.time())))
    url = 'https://github.com/Goldenfreddy0703/Otaku/raw/main/script.otaku.mappings/resources/data/anime_mappings.db'
    r = requests.get(url)
    with open(os.path.join(control.dataPath, 'mappings.db'), 'wb') as file:
        file.write(r.content)


# def sync_watchlist():
#     from resources.lib.WatchlistFlavor import WatchlistFlavor
#     if control.getSetting('sync.watchlist.notify') == 'true':
#         control.notify('Syncing Watchlist')
#
#     # WatchlistFlavor.get_info
#     flavor = WatchlistFlavor.get_update_flavor()
#     if flavor.flavor_name in ['mal', 'simkl', 'kitsu']:
#         status = 'completed'
#     elif flavor.flavor_name == 'anilist':
#         status = 'COMPLETED'
#     else:
#         return
#     data = flavor.get_watchlist_status(status, {})
#     control.print(data)


def run_maintenance():
    # ADD COMMON HOUSEKEEPING ITEMS HERE #

    # Refresh API tokens
    refresh_apis()
    if control.getSetting('mappingsdb.time') == '' or time.time() > int(control.getSetting('mappingsdb.time')) + 2_592_000:
        control.notify('updated mappings.db')
        update_mappings_db()

    # if control.getSetting('sync.watchlist.enable') == 'true':
    #     sync_watchlist()
