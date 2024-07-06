import pickle
import random
import xbmcgui

from resources.lib.ui import control, database


class BaseWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location)

        control.closeBusyDialog()
        self.setProperty('settings.color', 'deepskyblue')

        if actionArgs is None or actionArgs.get('item_type') == 'skip_intro':
            return
        anilist_id = actionArgs.get('anilist_id')
        if anilist_id:
            self.item_information = pickle.loads(database.get_show(actionArgs['anilist_id'])['kodi_meta'])
            show_meta = database.get_show_meta(actionArgs['anilist_id'])
            if show_meta:
                self.item_information.update(pickle.loads(show_meta.get('art')))
        elif actionArgs.get('playnext'):
            self.item_information = actionArgs
        else:
            self.item_information = {}

        thumb = self.item_information.get('thumb')
        if thumb:
            thumb = random.choice(thumb)
            self.setProperty('item.art.thumb', thumb)

        fanart = self.item_information.get('fanart')
        clearlogo = self.item_information.get('clearlogo', control.OTAKU_LOGO2_PATH)

        if not actionArgs.get('playnext') and not fanart:
            fanart = control.OTAKU_FANART

        if fanart is None or control.bools.fanart_disable:
            fanart = control.OTAKU_FANART
        else:
            if isinstance(fanart, list):
                if control.bools.fanart_select:
                    fanart_select = control.getSetting(f'fanart.select.anilist.{anilist_id}')
                    fanart = fanart_select if fanart_select else random.choice(fanart)
                else:
                    fanart = random.choice(fanart)
        if isinstance(clearlogo, list):
            clearlogo = control.OTAKU_LOGO2_PATH if control.bools.clearlogo_disable else random.choice(clearlogo)

        self.setProperty('item.art.poster', self.item_information.get('poster'))
        self.setProperty('item.art.fanart', fanart)
        self.setProperty('item.art.clearlogo', clearlogo)
        self.setProperty('item.art.logo', clearlogo)
        self.setProperty('item.info.title', self.item_information.get('name'))

        if self.item_information.get('format') == 'MOVIE':
            self.setProperty('item.info.plot', self.item_information.get('plot'))
            self.setProperty('item.info.rating', str(self.item_information.get('rating')))
            self.setProperty('item.info.title', self.item_information.get('title_userPreferred'))
