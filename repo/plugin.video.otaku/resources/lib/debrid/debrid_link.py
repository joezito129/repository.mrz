import time
import requests
import threading
import xbmc

from resources.lib.ui import control, source_utils


class DebridLink:
    def __init__(self):
        self.ClientID = 'sdpBuYFQo6L53s3B4apluw'
        self.token = control.getString('debrid_link.token')
        self.refresh = control.getString('debrid_link.refresh')
        self.agent_identifier = 'Otaku'
        self.api_url = "https://debrid-link.com/api/v2"
        self.cache_check_results = {}
        self.dialog = None

    def headers(self) -> dict:
        return {'User-Agent': self.agent_identifier, 'Authorization': f"Bearer {self.token}"}


    def auth(self):
        import pyqrcode
        import os
        from resources.lib.windows.progress_dialog import Progress_dialog
        url = f'{self.api_url[:-3]}/oauth/device/code'
        data = {'client_id': self.ClientID, 'scope': 'get.post.delete.seedbox get.account'}
        resp = requests.post(url, data=data, headers={'User-Agent': self.agent_identifier}).json()

        OauthTotalTimeout = OauthTimeout = resp['expires_in']
        OauthTimeStep = resp['interval']

        copied = control.copy2clip(resp.get('user_code'))
        display_dialog = (f"{control.lang(30020).format(control.colorstr(resp['verification_url']))}[CR]"
                          f"{control.lang(30021).format(control.colorstr(resp['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"

        qr_path = os.path.join(control.dataPath, 'qr_code.png')
        qr = pyqrcode.create(resp['verification_url'])
        qr.png(qr_path, scale=20)
        config = {
            'heading': f'{control.ADDON_NAME}: Debrid-Link Auth',
            'text': display_dialog,
            'image': qr_path,
            'percent': 100
        }
        self.dialog = Progress_dialog('progress_dialog.xml', control.ADDON_PATH, config=config)
        self.dialog.show()

        data = {
            'client_id': self.ClientID,
            'code': resp['device_code'],
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        }
        auth_done = False
        while not auth_done and OauthTimeout > 0:
            OauthTimeout -= OauthTimeStep
            xbmc.sleep(OauthTimeStep * 1000)
            auth_done, OauthTimeout = self.auth_loop(data, OauthTimeout)
            self.dialog.update(int(OauthTimeout / OauthTotalTimeout * 100))
        if auth_done:
            self.status()


    def auth_loop(self, data, OauthTimeout) -> tuple:
        if self.dialog.iscanceled():
            self.dialog.close()
            OauthTimeout = 0
            return False, OauthTimeout
        url = f"{self.api_url[:-3]}/oauth/token"
        r = requests.post(url, data=data, headers={'User-Agent': self.agent_identifier})
        if r.ok:
            response = r.json()
            self.dialog.close()
            self.token = response.get('access_token')
            self.refresh = response.get('refresh_token')
            control.setString('debrid_link.token', self.token)
            control.setString('debrid_link.refresh', self.refresh)
            control.setInt('debrid_link.expiry', int(time.time()) + int(response['expires_in']))
        return r.ok, OauthTimeout

    def status(self) -> None:
        url = f"{self.api_url[:-3]}/account/infos"
        response = requests.get(url, headers=self.headers()).json()
        username = response['value']['pseudo']
        premium = response['value']['premiumLeft'] > 0
        control.setString('debrid_link.username', username)
        control.ok_dialog(f'{control.ADDON_NAME}: Debrid-Link', control.lang(30023))
        if not premium:
            control.setString('debrid_link.auth.status', 'Expired')
            control.ok_dialog(control.ADDON_NAME, control.lang(30024))
        else:
            control.setString('debrid_link.auth.status', 'Premium')

    def refreshToken(self):
        postData = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh,
            'client_id': self.ClientID
        }
        url = f"{self.api_url[:-3]}/oauth/token"
        response = requests.post(url, data=postData, headers={'User-Agent': self.agent_identifier}).json()
        if response.get('access_token'):
            self.token = response['access_token']
            control.setString('debrid_link.token', self.token)
            control.setInt('debrid_link.expiry', int(time.time()) + response['expires_in'])

    def check_hash(self, hashlist):
        if isinstance(hashlist, list):
            self.cache_check_results = {}
            hashlist = [hashlist[x: x + 100] for x in range(0, len(hashlist), 100)]
            threads = []
            for arg in hashlist:
                t = threading.Thread(target=self._check_hash_thread, args=[arg])
                threads.append(t)
                t.start()
            for i in threads:
                i.join()
            return self.cache_check_results
        else:
            url = f"{self.api_url}/seedbox/cached?url={hashlist}"
            response = requests.get(url, headers=self.headers()).json()
            return response.get('value')

    def _check_hash_thread(self, hashes):
        hashString = ','.join(hashes)
        url = "{0}/seedbox/cached?url={1}".format(self.api_url, hashString)
        response = requests.get(url, headers=self.headers())
        if response.ok:
            self.cache_check_results.update(response.json().get('value'))

    def addMagnet(self, magnet):
        postData = {
            'url': magnet,
            'async': 'true'
        }
        url = f"{self.api_url}/seedbox/add"
        response = requests.post(url, data=postData, headers=self.headers()).json()
        return response.get('value')

    def resolve_single_magnet(self, hash_, magnet, episode, pack_select, filename):
        files = self.addMagnet(magnet)['files']
        folder_details = [{'link': x['downloadUrl'], 'path': x['name']} for x in files]
        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, episode, pack_select, filename)
            if selected_file is not None:
                return selected_file['link']

        sources = [(item.get('size'), item.get('downloadUrl'))for item in files if any(item.get('name').lower().endswith(x) for x in ['avi', 'mp4', 'mkv'])]

        selected_file = max(sources)[1]
        if selected_file is None:
            return
        return selected_file

    @staticmethod
    def resolve_cloud(source, pack_selct):
        pass

    @staticmethod
    def resolve_uncached_source_background(source, autorun):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for Debrid-Link')

    @staticmethod
    def resolve_uncached_source_forground(source, autorun):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for Debrid-Link')
