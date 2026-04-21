import pyqrcode
import os

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class WatchlistFlavorAuth(BaseWindow):
    def __init__(self, xml_file, location, *, flavor=None):
        super().__init__(xml_file, location)
        self.flavor = flavor
        self.authorized = False

    def onInit(self):
        qr_path = os.path.join(control.dataPath, 'qr_code.png')
        url = f"https://armkai.vercel.app/api/{self.flavor}"
        copy = control.copy2clip(url)
        if copy:
            self.setProperty('copy2clip', control.lang(30022))
        else:
            self.clearProperty('copy2clip')
        qr = pyqrcode.create(url)
        qr.png(qr_path, scale=20)
        self.setProperty('qr_code', qr_path)
        control.closeBusyDialog()

    def doModal(self) -> bool:
        super(WatchlistFlavorAuth, self).doModal()
        return self.authorized

    def onClick(self, controlId):
        self.handle_action(controlId)

    def handle_action(self, actionID):
        if actionID == 1002:
            self.set_settings()
            self.close()
        elif actionID == 1003:
            self.close()

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()

    def set_settings(self):
        if self.flavor == 'anilist':
            username = self.getControl(1000).getText()
            token = self.getControl(1001).getText()
            control.setString('anilist.username', username)
            control.setString('anilist.token', token)
        elif self.flavor == 'mal':
            authvar = self.getControl(1000).getText()
            control.setString('mal.authvar', authvar)
        else:
            raise Exception("No Flavor")
        self.authorized = True
