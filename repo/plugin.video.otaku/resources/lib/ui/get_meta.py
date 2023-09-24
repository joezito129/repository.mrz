import threading

from resources.lib.indexers.fanart import FANARTAPI
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.ui import database


def collect_meta(anime_list):
    threads = []
    for anime in anime_list:
        if 'media' in anime.keys():
            anime = anime['media']
        anilist_id = anime.get('id')
        show_meta = database.get_show_meta(anilist_id)
        if not show_meta:
            mtype = 'movies' if anime.get('format') == 'MOVIE' else 'tv'
            if anime.get('format') == 'ONA' and anime.get('episodes') == 1:
                mtype = 'movies'
            t = threading.Thread(target=get_meta, args=(anilist_id, {}, mtype))
            t.start()
            threads.append(t)
    for thread in threads:
        thread.join()
        

def get_meta(anilist_id, meta_ids, mtype):
    meta = FANARTAPI().getArt(meta_ids, mtype)
    if not meta:
        meta = TMDBAPI().getArt(meta_ids, mtype)
    elif 'fanart' not in meta.keys():
        meta2 = TMDBAPI().getArt(meta_ids, mtype)
        if meta2.get('fanart'):
            meta['fanart'] = meta2['fanart']
    database.update_show_meta(anilist_id, meta_ids, meta)
