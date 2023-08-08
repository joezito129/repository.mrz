import pickle
import requests

from resources.lib import pages
from resources.lib.indexers import enime, consumet, simkl
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
        title = kodi_meta['ename']
        info = {
            "title": title,
            "mediatype": 'movie',
            'plot': kodi_meta['plot'],
            'rating': kodi_meta['rating'],
            'premiered': str(kodi_meta['start_date']),
        }

        info['year'] = int(info['premiered'][:4])
        items = [
            utils.allocate_item(title, 'null', info=info, poster=kodi_meta['poster'])
        ]

    else:
        episodes = database.get_episode_list(anilist_id)
        items = enime.ENIMEAPI().process_episodes(episodes, '') if episodes else []
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
    if r.ok:
        r = r.json()
        result = r.get('Pages', {}).get(source, {})
        return result


def get_anime_init(anilist_id):
    meta_api = control.getSetting('meta.api')
    if meta_api == 'consumet':
        return consumet.CONSUMETAPI().get_episodes(anilist_id)
    elif meta_api == 'simkl':
        return simkl.SIMKLAPI().get_episodes(anilist_id)
    else:
        return enime.ENIMEAPI().get_episodes(anilist_id)


def get_sources(anilist_id, episode, filter_lang, media_type, rescrape=False, source_select=False, download=False):
    show = database.get_show(anilist_id)
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
