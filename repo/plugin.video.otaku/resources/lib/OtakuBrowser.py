import pickle
import requests

from resources.lib import pages
from resources.lib import indexers
from resources.lib.indexers import consumet, simkl, jikanmoe
from resources.lib.ui import control, database, utils


def parse_history_view(res):
    return utils.allocate_item(res, "search/%s/1" % res, True)


def search_history(search_array):
    result = list(map(parse_history_view, search_array))
    result.insert(0, utils.allocate_item("New Search", "search", True, 'new_search.png'))
    result.append(utils.allocate_item("Clear Search History...", "clear_history", True, 'clear_search_history.png'))
    return result


def get_episodeList(anilist_id, pass_idx, filter_lang=None):
    show = database.get_show(anilist_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    if kodi_meta['format'] == 'MOVIE' and kodi_meta['episodes'] == 1:
        title = kodi_meta['userPreferred'] or kodi_meta['name']
        info = {
            "title": title,
            "mediatype": 'movie',
            'plot': kodi_meta['plot'],
            'rating': kodi_meta['rating'],
            'premiered': str(kodi_meta['start_date']),
            'year': int(str(kodi_meta['start_date'])[:4])
        }
        items = [utils.allocate_item(title, 'null', info=info, poster=kodi_meta['poster'])]

    else:
        episodes = database.get_episode_list(anilist_id)
        items = indexers.process_episodes(episodes, '') if episodes else []
        playlist = control.bulk_draw_items(items)[pass_idx:]

        for i in playlist:
            url = i[0]
            if filter_lang:
                url += filter_lang
            control.playList.add(url=url, listitem=i[1])
    return items


def get_meta_ids(anilist_id):
    params = {
        "type": "anilist",
        "id": anilist_id
    }
    r = requests.get('https://armkai.vercel.app/api/search', params=params)
    return r.json()


def get_backup(anilist_id, source):
    show = database.get_show(anilist_id)
    mal_id = show['mal_id']

    if not mal_id:
        mal_id = get_meta_ids(anilist_id)['mal']
        database.add_mapping_id(anilist_id, 'mal_id', str(mal_id))
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
        show = AniListBrowser().get_anilist(anilist_id)
        show_meta = database.get_show_meta(anilist_id)
        if not show_meta:
            return [], 'episodes'
    if control.getSetting('overide.meta.api') == 'true':
        meta_api = control.getSetting('meta.api')
        if meta_api == 'consumet':
            data = consumet.CONSUMETAPI().get_episodes(anilist_id, show_meta)
        elif meta_api == 'simkl':
            data = simkl.SIMKLAPI().get_episodes(anilist_id, show_meta)
        elif meta_api == 'jikanmoa':
            data = jikanmoe.JikanAPI().get_episodes(anilist_id, show_meta)
        else:
            data = [], 'episodes'
    else:
        data = simkl.SIMKLAPI().get_episodes(anilist_id, show_meta)
        if not data[0]:
            data = jikanmoe.JikanAPI().get_episodes(anilist_id, show_meta)
        if not data[0]:
            data = [], 'episodes'
    return data


def get_sources(anilist_id, episode, filter_lang, media_type, rescrape=False, source_select=False, download=False):
    show = database.get_show(anilist_id)
    if not show:
        from resources.lib.AniListBrowser import AniListBrowser
        show = AniListBrowser().get_anilist(anilist_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    actionArgs = {
        'query': kodi_meta['query'],
        'anilist_id': anilist_id,
        'episode': episode,
        'status': kodi_meta['status'],
        'filter_lang': filter_lang,
        'media_type': media_type,
        'rescrape': rescrape,
        'get_backup': get_backup,
        'source_select': source_select,
        'download': download
    }
    sources = pages.getSourcesHelper(actionArgs)
    return sources
