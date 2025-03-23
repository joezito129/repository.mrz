import threading

from resources.lib.ui import database
from resources.lib.endpoint import tmdb, fanart


def collect_meta(anime_list):
    threads = []
    for anime in anime_list:
        mal_id = anime.get('idMal') or anime.get('mal_id')
        if not mal_id:
            continue
        if not database.get_show_meta(mal_id):
            if (anime.get('format', '').lower() or anime.get('type', '').lower()) in ['movie', 'special', 'ona'] and anime.get('episodes') == 1:
                mtype = 'movies'
            else:
                mtype = 'tv'
            t = threading.Thread(target=update_meta, args=(mal_id, mtype))
            t.start()
            threads.append(t)
    for thread in threads:
        thread.join()


def update_meta(mal_id, mtype='tv'):
    meta_ids = database.get_mappings(mal_id, 'mal_id')
    art = fanart.getArt(meta_ids, mtype)
    if not art:
        art = tmdb.getArt(meta_ids, mtype)
    elif 'fanart' not in art.keys():
        art2 = tmdb.getArt(meta_ids, mtype)
        if art2.get('fanart'):
            art['fanart'] = art['fanart']
    database.update_show_meta(mal_id, meta_ids, art)
