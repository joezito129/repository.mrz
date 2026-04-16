import threading

from copy import deepcopy
from resources.lib.debrid import real_debrid, all_debrid,  debrid_link, premiumize, torbox
from resources.lib.ui import control


class Debrid:
    def __init__(self):
        self.premiumizeCached = []
        self.realdebridCached = []
        self.all_debridCached = []
        self.debrid_linkCached = []
        self.torboxCached = []

        self.premiumizeUnCached = []
        self.realdebridUnCached = []
        self.all_debridUnCached = []
        self.debrid_linkUnCached = []
        self.torboxUnCached = []
        self.threads = []

    def torrentCacheCheck(self, torrent_list):
        for debrid in control.enabled_debrid():
            worker = getattr(self, f'{debrid}_worker', None)
            if worker:
                t = threading.Thread(target=worker, args=(deepcopy(torrent_list),))
                t.start()
                self.threads.append(t)
        for i in self.threads:
            i.join()

        cached_list = self.realdebridCached + self.premiumizeCached + self.all_debridCached + self.debrid_linkCached + self.torboxCached
        uncached_list = self.realdebridUnCached + self.premiumizeUnCached + self.all_debridUnCached + self.debrid_linkUnCached + self.torboxUnCached
        return cached_list, uncached_list

    def alldebrid_worker(self, torrent_list: list):
        if torrent_list:
            for i in torrent_list:
                i['debrid_provider'] = 'alldebrid'
                self.all_debridUnCached.append(i)


    def debrid_link_worker(self, torrent_list: list):
        if torrent_list:
            cache_check = debrid_link.DebridLink().check_hash([i['hash'] for i in torrent_list])
            if cache_check:
                for i in torrent_list:
                    i['debrid_provider'] = 'debrid_link'
                    if i['hash'] in list(cache_check.keys()):
                        self.debrid_linkCached.append(i)
                    else:
                        self.debrid_linkUnCached.append(i)

    def real_debrid_worker(self, torrent_list: list):
        hash_list = [i['hash'] for i in torrent_list]
        if len(hash_list) != 0:
            for torrent in torrent_list:
                torrent['debrid_provider'] = 'real_debrid'
                self.realdebridUnCached.append(torrent)

    def premiumize_worker(self, torrent_list: list):
        hash_list = [i['hash'] for i in torrent_list]
        if hash_list:
            premiumizeCache = premiumize.Premiumize().hash_check(hash_list)
            premiumizeCache = premiumizeCache['response']

            for index, torrent in enumerate(torrent_list):
                torrent['debrid_provider'] = 'premiumize'
                if premiumizeCache[index] is True:
                    self.premiumizeCached.append(torrent)
                else:
                    self.premiumizeUnCached.append(torrent)

    def torbox_worker(self, torrent_list: list):
        hash_list = [i['hash'] for i in torrent_list]
        if hash_list:
            cache_check = [i['hash'] for i in torbox.Torbox().hash_check(hash_list)]
            for torrent in torrent_list:
                torrent['debrid_provider'] = 'torbox'
                if torrent['hash'] in cache_check:
                    self.torboxCached.append(torrent)
                else:
                    self.torboxUnCached.append(torrent)
