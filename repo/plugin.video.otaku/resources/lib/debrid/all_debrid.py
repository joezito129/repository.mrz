import requests
import xbmc

from resources.lib.ui import control, source_utils


class AllDebrid:
    def __init__(self):
        self.token = control.getString('alldebrid.token')
        self.agent_identifier = control.ADDON_NAME
        self.base_url = 'https://api.alldebrid.com/v4'
        self.dialog = None

    def auth(self):
        import pyqrcode
        import os
        from resources.lib.windows.progress_dialog import Progress_dialog
        url = f'{self.base_url}/pin/get'
        params = {'agent': self.agent_identifier}
        resp = requests.get(url, params=params).json()['data']
        OauthTotalTimeout = OauthTimeout = int(resp['expires_in'])
        OauthTimeStep = 1

        copied = control.copy2clip(resp['pin'])
        display_dialog = (f"{control.lang(30020).format(control.colorstr(resp['base_url']))}[CR]"
                          f"{control.lang(30021).format(control.colorstr(resp['pin']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"

        qr_path = os.path.join(control.dataPath, 'qr_code.png')
        qr = pyqrcode.create(resp['base_url'])
        qr.png(qr_path, scale=20)
        config = {
            'heading': f'{control.ADDON_NAME}: AllDebrid Auth',
            'text': display_dialog,
            'image': qr_path,
            'percent': 100
        }
        self.dialog = Progress_dialog('progress_dialog.xml', control.ADDON_PATH, config=config)
        self.dialog.show()

        # Seems the All Debrid servers need some time do something with the pin before polling
        # Polling too early will cause an invalid pin error
        xbmc.sleep(5000)

        params = {
            'check': resp['check'],
            'pin': resp['pin'],
            'agent': self.agent_identifier
        }
        auth_done = False
        while not auth_done and OauthTimeout > 0:
            OauthTimeout -= OauthTimeStep
            xbmc.sleep(OauthTimeStep * 1000)
            auth_done, OauthTimeout = self.auth_loop(params, OauthTimeout)
            self.dialog.update(int(OauthTimeout / OauthTotalTimeout * 100))
        self.dialog.close()
        if auth_done:
            self.status()

    def auth_loop(self, params, OauthTimeout) -> tuple:
        if self.dialog.iscanceled():
            OauthTimeout = 0
            return False, OauthTimeout
        url = f'{self.base_url}/pin/check'
        r = requests.get(url, params=params)
        resp = r.json()['data']
        if resp['activated']:
            self.token = resp['apikey']
            control.setString('alldebrid.token', self.token)
            return True, OauthTimeout
        return False, OauthTimeout


    def status(self) -> None:
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token
        }
        r = requests.get(f'{self.base_url}/user', params=params)
        res = r.json()['data']
        user_information = res['user']
        premium = user_information['isPremium']
        control.setString('alldebrid.username', user_information['username'])
        control.ok_dialog(f'{control.ADDON_NAME}: AllDebrid', control.lang(30023))
        if not premium:
            control.setString('alldebrid.auth.status', 'Expired')
            control.ok_dialog(f'{control.ADDON_NAME}: AllDebrid', control.lang(30024))
        else:
            control.setString('alldebrid.auth.status', 'Premium')

    def addMagnet(self, magnet_hash):
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token,
            'magnets': magnet_hash
        }
        r = requests.get(f'{self.base_url}/magnet/upload', params=params)
        return r.json()['data']

    def resolve_hoster(self, url):
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token,
            'link': url
        }
        r = requests.get(f'{self.base_url}/link/unlock', params=params)
        resolve = r.json()['data']
        return resolve['link']

    def magnet_status(self, magnet_id):
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token,
            'id': magnet_id
        }
        r = requests.get(f'{self.base_url}/magnet/status', params=params)
        return r.json()['data']

    def list_torrents(self):
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token
        }
        r = requests.get(f'{self.base_url}/user/links', params=params)
        return r.json()['data']

    def link_info(self, link):
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token,
            'link[]': link
        }
        r = requests.get(f'{self.base_url}/link/infos', params=params)
        return r.json()['data']

    def resolve_single_magnet(self, hash_, magnet, episode, pack_select, filename):
        magnet_id = self.addMagnet(magnet)['magnets'][0]['id']
        folder_details = self.magnet_status(magnet_id)['magnets']['links']
        folder_details = [{'link': x['link'], 'path': x['filename']} for x in folder_details]

        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, str(episode), pack_select, filename)
            self.delete_magnet(magnet_id)
            if selected_file is not None:
                return self.resolve_hoster(selected_file['link'])

        selected_file = folder_details[0]['link']

        if selected_file is None:
            return None

        self.delete_magnet(magnet_id)
        return self.resolve_hoster(selected_file)

    def resolve_cloud(self, source, pack_select):
        pass

    def delete_magnet(self, magnet_id) -> bool:
        params = {
            'agent': self.agent_identifier,
            'apikey': self.token,
            'id': magnet_id
        }
        r = requests.get(f'{self.base_url}/magnet/delete', params=params)
        return r.ok

    @staticmethod
    def resolve_uncached_source_background(source, autorun):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for All Debrid')

    @staticmethod
    def resolve_uncached_source_forground(source, autorun):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for All Debrid')
