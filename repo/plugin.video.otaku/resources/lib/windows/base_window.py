import random
import xbmcgui

from resources.lib.ui import control, database
from resources.packages import msgpack

class BaseWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_file, location, *args, actionArgs=None):
        super().__init__(xml_file, location)

        control.closeBusyDialog()
        if actionArgs is None or (item_type := actionArgs.get('item_type')) == 'skip_intro':
            return

        if mal_id := actionArgs.get('mal_id'):
            show = database.get_show(mal_id)
            if show is not None:
                self.item_information = msgpack.loads(show['kodi_meta'])
                self.item_information.update(msgpack.loads(show['art']))

        elif item_type == 'playing_next':
            self.item_information = actionArgs
        else:
            self.item_information = {}

        if thumb := self.item_information.get('thumb', []):
            thumb = random.choice(thumb)
            self.setProperty('item.art.thumb', thumb)
        fanart = self.item_information.get('fanart')
        clearlogo = self.item_information.get('clearlogo', control.LOGO_SMALL)
        if fanart is None or control.getBool('interface.fanart.disable'):
            fanart = control.FANART
        else:
            if isinstance(fanart, list):
                fanart = random.choice(fanart)
        if isinstance(clearlogo, list):
            clearlogo = control.LOGO_SMALL if control.getBool('interface.clearlogo.disable') else random.choice(clearlogo)

        if item_type != 'playing_next':
            self.setProperty('item.art.fanart', str(fanart))

        self.setProperty('item.art.poster', str(self.item_information.get('poster')))
        self.setProperty('item.art.clearlogo', str(clearlogo))
        self.setProperty('item.info.title', str(self.item_information.get('name')))
