import threading
import copy

from . import real_debrid, premiumize, all_debrid, debrid_link
from resources.lib.ui import control


class TorrentCacheCheck:
    def __init__(self):
        self.premiumizeCached = []
        self.realdebridCached = []
        self.all_debridCached = []
        self.debrid_linkCached = []
        self.threads = []

    def torrentCacheCheck(self, torrent_list):
        if control.real_debrid_enabled():
            self.threads.append(
                threading.Thread(target=self.real_debrid_worker, args=[copy.deepcopy(torrent_list)]))

        if control.debrid_link_enabled():
            self.threads.append(
                threading.Thread(target=self.debrid_link_worker, args=[copy.deepcopy(torrent_list)]))

        if control.premiumize_enabled():
            self.threads.append(threading.Thread(target=self.premiumize_worker, args=[copy.deepcopy(torrent_list)]))

        if control.all_debrid_enabled():
            self.threads.append(threading.Thread(target=self.all_debrid_worker, args=[copy.deepcopy(torrent_list)]))

        for i in self.threads:
            i.start()
        for i in self.threads:
            i.join()

        cachedList = self.realdebridCached + self.premiumizeCached + self.all_debridCached + self.debrid_linkCached
        return cachedList

    def all_debrid_worker(self, torrent_list):

        api = all_debrid.AllDebrid()

        if len(torrent_list) == 0:
            return
        cache_check = api.check_hash([i['hash'] for i in torrent_list])
        if not cache_check:
            return

        cache_list = []
        cached_items = [m.get('hash') for m in cache_check if m.get('instant') is True]

        for i in torrent_list:
            if i['hash'] in cached_items:
                i['debrid_provider'] = 'all_debrid'
                cache_list.append(i)

        self.all_debridCached = cache_list

    def debrid_link_worker(self, torrent_list):
        if len(torrent_list) == 0:
            return

        cache_check = debrid_link.DebridLink().check_hash([i['hash'] for i in torrent_list])

        if not cache_check:
            return

        cache_list = []

        for i in torrent_list:
            if i['hash'] in list(cache_check.keys()):
                i['debrid_provider'] = 'debrid_link'
                cache_list.append(i)

        self.debrid_linkCached = cache_list

    def real_debrid_worker(self, torrent_list):
        cache_list = []
        hash_list = [i['hash'] for i in torrent_list]

        if len(hash_list) == 0:
            return

        realDebridCache = real_debrid.RealDebrid().checkHash(hash_list)

        for i in torrent_list:
            try:
                if 'rd' not in realDebridCache.get(i['hash'], {}):
                    continue
                if len(realDebridCache[i['hash']]['rd']) >= 1:
                    i['debrid_provider'] = 'real_debrid'
                    cache_list.append(i)
            except KeyError:
                pass

        self.realdebridCached = cache_list

    def premiumize_worker(self, torrent_list):
        hash_list = [i['hash'] for i in torrent_list]
        if len(hash_list) == 0:
            return
        premiumizeCache = premiumize.Premiumize().hash_check(hash_list)
        premiumizeCache = premiumizeCache['response']
        cache_list = []
        count = 0
        for i in torrent_list:
            if premiumizeCache[count] is True:
                i['debrid_provider'] = 'premiumize'
                cache_list.append(i)
            count += 1

        self.premiumizeCached = cache_list
