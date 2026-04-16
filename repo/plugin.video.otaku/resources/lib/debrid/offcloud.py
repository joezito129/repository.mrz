import requests
import xbmcgui

from resources.lib.ui import control

class OffCloud:
    def __init__(self):
        self.token = control.getString('offcloud.token')
        self.refresh = control.getString('offcloud.refresh')
        self.connectionsid = control.getString('offcloud.connectsid')
        self.api_url = "https://offcloud.com/api"
        self.email = control.getString('offcloud.username')
        self.password = control.getString('offcloud.password')


    def auth(self):
        self.email = control.input_dialog('Enter Username:')
        self.password = control.input_dialog('Enter Password:', option=xbmcgui.ALPHANUM_HIDE_INPUT)
        params = {
            'username': self.email,
            'password': self.password
        }
        r = requests.get(f'{self.api_url}/login', params=params)
        user_information = r.json()
        if 'error' not in user_information:
            user_information = r.json()
            self.connectionsid = r.cookies.get_dict()['connect.sid']
            self.email = user_information['email']
            control.setString('offcloud.username', self.email)
            control.setString('offcloud.password', self.password)
            # self.userId = user_information['userId']
