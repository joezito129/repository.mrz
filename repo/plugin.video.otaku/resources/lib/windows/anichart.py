import xbmcgui
import time
import default

from resources.lib.windows.base_window import BaseWindow
from resources.lib.ui import control


class Anichart(BaseWindow):
    def __init__(self, xml_file, location, *, calendar=None):
        super().__init__(xml_file, location)
        self.calendar = calendar
        self.display_list = None
        self.item = None
        self.anime_path = ''
        self.last_action_time = 0

    def onInit(self) -> None:
        self.display_list  = self.getControl(1000)
        for c in self.calendar:
            if c:
                menu_item = xbmcgui.ListItem(c['name'], offscreen=True)
                menu_item.setPath(control.addon_url(c['url']))
                control.set_videotags(menu_item, c['info'])
                art = control.handle_set_fanart(c['image'], c['info'])
                menu_item.setArt(art)
                self.display_list.addItem(menu_item)
        self.setFocusId(1000)

    def doModal(self) -> str:
        super().doModal()
        return self.anime_path

    def onDoubleClick(self, controlId) -> None:
        self.handle_action(controlId)

    def onAction(self, action) -> None:
        actionID = action.getId()
        if actionID in [xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_BACKSPACE, xbmcgui.ACTION_PREVIOUS_MENU]:
            self.close()
        elif actionID in [xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_TOUCH_TAP]:
            time_ = time.time()
            if time_ - self.last_action_time < .3:
                self.handle_action(actionID)
            else:
                self.last_action_time = time_

    def handle_action(self, actionID) -> None:
        if self.getFocusId() == 1000:
            self.item = self.display_list.getSelectedItem()
            self.anime_path = self.item.getPath()
            new_payload, new_params = control.get_payload_params(self.anime_path)
            if 'animes/' in new_payload:
                control.progressDialog.create(control.ADDON_NAME, "Loading..")
                try:
                    x = new_payload.split('animes/', 1)[1]
                    default.ANIMES_PAGE(x, new_params)
                finally:
                    control.progressDialog.close()
            elif 'airing_calendar' in new_payload:
                default.AIRING_CALENDAR(new_payload.rsplit('airing_calendar', 0)[0], new_params)
            self.close()
