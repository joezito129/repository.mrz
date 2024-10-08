import pickle
import requests

from resources.lib import pages
from resources.lib import indexers
from resources.lib.indexers import simkl, anizip, jikanmoe
from resources.lib.ui import control, database, utils


def parse_history_view(res):
    return utils.allocate_item(res, f'search/{res}/1', True, False)


def search_history(search_array):
    result = [utils.allocate_item("New Search", "search//1", True, False, 'new_search.png')]
    result += list(map(parse_history_view, search_array))
    result.append(utils.allocate_item("Clear Search History...", "clear_search_history", False, False, 'clear_search_history.png'))
    return result


def get_episodeList(anilist_id, pass_idx):
    show = database.get_show(anilist_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    if kodi_meta['format'] in ['MOVIE', 'ONA', 'SPECIAL'] and kodi_meta['episodes'] == 1:
        title = kodi_meta['title_userPreferred'] or kodi_meta['name']
        info = {
            "title": title,
            "mediatype": 'movie',
            'plot': kodi_meta['plot'],
            'rating': kodi_meta['rating'],
            'premiered': str(kodi_meta['start_date']),
            'year': int(str(kodi_meta['start_date'])[:4])
        }
        items = [utils.allocate_item(title, 'null', False, True, info=info, poster=kodi_meta['poster'])]

    else:
        episodes = database.get_episode_list(anilist_id)
        items = indexers.process_episodes(episodes, '') if episodes else []
        playlist = control.bulk_player_list(items)[pass_idx:]
        for i in playlist:
            control.playList.add(url=i[0], listitem=i[1])
    return items


def get_meta_ids(anilist_id):
    params = {
        "type": "anilist",
        "id": anilist_id
    }
    r = requests.get('https://armkai.vercel.app/api/search', params=params)
    return r.json()


def get_backup(anilist_id, source):
    show_meta = database.get_show_meta(anilist_id)
    meta_ids = pickle.loads(show_meta['meta_ids'])
    mal_id = meta_ids['mal_id']

    if not mal_id:
        mal_id = get_meta_ids(anilist_id)['mal']
        database.add_mapping_id_meta(anilist_id, mal_id, 'mal_id')
    params = {
        "type": "myanimelist",
        "id": mal_id
    }
    r = requests.get("https://arm2.vercel.app/api/kaito-b", params=params)
    return r.json().get('Pages', {}).get(source, {}) if r.ok else {}


def get_anime_init(anilist_id):
    show_meta = database.get_show_meta(anilist_id)
    if not show_meta:
        from resources.lib.AniListBrowser import AniListBrowser
        AniListBrowser().get_anilist(anilist_id)
        show_meta = database.get_show_meta(anilist_id)
        if not show_meta:
            return [], 'episodes'

    if control.getBool('overide.meta.api'):
        meta_api = control.getSetting('meta.api')
        if meta_api == 'simkl':
            data = simkl.SIMKLAPI().get_episodes(anilist_id, show_meta)
        elif meta_api == 'anizip':
            data = anizip.ANIZIPAPI().get_episodes(anilist_id, show_meta)
        else:    # elif meta_api == 'jikanmoa':
            data = jikanmoe.JikanAPI().get_episodes(anilist_id, show_meta)

    else:
        data = simkl.SIMKLAPI().get_episodes(anilist_id, show_meta)
        if not data[0]:
            data = anizip.ANIZIPAPI().get_episodes(anilist_id, show_meta)
        if not data[0]:
            data = jikanmoe.JikanAPI().get_episodes(anilist_id, show_meta)
        if not data[0]:
            data = [], 'episodes'
    return data


def get_sources(anilist_id, episode, media_type, rescrape=False, source_select=False, silent=False):
    if not (show := database.get_show(anilist_id)):
        from resources.lib.AniListBrowser import AniListBrowser
        show = AniListBrowser().get_anilist(anilist_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    actionArgs = {
        'query': kodi_meta['query'],
        'anilist_id': anilist_id,
        'episode': episode,
        'status': kodi_meta['status'],
        'media_type': media_type,
        'rescrape': rescrape,
        'get_backup': get_backup,
        'source_select': source_select,
        'silent': silent
    }
    sources = pages.getSourcesHelper(actionArgs)
    return sources
