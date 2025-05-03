import time
import requests
import json
import os

from resources.lib.ui import control, database_sync


def refresh_apis() -> None:
    control.log("### Refreshing API's")
    rd_token = control.getSetting('real_debrid.token')
    dl_token = control.getSetting('debrid_link.token')

    kitsu_token = control.getSetting('kitsu.token')
    mal_token = control.getSetting('mal.token')

    if rd_token != '':
        rd_expiry = control.getInt('real_debrid.expiry')
        if time.time() > (rd_expiry - 600):
            from resources.lib.debrid import real_debrid
            real_debrid.RealDebrid().refreshToken()

    if dl_token != '':
        dl_expiry = control.getInt('debrid_link.expiry')
        if time.time() > (dl_expiry - 600):
            from resources.lib.debrid import debrid_link
            debrid_link.DebridLink().refreshToken()

    if kitsu_token != '':
        kitsu_expiry = control.getInt('kitsu.expiry')
        if time.time() > (kitsu_expiry - 600):
            from resources.lib.WatchlistFlavor import Kitsu
            Kitsu.KitsuWLF().refresh_token()

    if mal_token != '':
        mal_expiry = control.getInt('mal.expiry')
        if time.time() > (mal_expiry - 600):
            from resources.lib.WatchlistFlavor import MyAnimeList
            MyAnimeList.MyAnimeListWLF().refresh_token()


def update_mappings_db() -> None:
    control.log("### Updating Mappings")
    # url = 'https://github.com/Goldenfreddy0703/Otaku/raw/main/script.otaku.mappings/resources/data/anime_mappings.db'
    url = 'https://github.com/Goldenfreddy0703/Otaku-Mappings/raw/main/anime_mappings.db'
    r = requests.get(url)
    with open(os.path.join(control.dataPath, 'mappings.db'), 'wb') as file:
        file.write(r.content)


def sync_watchlist(silent: bool = False) -> None:
    if control.getBool('watchlist.sync.enabled'):
        control.log('### Updating Completed Sync')
        from resources.lib.WatchlistFlavor import WatchlistFlavor

        flavor = WatchlistFlavor.get_update_flavor()
        if flavor:
            if flavor.flavor_name in control.enabled_watchlists():
                flavor.save_completed()
                if not silent:
                    notify_string = f'Completed Sync [B]{flavor.flavor_name.capitalize()}[/B]'
                    control.notify(control.ADDON_NAME, notify_string)
                    return
            else:
                if not silent:
                    control.ok_dialog(control.ADDON_NAME, "No Watchlist Enabled or Not Logged In")
        else:
            if not silent:
                control.ok_dialog(control.ADDON_NAME, "No Watchlist Enabled or Not Logged In")
    else:
        if not silent:
            control.ok_dialog(control.ADDON_NAME, "Watchilst Sync is Disabled")


def update_dub_json() -> None:
    control.log("### Updating Dub json")
    with open(control.maldubFile, 'w') as file:
        r = requests.get('https://raw.githubusercontent.com/MAL-Dubs/MAL-Dubs/main/data/dubInfo.json')
        mal_dub_list = r.json()["dubbed"]
        mal_dub = {str(item): {'dub': True} for item in mal_dub_list}
        json.dump(mal_dub, file)


def getChangeLog() -> None:
    with open(os.path.join(control.ADDON_PATH, 'changelog.txt')) as f:
        changelog_text = f.read()

    heading = '[B]%s -  v%s - ChangeLog[/B]' % (control.ADDON_NAME, control.ADDON_VERSION)
    from resources.lib.windows.textviewer import TextViewerXML
    windows = TextViewerXML('textviewer.xml', control.ADDON_PATH, heading=heading, text=changelog_text)
    windows.run()
    del windows


def toggle_reuselanguageinvoker(forced_state: str = None) -> None:
    def _store_and_reload(output):
        with open(file_path, "w+") as addon_xml_:
            addon_xml_.writelines(output)
        if not forced_state:
            control.ok_dialog(control.ADDON_NAME, 'Language Invoker option has been changed, reloading kodi profile')
            control.execute('LoadProfile({})'.format(control.xbmc.getInfoLabel("system.profilename")))
    file_path = os.path.join(control.ADDON_PATH, "addon.xml")
    with open(file_path) as addon_xml:
        file_lines = addon_xml.readlines()
    for i in range(len(file_lines)):
        line_string = file_lines[i]
        if "reuselanguageinvoker" in file_lines[i]:
            if forced_state == 'Disabled' or ("true" in line_string and forced_state is None):
                file_lines[i] = file_lines[i].replace("true", "false")
                control.setSetting("reuselanguageinvoker.status", "Disabled")
                _store_and_reload(file_lines)
            elif forced_state == 'Enabled' or ("false" in line_string and forced_state is None):
                file_lines[i] = file_lines[i].replace("false", "true")
                control.setSetting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            break


def version_check() -> None:
    control.log(f'### {control.ADDON_ID} {control.ADDON_VERSION}')
    control.log(f'### Platform: {control.sys.platform}')
    control.log(f'### Python: {control.sys.version}')
    control.log(f'### SQLite: {database_sync.sqlite_version}')
    control.log(f'### Kodi Version: {control.kodi_version}')

    if control.getSetting('otaku.version') != control.ADDON_VERSION:
        reuselang = control.getSetting('reuselanguageinvoker.status')
        toggle_reuselanguageinvoker(reuselang)
        control.setSetting('otaku.version', control.ADDON_VERSION)
        control.log(f"### {reuselang} Re-uselanguageinvoker")


if __name__ == "__main__":
    control.log('##################  RUNNING MAINTENANCE  ######################')
    version_check()
    database_sync.SyncDatabase()
    refresh_apis()
    if time.time() > control.getInt('update.time.30') + 2_592_000:   # 30 days
        update_mappings_db()
        control.setInt('update.time.30', int(time.time()))
    if time.time() > control.getInt('update.time.7') + 604_800:   # 7 days
        update_dub_json()
        sync_watchlist(True)
        control.setInt('update.time.7', int(time.time()))
    control.log('##################  MAINTENANCE COMPLETE ######################')
