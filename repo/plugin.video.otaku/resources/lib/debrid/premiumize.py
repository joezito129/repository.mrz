import xbmc
import requests

from resources.lib.ui import source_utils, control


class Premiumize:
    def __init__(self):
        self.client_id = "855400527"
        self.token = control.getSetting('premiumize.token')
        self.base_url = 'https://www.premiumize.me/api'
        self.OauthTimeStep = 0
        self.OauthTimeout = 0
        self.OauthTotalTimeout = 0

    def headers(self) -> dict:
        return {'Authorization': f"Bearer {self.token}"}

    def auth(self):
        data = {'client_id': self.client_id, 'response_type': 'device_code'}
        r = requests.post('https://www.premiumize.me/token', data=data)
        resp = r.json()
        self.OauthTotalTimeout = self.OauthTimeout = resp['expires_in']
        self.OauthTimeStep = int(resp['interval'])
        copied = control.copy2clip(resp['user_code'])
        display_dialog = (f"{control.lang(30020).format(control.colorstr(resp['verification_uri']))}[CR]"
                          f"{control.lang(30021).format(control.colorstr(resp['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30022)}"
        control.progressDialog.create(f'{control.ADDON_NAME}: Premiumize', display_dialog)
        control.progressDialog.update(100)

        auth_done = False
        while not auth_done and self.OauthTimeout > 0:
            self.OauthTimeout -= self.OauthTimeStep
            xbmc.sleep(self.OauthTimeStep * 1000)
            auth_done = self.auth_loop(resp['device_code'])
        control.progressDialog.close()

        if auth_done:
            self.status()

    def status(self):
        r = requests.get(f'{self.base_url}/account/info', headers=self.headers())
        user_information = r.json()
        premium = user_information['premium_until'] > 0
        control.setSetting('premiumize.username', user_information['customer_id'])
        control.ok_dialog(f'{control.ADDON_NAME}: Premiumize', control.lang(30023))
        if not premium:
            control.setSetting('premiumize.auth.status', 'Expired')
            control.ok_dialog(f'{control.ADDON_NAME}: Premiumize', control.lang(30024))
        else:
            control.setSetting('premiumize.auth.status', 'Premium')

    def auth_loop(self, device_code):
        if control.progressDialog.iscanceled():
            self.OauthTimeout = 0
            return False
        control.progressDialog.update(int(self.OauthTimeout / self.OauthTotalTimeout * 100))
        data = {'client_id': self.client_id, 'code': device_code, 'grant_type': 'device_code'}
        r = requests.post('https://www.premiumize.me/token', data=data)
        token = r.json()
        if r.ok:
            control.setSetting('premiumize.token', token['access_token'])
            return True
        else:
            if token.get('error') == 'access_denied':
                self.OauthTimeout = 0
            if token.get('error') == 'slow_down':
                xbmc.sleep(1000)
        return False

    def post_url(self, url, data):
        url = "https://www.premiumize.me/api{}".format(url)
        req = requests.post(url, headers=self.headers(), data=data, timeout=10)
        return req.json()

    def list_folder(self, folderid):
        url = "/folder/list"
        postData = {'id': folderid} if folderid else ''
        response = self.post_url(url, postData)
        return response['content']

    def hash_check(self, hashlist) -> dict:
        params = {
            'items[]': hashlist
        }
        r = requests.get(f'{self.base_url}/cache/check', headers=self.headers(), params=params)
        return r.json()

    def direct_download(self, src) -> dict:
        postData = {'src': src}
        r = requests.post(f'{self.base_url}/transfer/directdl', headers=self.headers(), data=postData)
        return r.json()

    def resolve_hoster(self, source):
        directLink = self.direct_download(source)
        return directLink['location'] if directLink['status'] == 'success' else None

    def resolve_single_magnet(self, hash_, magnet, episode='', pack_select=False):
        folder_details = self.direct_download(magnet)['content']
        folder_details = sorted(folder_details, key=lambda i: int(i['size']), reverse=True)
        folder_details = [i for i in folder_details if source_utils.is_file_ext_valid(i['link'])]
        filter_list = [i for i in folder_details]

        if pack_select:
            identified_file = source_utils.get_best_match('path', folder_details, episode, pack_select)
            stream_link = identified_file['link']
            return stream_link

        elif len(filter_list) == 1:
            stream_link = filter_list[0]['link']
            return stream_link

        elif len(filter_list) >= 1:
            identified_file = source_utils.get_best_match('path', folder_details, episode, pack_select)
            stream_link = identified_file['link']
            return stream_link

        filter_list = [tfile for tfile in folder_details if 'sample' not in tfile['path'].lower()]

        if len(filter_list) == 1:
            stream_link = filter_list[0]['link']
            return stream_link

    @staticmethod
    def resolve_uncached_source(source, runinbackground):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        control.ok_dialog(heading, 'Cache Reolver Has not been added for Premiumize')
