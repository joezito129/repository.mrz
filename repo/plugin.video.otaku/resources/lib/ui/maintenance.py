import time

from resources.lib.ui import control


def refresh_apis():
    rd_token = control.getSetting('rd.auth')
    dl_token = control.getSetting('dl.auth')

    kitsu_token = control.getSetting('kitsu.token')
    mal_token = control.getSetting('mal.token')

    if rd_token != '':
        rd_expiry = int(control.getSetting('rd.expiry'))
        if time.time() > (rd_expiry - 1200):
            from resources.lib.debrid import real_debrid
            real_debrid.RealDebrid().refreshToken()

    if dl_token != '':
        dl_expiry = int(control.getSetting('dl.expiry'))
        if time.time() > (dl_expiry - 600):
            from resources.lib.debrid import debrid_link
            debrid_link.DebridLink().refreshToken()

    if kitsu_token != '':
        kitsu_expiry = int(control.getSetting('kitsu.expiry'))
        if time.time() > (kitsu_expiry - 600):
            from resources.lib.WatchlistFlavor import Kitsu
            Kitsu.KitsuWLF().refresh_token()

    if mal_token != '':
        mal_expiry = int(control.getSetting('mal.expiry'))
        if time.time() > (mal_expiry - 600):
            from resources.lib.WatchlistFlavor import MyAnimeList
            MyAnimeList.MyAnimeListWLF().refresh_token()


def update_mappings_db():
    import requests
    import os

    control.setSetting('update.time', str(int(time.time())))
    url = 'https://github.com/Goldenfreddy0703/Otaku/raw/main/script.otaku.mappings/resources/data/anime_mappings.db'
    r = requests.get(url)
    with open(os.path.join(control.dataPath, 'mappings.db'), 'wb') as file:
        file.write(r.content)


def sync_watchlist(silent=False):
    if control.getSetting('watchlist.sync.enabled') == 'true':
        from resources.lib.WatchlistFlavor import WatchlistFlavor

        flavor = WatchlistFlavor.get_update_flavor()
        if flavor:
            if flavor.flavor_name in WatchlistFlavor.get_enabled_watchlist_list():
                flavor.save_completed()
                if not silent:
                    notify_string = f'Completed Sync [B]{flavor.flavor_name.capitalize()}[/B]'
                    return control.notify(control.ADDON_NAME, notify_string)
            else:
                if not silent:
                    control.ok_dialog(control.ADDON_NAME, "No Watchlist Enabled or Not Logged In")
        else:
            if not silent:
                control.ok_dialog(control.ADDON_NAME, "No Watchlist Enabled or Not Logged In")
    else:
        if not silent:
            control.ok_dialog(control.ADDON_NAME, "Watchilst Sync is Disabled")


def update_dub_json():
    import requests
    import json

    with open(control.maldubFile, 'w') as file:
        mal_dub_raw = requests.get('https://raw.githubusercontent.com/MAL-Dubs/MAL-Dubs/main/data/dubInfo.json')
        mal_dub_list = mal_dub_raw.json()["dubbed"]
        mal_dub = {str(item): {'dub': True} for item in mal_dub_list}
        json.dump(mal_dub, file)


def run_maintenance():
    # ADD COMMON HOUSEKEEPING ITEMS HERE #

    # Refresh API tokens
    refresh_apis()
    if control.getSetting('update.time') == '' or time.time() > int(control.getSetting('update.time')) + 2_592_000:
        update_mappings_db()
        update_dub_json()
        sync_watchlist(True)
