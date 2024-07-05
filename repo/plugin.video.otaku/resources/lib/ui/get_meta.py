import threading

from resources.lib.ui import database
from resources.lib.indexers import tmdb, fanart


def collect_meta_(anime_list):
    threads = []
    for anime in anime_list:
        anilist_id = anime['id']
        show_meta = database.get_show_meta(anilist_id)
        if not show_meta:
            mtype = 'movies' if anime.get('format') == 'MOVIE' else 'tv'
            if anime.get('format') == 'ONA' and anime.get('episodes') == 1:
                mtype = 'movies'
            t = threading.Thread(target=update_meta, args=(anilist_id, mtype))
            threads.append(t)
            t.start()
    for thread in threads:
        thread.join()


def update_meta(anilist_id, mtype='tv'):
    meta_ids = database.get_mappings(anilist_id, 'anilist_id')
    art = fanart.getArt(meta_ids, mtype)
    if not art:
        art = tmdb.getArt(meta_ids, mtype)
    elif 'fanart' not in art.keys():
        art2 = tmdb.getArt(meta_ids, mtype)
        if art2.get('fanart'):
            art['fanart'] = art['fanart']
    database.update_show_meta(anilist_id, meta_ids, art)
