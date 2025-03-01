import threading

from copy import deepcopy
from resources.lib.debrid import real_debrid, all_debrid,  debrid_link, premiumize, torbox
from resources.lib.debrid.torbox import Torbox
from resources.lib.ui import control

premiumizeCached = []
realdebridCached = []
all_debridCached = []
debrid_linkCached = []
torboxCached = []

premiumizeUnCached = []
realdebridUnCached = []
all_debridUnCached = []
debrid_linkUnCached = []
torboxUnCached = []
threads = []


def torrentCacheCheck(torrent_list):
    enabled_debrids = control.enabled_debrid()
    if enabled_debrids['real_debrid']:
        t = threading.Thread(target=real_debrid_worker, args=(deepcopy(torrent_list),))
        t.start()
        threads.append(t)

    if enabled_debrids['debrid_link']:
        t = threading.Thread(target=debrid_link_worker, args=(deepcopy(torrent_list),))
        threads.append(t)
        t.start()

    if enabled_debrids['premiumize']:
        t = threading.Thread(target=premiumize_worker, args=(deepcopy(torrent_list),))
        t.start()
        threads.append(t)

    if enabled_debrids['alldebrid']:
        t = threading.Thread(target=all_debrid_worker, args=(deepcopy(torrent_list),))
        t.start()
        threads.append(t)

    if enabled_debrids['torbox']:
        t = threading.Thread(target=torbox_worker, args=(deepcopy(torrent_list),))
        t.start()
        threads.append(t)

    for i in threads:
        i.join()

    cached_list = realdebridCached + premiumizeCached + all_debridCached + debrid_linkCached + torboxCached
    uncached_list = realdebridUnCached + premiumizeUnCached + all_debridUnCached + debrid_linkUnCached + torboxUnCached
    return cached_list, uncached_list


def all_debrid_worker(torrent_list: list):
    if torrent_list:
        for i in torrent_list:
            i['debrid_provider'] = 'alldebrid'
            all_debridUnCached.append(i)


def debrid_link_worker(torrent_list: list):
    if torrent_list:
        cache_check = debrid_link.DebridLink().check_hash([i['hash'] for i in torrent_list])
        if cache_check:
            for i in torrent_list:
                i['debrid_provider'] = 'debrid_link'
                if i['hash'] in list(cache_check.keys()):
                    debrid_linkCached.append(i)
                else:
                    debrid_linkUnCached.append(i)


def real_debrid_worker(torrent_list: list):
    hash_list = [i['hash'] for i in torrent_list]
    if len(hash_list) != 0:
        for torrent in torrent_list:
            torrent['debrid_provider'] = 'real_debrid'
            realdebridUnCached.append(torrent)


def premiumize_worker(torrent_list: list):
    hash_list = [i['hash'] for i in torrent_list]
    if hash_list:
        premiumizeCache = premiumize.Premiumize().hash_check(hash_list)
        premiumizeCache = premiumizeCache['response']

        for index, torrent in enumerate(torrent_list):
            torrent['debrid_provider'] = 'premiumize'
            if premiumizeCache[index] is True:
                premiumizeCached.append(torrent)
            else:
                premiumizeUnCached.append(torrent)


def torbox_worker(torrent_list: list):
    hash_list = [i['hash'] for i in torrent_list]
    if hash_list:
        cache_check = [i['hash'] for i in torbox.Torbox().hash_check(hash_list)]
        for torrent in torrent_list:
            torrent['debrid_provider'] = 'torbox'
            if torrent['hash'] in cache_check:
                torboxCached.append(torrent)
            else:
                torboxUnCached.append(torrent)
