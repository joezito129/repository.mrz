import time
import requests
import json
import os
import xbmc

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


def getchangelog() -> None:
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
            control.execute(f'LoadProfile({control.xbmc.getInfoLabel("system.profilename")})')
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
    control.log(f'### SQLite: {database_sync.version}')
    control.log(f'### Kodi Version: {control.kodi_version}')

    if control.getSetting('otaku.version') != control.ADDON_VERSION:
        reuselang = control.getSetting('reuselanguageinvoker.status')
        toggle_reuselanguageinvoker(reuselang)
        control.setSetting('otaku.version', control.ADDON_VERSION)
        control.log(f"### {reuselang} Re-uselanguageinvoker")


def load_settings():
    bool_settings = [
        "jz.dub", "jz.filler", "general.smart.scroll.enable", "override.meta.api",
        "interface.viewtypes.bool", "interface.cleantitles", "interface.fanart.disable",
        "interface.clearlogo.disable", "context.otaku.findrecommendations", "context.otaku.findrelations",
        "context.otaku.rescrape", "context.otaku.sourceselect", "context.otaku.logout",
        "context.otaku.deletefromdatabase", "context.otaku.watchlist", "context.otaku.markedaswatched",
        "context.otaku.fanartselect", "widget.hide.nextpage", "provider.nyaa", "provider.animetosho", 'provider.hianime',
        "provider.localfiles", "general.autotrynext", "general.terminate.oncloud",
        "smartplay.skipintrodialog", "skipintro.aniskip.enable", "smartplay.playingnextdialog",
        "skipoutro.aniskip.enable", "subtitle.enable", "general.disable265", "show.uncached",
        "uncached.autorun", "divflavors.dubonly", "divflavors.showdub", "contentformat.bool",
        "contentorigin.bool", "search.adult", "real_debrid.enabled", "real_debrid.cloudInspection",
        "alldebrid.enabled", "alldebrid.cloudInspection", "debrid_link.enabled", "premiumize.enabled",
        "premiumize.cloudInspection", "torbox.enabled", "torbox.cloudInspection", "watchlist.update.enabled",
        "watchlist.sync.enabled", "watchlist.episode.data", "mal.enabled", "anilist.enabled",
        "kitsu.enabled", "simkl.enabled", "menu.lastwatched", "airing_anime", "airing_calendar",
        "upcoming_next_season", "top_100_anime", "genres//", "search_history", "tools"
    ]

    int_settings = [
        "jz.dub.api", "titlelanguage", "searchhistory", "interface.perpage.general.anilist",
        "interface.perpage.general.mal", "interface.perpage.watchlist", "interface.check.updates",
        "general.playstyle.movie", "general.playstyle.episode", "general.playlist.size",
        "general.timeout", "skipintro.aniskip.offset", "skipintro.time", "skipintro.delay",
        "skipintro.duration", "skipoutro.aniskip.offset", "playingnext.time", "general.maxResolution",
        "general.minResolution", "general.source", "contentformat.menu", "contentorigin.menu",
        "real_debrid.expiry", "debrid_link.expiry", "torbox.expiry", "watchlist.update.percent",
        "mal.expiry", "mal.sort", "anilist.sort", "kitsu.expiry", "kitsu.sort", "simkl.sort",
        "addon.last_watched", "update.time.30", "update.time.7"
    ]

    str_settings = [
        "download.location", "browser.api", "meta.api", "interface.viewtypes.general",
        "interface.viewtypes.tvshows", "interface.viewtypes.episodes", "interface.icons",
        "watchlist.update.flavor", "reuselanguageinvoker.status",
        "otaku.version", "last_played"
]

    for s_id in bool_settings:
        val = control.ADDON.getSettingBool(s_id)
        control.window.setProperty(f"{control.ADDON_ID}_{s_id}", str(val).lower())

    for s_id in int_settings:
        val = control.ADDON.getSettingInt(s_id)
        control.window.setProperty(f"{control.ADDON_ID}_{s_id}", str(val))

    for s_id in str_settings:
        val = control.ADDON.getSettingString(s_id)
        control.window.setProperty(f"{control.ADDON_ID}_{s_id}", str(val))


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

    def onSettingsChanged(self):
        control.log('Setting Changed Updating Settings Cache')
        load_settings()


if __name__ == "__main__":
    control.log('##################  RUNNING MAINTENANCE  ######################')
    load_settings()
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

    Monitor().waitForAbort()

