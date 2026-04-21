import threading

from resources.lib.ui import database
from resources.lib.endpoint import tmdb, fanart


def collect_meta(anime_list):
    threads = []
    for anime in anime_list:
        mal_id = anime.get('idMal') or anime.get('mal_id')
        if mal_id is None:
            continue
        if database.get_show(mal_id) is None:
            if (anime.get('format') or anime.get('type')) in ['MOVIE', 'ONA', 'OVA', 'SPECIAL', 'Movie', "Special"] and anime.get('episodes') == 1:
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
    elif art.get('fanart') is None:
        art2 = tmdb.getArt(meta_ids, mtype)
        if (fanart2 := art2.get('fanart')) is not None:
            art['fanart'] = fanart2
    database.create_show(mal_id, meta_ids.get('anilist_id'), meta_ids.get('kitsu_id'), meta_ids.get('anidb_id'), meta_ids.get('simkl_id'), art)
