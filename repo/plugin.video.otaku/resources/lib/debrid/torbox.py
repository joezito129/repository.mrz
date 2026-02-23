import requests
import xbmc

from resources.lib.ui import source_utils, control


class Torbox:
    def __init__(self):
        self.token = control.getSetting('torbox.token')
        self.BaseUrl = "https://api.torbox.app/v1/api"

    def headers(self):
        return {'Authorization': f"Bearer {self.token}"}

    def auth(self) -> None:
        params = {'app': control.ADDON_NAME}
        r = requests.get(f'{self.BaseUrl}/user/auth/device/start', params=params)
        if r.ok:
            res = control.json_res(r).get('data')
            if res:
                device_code = res.get('device_code', '')
                user_code = res.get('code', '')
                verification_url = res.get('friendly_verification_url') or res.get('verification_url', 'https://tor.box/link')
                interval = int(res.get('interval', 5))

                copied = control.copy2clip(user_code)
                display_dialog = (f"{control.lang(30020).format(control.colorstr(verification_url))}[CR]"
                                  f"{control.lang(30021).format(control.colorstr(user_code))}")
                if copied:
                    display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"
                control.progressDialog.create(f'{control.ADDON_NAME}: TorBox Auth', display_dialog)
                control.progressDialog.update(100)

                expires_at = res.get('expires_at', '')
                timeout = total_timeout = 600

                auth_done = False
                while not auth_done and timeout > 0:
                    timeout -= interval
                    xbmc.sleep(interval * 1000)
                    control.progressDialog.update(int(timeout / total_timeout * 100))
                    auth_done, expires_in = self.auth_loop(device_code, timeout)
                control.progressDialog.close()

                if auth_done:
                    self.status()
                control.progressDialog.close()


    def auth_loop(self, device_code, timeout) -> tuple:
        if control.progressDialog.iscanceled():
            timeout = 0
            return False, timeout
        data = {'device_code': device_code}
        r = requests.post(f'{self.BaseUrl}/user/auth/device/token', json=data)
        if r.ok:
            r = control.json_res(r)
            res = r.get('data')
            if 'access_token' in res:
                self.token = res['access_token']
                control.setSetting('torbox.token', self.token)
                return True, timeout
        return False, timeout


    def status(self) -> bool:
        r = requests.get(f'{self.BaseUrl}/user/me', headers=self.headers())
        if r.ok:
            user_info = r.json()['data']
            control.setSetting('torbox.username', user_info['email'])
            if user_info['plan'] == 0:
                control.setSetting('torbox.auth.status', 'Free')
                control.ok_dialog(f'{control.ADDON_NAME}: Torbox', control.lang(30024))
            elif user_info['plan'] == 1:
                control.setSetting('torbox.auth.status', 'Essential')
            elif user_info['plan'] == 3:
                control.setSetting('torbox.auth.status', 'Standard')
            elif user_info['plan'] == 2:
                control.setSetting('torbox.auth.status', 'Pro')
            control.ok_dialog(control.ADDON_NAME, 'Torbox %s' % control.lang(30023))
        return r.ok

    def refreshToken(self):
        url = f'{self.BaseUrl}/v1/api/user/refreshtoken'
        r = requests.post(url, headers=self.headers())
        return r.ok

    def hash_check(self, hash_list: list) -> dict:
        hashes = ','.join(hash_list)
        url = f'{self.BaseUrl}/torrents/checkcached'
        params = {
            'hash': hashes,
            'format': 'list'
        }
        r = requests.get(url, headers=self.headers(), params=params)
        return r.json()['data']

    def addMagnet(self, magnet: str) -> dict:
        url = f'{self.BaseUrl}/torrents/createtorrent'
        data = {
            'magnet': magnet
        }
        r = requests.post(url, headers=self.headers(), data=data)
        return r.json()['data']

    def delete_torrent(self, torrent_id) -> bool:
        url = f'{self.BaseUrl}/torrents/controltorrent'
        data = {
            'torrent_id': str(torrent_id),
            'operation': 'delete'
        }
        r = requests.post(url, headers=self.headers(), json=data)
        return r.ok

    def list_torrents(self) -> dict:
        url = f'{self.BaseUrl}/torrents/mylist'
        r = requests.get(url, headers=self.headers())
        return r.json()['data']

    def get_torrent_info(self, torrent_id: str):
        url = f'{self.BaseUrl}/torrents/mylist'
        params = {'id': torrent_id}
        r = requests.get(url, headers=self.headers(), params=params)
        return r.json()['data']

    def request_dl_link(self, torrent_id, file_id=-1):
        url = f'{self.BaseUrl}/torrents/requestdl'
        params = {
            'token': self.token,
            'torrent_id': torrent_id
        }
        if file_id >= 0:
            params['file_id'] = file_id
        r = requests.get(url, params=params)
        return r.json()['data']

    def resolve_single_magnet(self, hash_, magnet, episode, pack_select):
        torrent = self.addMagnet(magnet)
        torrentId = torrent['torrent_id']
        torrent_info = self.get_torrent_info(torrentId)
        folder_details = [{'fileId': x['id'], 'path': x['name']} for x in torrent_info['files']]
        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, str(episode), pack_select)
            if selected_file and selected_file['fileId'] is not None:
                stream_link = self.request_dl_link(torrentId, selected_file['fileId'])
                self.delete_torrent(torrentId)
                return stream_link
        self.delete_torrent(torrentId)

    def resolve_hoster(self, source):
        return self.request_dl_link(source['folder_id'], source['file']['id'])

    @staticmethod
    def resolve_cloud(source, pack_select):
        if source['hash']:
            best_match = source_utils.get_best_match('short_name', source['hash'], source['episode'], pack_select)
            if not best_match or not best_match['short_name']:
                return
            for f_index, torrent_file in enumerate(source['hash']):
                if torrent_file['short_name'] == best_match['short_name']:
                    return {'folder_id': source['id'], 'file': source['hash'][f_index]}


    @staticmethod
    def resolve_uncached_source_background(source, autorun):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for Torbox')

    @staticmethod
    def resolve_uncached_source_forground(source, autorun):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for Torbox')