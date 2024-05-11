import time
import requests
import threading

from resources.lib.ui import control, source_utils


class RealDebrid:
    def __init__(self):
        self.ClientID = control.getSetting('rd.client_id')
        if self.ClientID == '':
            self.ClientID = 'X245A4XAIBGVM'
        self.OauthUrl = 'https://api.real-debrid.com/oauth/v2'
        self.token = control.getSetting('rd.auth')
        self.refresh = control.getSetting('rd.refresh')
        self.DeviceCode = ''
        self.ClientSecret = control.getSetting('rd.secret')
        self.OauthTimeout = 0
        self.OauthTimeStep = 0
        self.BaseUrl = "https://api.real-debrid.com/rest/1.0"
        self.cache_check_results = {}

    def __headers(self):
        return {
            'Authorization': 'Bearer {}'.format(self.token)
        }

    def auth_loop(self):
        if control.progressDialog.iscanceled():
            control.progressDialog.close()
            return
        time.sleep(self.OauthTimeStep)
        params = {
            'client_id': self.ClientID,
            'code': self.DeviceCode
        }
        r = requests.get(f'{self.OauthUrl}/device/credentials', params=params)
        if r.ok:
            response = r.json()
            control.progressDialog.close()
            control.setSetting('rd.client_id', response['client_id'])
            control.setSetting('rd.secret', response['client_secret'])
            self.ClientSecret = response['client_secret']
            self.ClientID = response['client_id']

    def auth(self):
        self.ClientSecret = ''
        self.ClientID = 'X245A4XAIBGVM'
        params = {
            'client_id': self.ClientID,
            'new_credentials': 'yes'
        }
        response = requests.get(f'{self.OauthUrl}/device/code', params=params).json()
        control.copy2clip(response['user_code'])
        control.progressDialog.create('Real-Debrid Auth')
        control.progressDialog.update(
            -1,
            control.lang(30100).format(control.colorString('https://real-debrid.com/device')) + '[CR]'
            + control.lang(30101).format(control.colorString(response['user_code'])) + '[CR]'
            + control.lang(30102)
        )
        self.OauthTimeout = int(response['expires_in'])
        self.OauthTimeStep = int(response['interval'])
        self.DeviceCode = response['device_code']

        while self.ClientSecret == '':
            self.auth_loop()

        self.token_request()

        user_information = requests.get(f'{self.BaseUrl}/user', headers=self.__headers()).json()
        if user_information['type'] != 'premium':
            control.ok_dialog(control.ADDON_NAME, control.lang(30104))

    def token_request(self):
        if self.ClientSecret == '':
            return

        postData = {
            'client_id': self.ClientID,
            'client_secret': self.ClientSecret,
            'code': self.DeviceCode,
            'grant_type': 'http://oauth.net/grant_type/device/1.0'
        }

        response = requests.post(f'{self.OauthUrl}/token', data=postData)
        response = response.json()

        control.setSetting('rd.auth', response['access_token'])
        control.setSetting('rd.refresh', response['refresh_token'])
        self.token = response['access_token']
        self.refresh = response['refresh_token']
        control.setSetting('rd.expiry', str(int(time.time()) + int(response['expires_in'])))
        user_info = requests.get(f'{self.BaseUrl}/user', headers=self.__headers()).json()
        control.setSetting('rd.username', user_info['username'])
        control.setSetting('rd.auth.status', user_info['type'])
        control.ok_dialog(control.ADDON_NAME, 'Real Debrid %s' % control.lang(30103))

    def refreshToken(self):
        postData = {
            'grant_type': 'http://oauth.net/grant_type/device/1.0',
            'code': self.refresh,
            'client_secret': self.ClientSecret,
            'client_id': self.ClientID
        }
        url = '%s/token' % self.OauthUrl
        r = requests.post(url, data=postData)
        if r.ok:
            response = r.json()
            self.token = response['access_token']
            self.refresh = response['refresh_token']
            control.setSetting('rd.auth', self.token)
            control.setSetting('rd.refresh', self.refresh)
            control.setSetting('rd.expiry', str(int(time.time()) + int(response['expires_in'])))

    def checkHash(self, hashList):
        self.cache_check_results = {}
        hashList = [hashList[x: x + 100] for x in range(0, len(hashList), 100)]
        threads = []
        for arg in hashList:
            t = threading.Thread(target=self._check_hash_thread, args=[arg])
            threads.append(t)
            t.start()
        for i in threads:
            i.join()
        return self.cache_check_results

    def _check_hash_thread(self, hashes):
        hashString = '/'.join(hashes)
        response = requests.get(f'{self.BaseUrl}/torrents/instantAvailability/{hashString}', headers=self.__headers())
        response = response.json()
        self.cache_check_results.update(response)

    def addMagnet(self, magnet):
        postData = {
            'magnet': magnet
        }
        response = requests.post(f'{self.BaseUrl}/torrents/addMagnet', headers=self.__headers(), data=postData).json()
        return response

    def list_torrents(self):
        response = requests.get(f'{self.BaseUrl}/torrents', headers=self.__headers()).json()
        return response

    def torrentInfo(self, torrent_id):
        return requests.get(f'{self.BaseUrl}/torrents/info/{torrent_id}', headers=self.__headers()).json()

    def torrentSelect(self, torrentID, fileID):
        postData = {
            'files': fileID
        }
        r = requests.post(f'{self.BaseUrl}/torrents/selectFiles/{torrentID}', headers=self.__headers(), data=postData)
        return r.ok

    def resolve_hoster(self, link):
        postData = {
            'link': link
        }
        response = requests.post(f'{self.BaseUrl}/unrestrict/link', headers=self.__headers(), data=postData).json()
        return response['download']

    def deleteTorrent(self, torrent_id):
        requests.delete(f'{self.BaseUrl}/torrents/delete/{torrent_id}', headers=self.__headers(), timeout=10)

    def resolve_single_magnet(self, hash_, magnet, episode='', pack_select=False):
        hashCheck = requests.get(f'{self.BaseUrl}/torrents/instantAvailability/{hash_}', headers=self.__headers()).json()
        for _ in hashCheck[hash_]['rd']:
            key_list = 'all'
            torrent = self.addMagnet(magnet)
            self.torrentSelect(torrent['id'], key_list)
            files = self.torrentInfo(torrent['id'])

            selected_files = [(idx, i) for idx, i in enumerate([i for i in files['files'] if i['selected'] == 1])]
            if pack_select:
                best_match = source_utils.get_best_match('path', [i[1] for i in selected_files], episode, pack_select)
                if best_match:
                    try:
                        file_index = [i[0] for i in selected_files if i[1]['path'] == best_match['path']][0]
                        link = files['links'][file_index]
                        stream_link = self.resolve_hoster(link)
                    except IndexError:
                        stream_link = None
                else:
                    stream_link = None
            elif len(selected_files) == 1:
                stream_link = self.resolve_hoster(files['links'][0])
            elif len(selected_files) > 1:
                best_match = source_utils.get_best_match('path', [i[1] for i in selected_files], episode)
                if best_match:
                    try:
                        file_index = [i[0] for i in selected_files if i[1]['path'] == best_match['path']][0]
                        link = files['links'][file_index]
                        stream_link = self.resolve_hoster(link)
                    except IndexError:
                        stream_link = None
                else:
                    stream_link = None
            else:
                stream_link = None
            self.deleteTorrent(torrent['id'])
            return stream_link
