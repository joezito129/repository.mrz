import json
import threading
import requests

from resources.lib.ui import control, source_utils
from urllib import parse


class AllDebrid:
    def __init__(self):
        self.apikey = control.getSetting('alldebrid.apikey')
        self.agent_identifier = 'Otaku_Kodi_Addon'
        self.base_url = 'https://api.alldebrid.com/v4/'
        self.cache_check_results = []

    def get(self, url, **params):
        params['agent'] =  self.agent_identifier
        return requests.get(parse.urljoin(self.base_url, url), params=params).text

    def post(self, url, post_data=None, **params):
        params['agent'] =  self.agent_identifier
        return requests.post(parse.urljoin(self.base_url, url), data=post_data, params=params).text

    @staticmethod
    def _extract_data(response):
        return response['data'] if ['data'] in response else response

    def get_json(self, url, **params):
        return self._extract_data(json.loads(self.get(url, **params)))

    def post_json(self, url, post_data=None, **params):
        post_ = self.post(url, post_data, **params)
        if post_:
            return self._extract_data(json.loads(post_))

    def auth(self):
        resp = self.get_json('pin/get')
        expiry = pin_ttl = int(resp['expires_in'])
        auth_complete = False
        control.copy2clip(resp['pin'])
        control.progressDialog.create(
            control.ADDON_NAME + ': AllDebrid Auth',
            control.lang(30100).format(control.colorString(resp['base_url'])) + '[CR]'
            + control.lang(30101).format(control.colorString(resp['pin'])) + '[CR]'
            + control.lang(30102)
        )

        # Seems the All Debrid servers need some time do something with the pin before polling
        # Polling too early will cause an invalid pin error
        control.sleep(5000)
        control.progressDialog.update(100)
        while not auth_complete and not expiry <= 0 and not control.progressDialog.iscanceled():
            auth_complete, expiry = self.poll_auth(check=resp['check'], pin=resp['pin'])
            progress_percent = 100 - int((float(pin_ttl - expiry) / pin_ttl) * 100)
            control.progressDialog.update(progress_percent)
            control.sleep(1000)
        control.progressDialog.close()


        self.store_user_info()

        if auth_complete:
            control.ok_dialog(control.ADDON_NAME, 'AllDebrid {}'.format(control.lang(30103)))

    def poll_auth(self, **params):
        resp = self.get_json('pin/check', **params)
        if resp['activated']:
            control.setSetting('alldebrid.apikey', resp['apikey'])
            self.apikey = resp['apikey']
            return True, 0

        return False, int(resp['expires_in'])

    def store_user_info(self):
        user_information = self.get_json('user', apikey=self.apikey)
        if user_information is not None:
            control.setSetting('alldebrid.username', user_information['user']['username'])

    def check_hash(self, hashList):
        if isinstance(hashList, list):
            self.cache_check_results = []
            hashList = [hashList[x: x + 10] for x in range(0, len(hashList), 10)]
            threads = []
            for section in hashList:
                threads.append(threading.Thread(target=self._check_hash_thread, args=(section,)))
                section.start()
            for i in threads:
                i.join()
            return self.cache_check_results
        else:
            hashString = '&magnets[]=' + hashList
            return self.post_json('magnet/instant', hashString, apikey=self.apikey).get('magnets')

    def _check_hash_thread(self, hashes):
        hashString = '&'.join(['magnets[]=' + x for x in hashes])
        response = self.post_json('magnet/instant', hashString, apikey=self.apikey)
        self.cache_check_results += response.get('magnets')

    def upload_magnet(self, magnet_hash):
        return self.get_json('magnet/upload', apikey=self.apikey, magnets=magnet_hash)

    def update_relevant_hosters(self):
        return

    def get_hosters(self, hosters):
        host_list = self.update_relevant_hosters()
        if host_list is not None:
            hosters['premium']['all_debrid'] = \
                [(d, d.split('.')[0])
                 for x in list(host_list['hosts'].values())
                 if 'status' in x and x['status']
                 for d in x['domains']]
        else:
            hosters['premium']['all_debrid'] = []

    def resolve_hoster(self, url):
        resolve = self.get_json('link/unlock', apikey=self.apikey, link=url)
        return resolve['link']

    def magnet_status(self, magnet_id):
        return self.get_json('magnet/status', apikey=self.apikey, id=magnet_id)

    def resolve_single_magnet(self, hash_, magnet, episode=''):
        selected_file = None

        magnet_id = self.upload_magnet(magnet)['magnets'][0]['id']
        folder_details = self.magnet_status(magnet_id)['magnets']['links']
        folder_details = [{'link': x['link'], 'path': x['filename']} for x in folder_details]

        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, episode)
            self.delete_magnet(magnet_id)
            if selected_file is not None:
                return self.resolve_hoster(selected_file['link'])

        selected_file = folder_details[0]['link']

        if selected_file is None:
            return

        self.delete_magnet(magnet_id)
        return self.resolve_hoster(selected_file)

    def delete_magnet(self, magnet_id):
        return self.get_json('magnet/delete', apikey=self.apikey, id=magnet_id)
