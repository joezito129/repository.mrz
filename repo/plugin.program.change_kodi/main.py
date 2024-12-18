import os

from resources.lib.ui import control
from resources.lib.ui.router import route, router_process


MENU_ITEMS = [
    ("XML File Path", "xml_file_exists", False, 'path.png'),
    ("Create XML File", "create_xml", False, 'create.png'),
    ("Delete XML File", 'delete_xml', False, 'delete.png'),
    ("Edit XML File", "edit_xml", False, 'edit.png'),
    ("View XMl File", "read_xml", False, 'read.png'),
    ("Open Settings", "settings", False, 'settings.png')
]


@route('xml_file_exists')
def XML_FILE_EXISTS(payload, params):
    isExist = os.path.exists(control.ADDVANCEDSETTINGS_PATH)
    if isExist:
        control.ok_dialog(control.ADDON_NAME, f"File Directory: \n[COLOR blue][I]{control.ADDVANCEDSETTINGS_PATH[:-29]}\n{control.ADDVANCEDSETTINGS_PATH[-29:]}[/I][/COLOR]")
    else:
        control.ok_dialog(control.ADDON_NAME, "No File Exists")


@route('create_xml')
def CREATE_XML(payload, params):
    if os.path.exists(control.ADDVANCEDSETTINGS_PATH):
        control.ok_dialog(control.ADDON_NAME, "File Already Exists")
    else:
        with open(control.ADDVANCEDSETTINGS_PATH, 'w'):
            pass
        control.ok_dialog(control.ADDON_NAME, "File Created")


@route('delete_xml')
def DELETE_XML(payload, params):
    yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to delete File?")
    if yesno:
        if os.path.exists(control.ADDVANCEDSETTINGS_PATH):
            os.remove(control.ADDVANCEDSETTINGS_PATH)
            control.ok_dialog(control.ADDON_NAME, "File Deleted")
        else:
            control.ok_dialog(control.ADDON_NAME, "No File Exists")


@route('edit_xml')
def EDIT_XML(payload, params):
    yesno = control.yesno_dialog(control.ADDON_NAME, "Are you sure you want to overide Addvancedsettings.xml with new_xml?")

    network_curllowspeedtime = control.setting('network.curllowspeedtime')
    network_curlclienttimeout = control.setting('network.curlclienttimeout')
    network_disablehttp2 = control.setting('network.disablehttp2')
    network_disableipv6 = control.setting('network.disableipv6')

    video_ignoresecondsatstart = control.setting('video.ignoresecondsatstart')
    video_ignorepercentatend = control.setting('video.ignorepercentatend')
    video_playcountminimumpercent = control.setting('video.playcountminimumpercent')

    database_enable = control.setting('database.enable') == "true"
    database_ipaddress = control.setting('database.ipaddress')

    new_xml_with_video_database = f'''<?xml version='1.0' encoding='UTF-8'?>
    <advancedsettings>
        <network>
            <curllowspeedtime>{network_curllowspeedtime}</curllowspeedtime>
            <curlclienttimeout>{network_curlclienttimeout}</curlclienttimeout>
            <disablehttp2>{network_disablehttp2}</disablehttp2>
            <disableipv6>{network_disableipv6}</disableipv6>
        </network>
        <video>
            <ignoresecondsatstart>{video_ignoresecondsatstart}</ignoresecondsatstart>
            <ignorepercentatend>{video_ignorepercentatend}</ignorepercentatend>
            <playcountminimumpercent>{video_playcountminimumpercent}</playcountminimumpercent>
        </video>
        <videodatabase>
            <type>mysql</type>
            <host>{database_ipaddress}</host>
            <port>3306</port>
            <user>kodi</user>
            <pass>kodi</pass>
        </videodatabase>
    </advancedsettings>
        '''

    new_xml_without_video_database = f'''<?xml version='1.0' encoding='UTF-8'?>
    <advancedsettings>
        <network>
            <curllowspeedtime>{network_curllowspeedtime}</curllowspeedtime>
            <curlclienttimeout>{network_curlclienttimeout}</curlclienttimeout>
            <disablehttp2>{network_disablehttp2}</disablehttp2>
            <disableipv6>{network_disableipv6}</disableipv6>
        </network>
        <video>
            <ignoresecondsatstart>{video_ignoresecondsatstart}</ignoresecondsatstart>
            <ignorepercentatend>{video_ignorepercentatend}</ignorepercentatend>
            <playcountminimumpercent>{video_playcountminimumpercent}</playcountminimumpercent>
        </video>
    </advancedsettings>
        '''

    if yesno:
        with open(control.ADDVANCEDSETTINGS_PATH, 'w') as file:
            if database_enable:
                file.write(new_xml_with_video_database)
            else:
                file.write(new_xml_without_video_database)
        control.ok_dialog(control.ADDON_NAME, "AddvencedSettings.xml has been overritten by jz_xml")


@route('read_xml')
def READ_XML(payload, params):
    with open(control.ADDVANCEDSETTINGS_PATH, 'r') as file:
        xml_file = file.read()
    control.textviewr_dialog(control.ADDON_NAME, xml_file)


@route('settings')
def SETTINGS(payload, params):
    control.opensettings()


@route('')
def LIST_MENU(payload, params):
    return control.draw_items([control.allocate_item(name, url, is_dir, img) for name, url, is_dir, img in MENU_ITEMS])


if __name__ == '__main__':
    router_process(control.get_plugin_url(), control.get_plugin_params())