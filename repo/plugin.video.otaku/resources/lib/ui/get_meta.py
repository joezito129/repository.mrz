import threading

from resources.lib.indexers.fanart import FANARTAPI
from resources.lib.indexers.tmdb import TMDBAPI
from resources.lib.indexers.trakt import TRAKTAPI
from resources.lib.ui import database


def collect_meta_(anime_list):
    threads = []
    for anime in anime_list:
        if 'media' in anime.keys():
            anime = anime['media']
        anilist_id = anime.get('id')
        show_meta = database.get_show_meta(anilist_id)
        if not show_meta:
            name = anime['title'].get('english')
            if name is None:
                name = anime['title'].get('romaji')
            # name = anime.get['title'].get('english') or anime['title'].get('romaji')
            mtype = 'movies' if anime.get('format') == 'MOVIE' else 'tv'
            if anime.get('format') == 'ONA' and anime.get('episodes') == 1:
                mtype = 'movies'
            year = anime['startDate'].get('year')
            t = threading.Thread(target=get_meta_, args=(anilist_id, name, mtype, year))
            threads.append(t)
            t.start()
    for thread in threads:
        thread.join()


def get_meta_(anilist_id, name, mtype='tv', year=''):
    resp = TRAKTAPI().get_trakt(name, mtype=mtype, year=year)
    if resp:
        meta_ids = resp['ids']
        update_meta(anilist_id, meta_ids, mtype)
    else:
        database.update_show_meta(anilist_id, {}, {})

def update_meta(anilist_id, meta_ids, mtype):
    art = FANARTAPI().getArt(meta_ids, mtype)
    if not art:
        art = TMDBAPI().getArt(meta_ids, mtype)
    elif 'fanart' not in art.keys():
        art2 = TMDBAPI().getArt(meta_ids, mtype)
        if art2.get('fanart'):
            art['fanart'] = art['fanart']
    database.update_show_meta(anilist_id, meta_ids, art)