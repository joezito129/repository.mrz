import time
import requests
import xbmc

from resources.lib.ui import control, source_utils


class RealDebrid:
    def __init__(self):
        self.ClientID = control.getSetting('rd.client_id')
        if self.ClientID == '':
            self.ClientID = 'X245A4XAIBGVM'
        self.ClientSecret = control.getSetting('rd.secret')
        self.token = control.getSetting('rd.token')
        self.refresh = control.getSetting('rd.refresh')
        self.DeviceCode = ''
        self.OauthTimeout = 0
        self.OauthTimeStep = 0
        self.OauthTotalTimeout = 0
        self.OauthUrl = 'https://api.real-debrid.com/oauth/v2'
        self.BaseUrl = "https://api.real-debrid.com/rest/1.0"

    def headers(self):
        return {'Authorization': f"Bearer {self.token}"}

    def auth_loop(self) -> bool:
        if control.progressDialog.iscanceled():
            self.OauthTimeout = 0
            return False
        control.progressDialog.update(int(self.OauthTimeout/self.OauthTotalTimeout * 100))
        params = {
            'client_id': self.ClientID,
            'code': self.DeviceCode
        }
        r = requests.get(f'{self.OauthUrl}/device/credentials', params=params)
        if r.ok:
            control.log(r.json())
            response = r.json()
            control.setSetting('rd.client_id', response['client_id'])
            control.setSetting('rd.secret', response['client_secret'])
            self.ClientSecret = response['client_secret']
            self.ClientID = response['client_id']
        return r.ok

    def auth(self) -> None:
        self.ClientID = 'X245A4XAIBGVM'
        self.ClientSecret = ''
        params = {
            'client_id': self.ClientID,
            'new_credentials': 'yes'
        }
        resp = requests.get(f'{self.OauthUrl}/device/code', params=params).json()
        copied = control.copy2clip(resp['user_code'])
        display_dialog = (f"{control.lang(30020).format(control.colorstr('https://real-debrid.com/device'))}[CR]"
                          f"{control.lang(30021).format(control.colorstr(resp['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"
        control.progressDialog.create(f'{control.ADDON_NAME}: Real-Debrid Auth', display_dialog)
        control.progressDialog.update(100)
        self.OauthTotalTimeout = self.OauthTimeout = int(resp['expires_in'])
        self.OauthTimeStep = int(resp['interval'])
        self.DeviceCode = resp['device_code']
        auth_done = False
        while not auth_done and self.OauthTimeout > 0:
            self.OauthTimeout -= self.OauthTimeStep
            xbmc.sleep(self.OauthTimeStep * 1000)
            auth_done = self.auth_loop()
        control.progressDialog.close()
        if auth_done:
            self.token_request()
            self.status()

    def token_request(self) -> None:
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

        control.setSetting('rd.token', response['access_token'])
        control.setSetting('rd.refresh', response['refresh_token'])
        control.setInt('rd.expiry', int(time.time()) + int(response['expires_in']))
        self.token = response['access_token']
        self.refresh = response['refresh_token']

    def status(self) -> None:
        user_info = requests.get(f'{self.BaseUrl}/user', headers=self.headers()).json()
        control.setSetting('rd.username', user_info['username'])
        control.setSetting('rd.auth.status', user_info['type'].capitalize())
        control.ok_dialog(control.ADDON_NAME, 'Real Debrid %s' % control.lang(30023))
        if user_info['type'] != 'premium':
            control.ok_dialog(f'{control.ADDON_NAME}: Real-Debrid', control.lang(30024))

    def refreshToken(self) -> None:
        postData = {
            'grant_type': 'http://oauth.net/grant_type/device/1.0',
            'code': self.refresh,
            'client_secret': self.ClientSecret,
            'client_id': self.ClientID
        }
        r = requests.post(f"{self.OauthUrl}/token", data=postData)
        if r.ok:
            response = r.json()
            self.token = response['access_token']
            self.refresh = response['refresh_token']
            control.setSetting('rd.token', self.token)
            control.setSetting('rd.refresh', self.refresh)
            control.setInt('rd.expiry', int(time.time()) + int(response['expires_in']))
            user_info = requests.get(f'{self.BaseUrl}/user', headers=self.headers()).json()
            control.setSetting('rd.username', user_info['username'])
            control.setSetting('rd.auth.status', user_info['type'])
            control.log('refreshed rd.token')
        else:
            control.log(repr(r), 'warning')

    def addMagnet(self, magnet) -> dict:
        postData = {
            'magnet': magnet
        }
        response = requests.post(f'{self.BaseUrl}/torrents/addMagnet', headers=self.headers(), data=postData).json()
        return response

    def list_torrents(self) -> dict:
        response = requests.get(f'{self.BaseUrl}/torrents', headers=self.headers()).json()
        return response

    def torrentInfo(self, torrent_id):
        return requests.get(f'{self.BaseUrl}/torrents/info/{torrent_id}', headers=self.headers()).json()

    def torrentSelect(self, torrentid, fileid='all') -> bool:
        postData = {
            'files': fileid
        }
        r = requests.post(f'{self.BaseUrl}/torrents/selectFiles/{torrentid}', headers=self.headers(), data=postData)
        return r.ok

    def resolve_hoster(self, link):
        postData = {
            'link': link
        }
        response = requests.post(f'{self.BaseUrl}/unrestrict/link', headers=self.headers(), data=postData).json()
        return response['download']

    def deleteTorrent(self, torrent_id) -> None:
        requests.delete(f'{self.BaseUrl}/torrents/delete/{torrent_id}', headers=self.headers(), timeout=10)

    def resolve_single_magnet(self, hash_, magnet, episode='', pack_select=False) -> None:
        pass

    @staticmethod
    def resolve_cloud(source, pack_select):
        if source['torrent_files']:
            best_match = source_utils.get_best_match('path', source['torrent_files'], source['episode'], pack_select)
            if not best_match or not best_match['path']:
                return
            for f_index, torrent_file in enumerate(source['torrent_files']):
                if torrent_file['path'] == best_match['path']:
                    return source['torrent_info']['links'][f_index]

    def resolve_uncached_source(self, source, runinbackground, silent):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        if not runinbackground:
            control.progressDialog.create(heading, "Caching Progress")
        stream_link = None
        self.addMagnet(source['magnet'])
        torrent = self.list_torrents()[0]
        torrent = self.torrentInfo(torrent['id'])
        if not self.torrentSelect(torrent['id']):
            self.deleteTorrent(torrent['id'])
            control.ok_dialog(control.ADDON_NAME, "BAD LINK")
            if runinbackground:
                return
        else:
            if runinbackground:
                control.notify(heading, "The souce is downloading to your cloud")
                return
            while torrent['status'] != 'downloaded':
                xbmc.sleep(1000)
                if control.progressDialog.iscanceled() or control.abort_requested():
                    break
                torrent = self.torrentInfo(torrent['id'])
                f_body = f'''
            Progress: {torrent['progress']} %
            Seeders: {torrent.get('seeders', 0)}
            Speed: {source_utils.get_size(torrent.get('speed', 0))}
'''
                control.progressDialog.update(int(torrent.get('progress', 0)), f_body)
        control.progressDialog.close()
        if torrent['status'] == 'downloaded':
            torrent_files = [selected for selected in torrent['files'] if selected['selected'] == 1]
            if len(torrent['files']) == 1:
                best_match = torrent_files[0]
            else:
                best_match = source_utils.get_best_match('path', torrent_files, source['episode_re'])
            if not best_match or not best_match['path']:
                return
            for f_index, torrent_file in enumerate(torrent_files):
                if torrent_file['path'] == best_match['path']:
                    hash_ = torrent['links'][f_index]
                    stream_link = self.resolve_hoster(hash_)
                    break
            if not silent:
                control.ok_dialog(heading, f'Finished Caching Source\nThe source has been added to your cloud')
        else:
            self.deleteTorrent(torrent['id'])
        if silent:
            self.deleteTorrent(torrent['id'])
        return stream_link
