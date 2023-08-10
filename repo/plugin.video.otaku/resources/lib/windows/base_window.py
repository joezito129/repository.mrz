import os
import pickle
import random

from resources.lib.ui import control, database


class BaseWindow(control.xmlWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        super(BaseWindow, self).__init__(xml_file, location)

        control.closeBusyDialog()
        self._title_lang = control.title_lang(control.getSetting("titlelanguage"))
        self.setProperty('otaku.logo', control.OTAKU_LOGO_PATH)
        self.setProperty('otaku.fanart', control.OTAKU_FANART_PATH)
        self.setProperty('settings.color', 'deepskyblue')
        self.setProperty('skin.dir', control.ADDON_PATH)

        if actionArgs is None or actionArgs.get('item_type') == 'skip_intro':
            return

        if actionArgs.get('anilist_id'):
            self.item_information = pickle.loads(database.get_show(actionArgs['anilist_id'])['kodi_meta'])
            show_meta = database.get_show_meta(actionArgs['anilist_id'])
            if show_meta:
                self.item_information.update(pickle.loads(show_meta.get('art')))
        elif actionArgs.get('playnext'):
            self.item_information = actionArgs
        else:
            self.item_information = {}

        self.setProperty('item.ids.%s_id' % 1, str('gh'))

        thumb = self.item_information.get('thumb')
        if thumb:
            thumb = random.choice(thumb)
            self.setProperty('item.art.thumb', thumb)

        fanart = self.item_information.get('fanart')
        clearlogo = self.item_information.get('clearlogo', control.OTAKU_LOGO2_PATH)

        if not actionArgs.get('playnext') and not fanart:
            fanart = control.OTAKU_FANART_PATH

        if isinstance(fanart, list):
            fanart = control.OTAKU_FANART_PATH if control.getSetting('scraping.fanart') == 'true' else random.choice(fanart)
        if isinstance(clearlogo, list):
            clearlogo = control.OTAKU_LOGO2_PATH if control.getSetting('scraping.clearlogo') == 'true' else random.choice(clearlogo)

        self.setProperty('item.art.poster', self.item_information.get('poster'))
        self.setProperty('item.art.fanart', fanart)
        self.setProperty('item.art.clearlogo', clearlogo)
        self.setProperty('item.art.logo', clearlogo)
        self.setProperty('item.info.title', self.item_information.get('name'))

        if self.item_information.get('format') == 'MOVIE':
            self.setProperty('item.info.plot', self.item_information.get('plot'))
            self.setProperty('item.info.rating', str(self.item_information.get('rating')))
            if self._title_lang == 'english':
                title = self.item_information.get('ename') or self.item_information.get('title_userPreferred')
            else:
                title = self.item_information.get('name')
            self.setProperty('item.info.title', title)
