import time
from functools import cached_property

import xbmc
import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.cache import use_cache
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.exceptions import UnexpectedResponse
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
import os

RD_AUTH_KEY = "rd.auth"
RD_STATUS_KEY = "rd.premiumstatus"
RD_REFRESH_KEY = "rd.refresh"
RD_EXPIRY_KEY = "rd.expiry"
RD_SECRET_KEY = "rd.secret"
RD_CLIENT_ID_KEY = "rd.client_id"
RD_USERNAME_KEY = "rd.username"
RD_AUTH_CLIENT_ID = "X245A4XAIBGVM"


class RealDebrid:
    def __init__(self):
        self.oauth_url = "https://api.real-debrid.com/oauth/v2/"
        self.device_code_url = "device/code?{}"
        self.device_credentials_url = "device/credentials?{}"
        self.token_url = "token"
        self.device_code = ""
        self.oauth_timeout = 0
        self.oauth_time_step = 0
        self.base_url = "https://api.real-debrid.com/rest/1.0/"
        self.cache_check_results = {}
        self._load_settings()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    def _auth_loop(self):
        url = f"client_id={RD_AUTH_CLIENT_ID}&code={self.device_code}"
        url = self.oauth_url + self.device_credentials_url.format(url)
        response = self.session.get(url).json()
        if "error" not in response and response.get("client_secret"):
            try:
                g.set_setting(RD_CLIENT_ID_KEY, response["client_id"])
                g.set_setting(RD_SECRET_KEY, response["client_secret"])
                self.client_secret = response["client_secret"]
                self.client_id = response["client_id"]
                return True
            except Exception:
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30065))
                raise
        return False

    def auth(self):
        url = f"client_id={self.client_id}&new_credentials=yes"
        url = self.oauth_url + self.device_code_url.format(url)
        response = self.session.get(url).json()
        tools.copy2clip(response["user_code"])
        success = False
        try:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                f"{g.ADDON_NAME}: {g.get_language_string(30017)}",
                tools.create_multiline_message(
                    line1=g.get_language_string(30018).format(g.color_string("https://real-debrid.com/device")),
                    line2=g.get_language_string(30019).format(g.color_string(response["user_code"])),
                    line3=g.get_language_string(30047),
                ),
            )
            self.oauth_timeout = int(response["expires_in"])
            token_ttl = int(response["expires_in"])
            self.oauth_time_step = int(response["interval"])
            self.device_code = response["device_code"]
            progress_dialog.update(100)
            while not success and token_ttl > 0 and not progress_dialog.iscanceled():
                xbmc.sleep(1000)
                if token_ttl % self.oauth_time_step == 0:
                    success = self._auth_loop()
                progress_percent = int(float((token_ttl * 100) / self.oauth_timeout))
                progress_dialog.update(progress_percent)
                token_ttl -= 1
            progress_dialog.close()
        finally:
            del progress_dialog

        if success:
            self.token_request()

            user_information = self.get_url("user")
            if user_information["type"] != "premium":
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30194))

    def token_request(self):
        if not self.client_secret:
            return

        url = self.oauth_url + self.token_url
        response = self.session.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": self.device_code,
                "grant_type": "http://oauth.net/grant_type/device/1.0",
            },
        ).json()
        self._save_settings(response)
        self._save_user_status()
        xbmcgui.Dialog().ok(g.ADDON_NAME, f"Real Debrid {g.get_language_string(30020)}")
        g.log("Authorised Real Debrid successfully", "info")

    def _save_settings(self, response):
        self.token = response["access_token"]
        self.refresh = response["refresh_token"]
        self.expiry = time.time() + int(response["expires_in"])
        g.set_setting(RD_AUTH_KEY, self.token)
        g.set_setting(RD_REFRESH_KEY, self.refresh)
        g.set_setting(RD_EXPIRY_KEY, self.expiry)

    def _save_user_status(self):
        username = self.get_url("user").get("username")
        status = self.get_account_status().title()
        g.set_setting(RD_USERNAME_KEY, username)
        g.set_setting(RD_STATUS_KEY, status)

    def _load_settings(self):
        self.client_id = g.get_setting("rd.client_id", RD_AUTH_CLIENT_ID)
        self.token = g.get_setting(RD_AUTH_KEY)
        self.refresh = g.get_setting(RD_REFRESH_KEY)
        self.expiry = g.get_float_setting(RD_EXPIRY_KEY)
        self.client_secret = g.get_setting(RD_SECRET_KEY)

    @staticmethod
    def _handle_error(response):
        g.log(f"Real Debrid API return a {response.status_code} response")
        g.log(response.text)
        g.log(response.request.url)

    def _is_response_ok(self, response):
        if response.ok:
            return True
        self._handle_error(response)
        return False

    def try_refresh_token(self, force=False):
        if not self.refresh:
            return
        if not force and self.expiry > float(time.time()):
            return

        try:
            with GlobalLock(self.__class__.__name__, True, self.token):
                url = f"{self.oauth_url}token"
                response = self.session.post(
                    url,
                    data={
                        "grant_type": "http://oauth.net/grant_type/device/1.0",
                        "code": self.refresh,
                        "client_secret": self.client_secret,
                        "client_id": self.client_id,
                    },
                )
                if not self._is_response_ok(response):
                    response = response.json()
                    g.notification(g.ADDON_NAME, "Failed to refresh RD token, please manually re-auth")
                    g.log(f"RD Refresh error: {response['error']}")
                    g.log(f"Invalid response from Real Debrid - {response}", "error")
                    return False
                response = response.json()
                self._save_settings(response)
                g.log("Real Debrid Token Refreshed")
                return True
        except RanOnceAlready:
            self._load_settings()
            return

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def post_url(self, url, post_data, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            return None

        response = self.session.post(url, data=post_data, headers=self._get_headers(), timeout=10)
        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token(True)
            response = self.post_url(original_url, post_data, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def get_url(self, url, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            g.log("No Real Debrid Token Found")
            return None

        response = self.session.get(url, headers=self._get_headers(), timeout=10)

        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token(True)
            response = self.get_url(original_url, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def delete_url(self, url, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            g.log("No Real Debrid Token Found")
            return None

        response = self.session.delete(url, headers=self._get_headers(), timeout=10)

        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token(True)
            response = self.delete_url(original_url, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def check_hash(self, hash_list):
        if isinstance(hash_list, list):
            hash_list = [hash_list[x: x + 100] for x in range(0, len(hash_list), 100)]
            thread = ThreadPool()
            for section in hash_list:
                thread.put(self._check_hash_thread, sorted(section))
            thread.wait_completion()
            return self.cache_check_results
        else:
            magnet = 'magnet:?xt=urn:btih:' + hash_list
            response = self.add_magnet(magnet)
            try:
                torr_id = response['id']
            except:
                return {}
            response = self.torrent_select_all(torr_id)
            response = self.torrent_info(torr_id)
            if response['status'] == 'downloaded':
                hash_dict = {hash_list: {'rd': []}}
                for x in response['files']:
                    if x['selected'] == 1:
                        hash_dict[hash_list]['rd'].append(
                            {str(x['id']): {'filename': x['path'], 'filesize': x['bytes']}})
                response = self.delete_torrent(torr_id)
                return hash_dict
            else:
                response = self.delete_torrent(torr_id)
                return {}

    def _check_hash_thread(self, hashes):
        for i in hashes:
            magnet = 'magnet:?xt=urn:btih:' + i
            response = self.add_magnet(magnet)
            try:
                torr_id = response['id']
            except:
                continue
            response = self.torrent_select_all(torr_id)
            response = self.torrent_info(torr_id)
            if response['status'] == 'downloaded':
                hash_dict = {i: {'rd': []}}
                for x in response['files']:
                    if x['selected'] == 1:
                        hash_dict[i]['rd'].append({str(x['id']): {'filename': x['path'], 'filesize': x['bytes']}})
                response = self.delete_torrent(torr_id)
                self.cache_check_results.update(hash_dict)
            else:
                response = self.delete_torrent(torr_id)

    def torrent_select_all(self, torrent_id):
        torr_info = self.torrent_info(torrent_id)
        file_string = ''
        for i in torr_info['files']:
            res = [ele for ele in self.common_video_extensions() if (ele in os.path.splitext(i['path'])[1])]
            if res and ('Sample' in i['path'] or 'sample.' in i['path']) == False:
                if file_string == '':
                    file_string = file_string + str(i['id'])
                else:
                    file_string = file_string + ',' + str(i['id'])
        file_id = 'all'
        response = self.torrent_select(torrent_id, file_string)
        return response

    def add_magnet(self, magnet):
        post_data = {"magnet": magnet}
        url = "torrents/addMagnet"
        return self.post_url(url, post_data)

    def list_torrents(self):
        url = "torrents"
        return self.get_url(url)

    def torrent_info(self, id):
        url = f"torrents/info/{id}"
        return self.get_url(url)

    def torrent_select(self, torrent_id, file_id):
        url = f"torrents/selectFiles/{torrent_id}"
        post_data = {"files": file_id}
        return self.post_url(url, post_data)

    def resolve_hoster(self, link):
        url = "unrestrict/link"
        post_data = {"link": link}
        response = self.post_url(url, post_data)
        try:
            return response["download"]
        except KeyError as e:
            raise UnexpectedResponse(response) from e

    def delete_torrent(self, id):
        url = f"torrents/delete/{id}"
        self.delete_url(url)

    def common_video_extensions(self):
        getSupportedMedia = '.m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.mpd|.m3u|.m3u8|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.udf|.pva|.wmv|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.mk3d|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.001|.wpl|.xspf|.zip|.vdr|.dvr-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.mpl|.webm|.bdmv|.bdm|.wtv|.trp|.f4v|.ssif|.pvr|.disc|'
        return [
            i
            for i in getSupportedMedia.split("|")
            if i not in ["", ".zip", ".rar"]
        ]

    @staticmethod
    def is_streamable_storage_type(storage_variant):
        """
        Confirms that all files within the storage variant are video files
        This ensure the pack from RD is instantly streamable and does not require a download
        :param storage_variant:
        :return: BOOL
        """
        return len([i for i in storage_variant.values() if not source_utils.is_file_ext_valid(i["filename"])]) <= 0

    @use_cache(1)
    def get_relevant_hosters(self):
        host_list = self.get_url("hosts/status")
        if "error" in host_list:
            return []
        return [domain for domain, status in host_list.items() if status["supported"] == 1 and status["status"] == "up"]

    def get_hosters(self, hosters):
        host_list = self.get_relevant_hosters()
        if host_list is None:
            host_list = self.get_relevant_hosters()
        if host_list is not None:
            hosters["premium"]["real_debrid"] = [(i, i.split(".")[0]) for i in host_list]
        else:
            hosters["premium"]["real_debrid"] = []

    @staticmethod
    def is_service_enabled():
        return g.get_bool_setting("realdebrid.enabled") and g.get_setting(RD_AUTH_KEY) is not None

    def get_account_status(self):
        status = None
        status_response = self.get_url("user")
        if isinstance(status_response, dict):
            status = status_response.get("type")
        return status or "unknown"