import pickle

from resources.lib.ui import control, database, utils

if control.getSetting('browser.api') == 'mal':
    from resources.lib.MalBrowser import MalBrowser
    BROWSER = MalBrowser()
else:
    from resources.lib.AniListBrowser import AniListBrowser
    BROWSER = AniListBrowser()


def get_episodeList(mal_id, pass_idx):
    from resources.lib import indexers
    show = database.get_show(mal_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    if kodi_meta['format'] in ['MOVIE', 'ONA', 'SPECIAL', 'Movie', 'Special'] and kodi_meta['episodes'] == 1:
        title = kodi_meta['title_userPreferred'] or kodi_meta['name']
        info = {
            "title": title,
            "mediatype": 'movie',
            'plot': kodi_meta['plot'],
            'rating': kodi_meta['rating'],
            'premiered': str(kodi_meta['start_date']),
            'year': int(str(kodi_meta['start_date'])[:4])
        }
        items = [utils.allocate_item(title, 'null', False, True, [], info=info, poster=kodi_meta['poster'])]

    else:
        episodes = database.get_episode_list(mal_id)
        items = indexers.process_episodes(episodes, '') if episodes else []
        playlist = control.bulk_player_list(items)[pass_idx:]
        for i in playlist:
            control.playList.add(url=i[0], listitem=i[1])
    return items


def get_anime_init(mal_id) -> tuple[list, str]:
    show_meta = database.get_show_meta(mal_id)
    if not show_meta:
        BROWSER.get_anime(mal_id)
        show_meta = database.get_show_meta(mal_id)
        if not show_meta:
            return [], 'episodes'

    if control.getBool('override.meta.api'):
        meta_api = control.getSetting('meta.api')
        if meta_api == 'simkl':
            from resources.lib.indexers import simkl
            data = simkl.SIMKLAPI().get_episodes(mal_id, show_meta)
        elif meta_api == 'anizip':
            from resources.lib.indexers import anizip
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show_meta)
        else:  # elif meta_api == 'jikanmoa':
            from resources.lib.indexers import jikanmoe
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show_meta)

    else:
        from resources.lib.indexers import simkl
        data = simkl.SIMKLAPI().get_episodes(mal_id, show_meta)
        if not data[0]:
            from resources.lib.indexers import anizip
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show_meta)
        if not data[0]:
            from resources.lib.indexers import jikanmoe
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show_meta)
        if not data[0]:
            data = [], 'episodes'
    return data
