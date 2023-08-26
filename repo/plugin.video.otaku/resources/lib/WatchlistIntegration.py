import pickle

from resources.lib.ui import control, database
from resources.lib.ui.router import route
from resources.lib.WatchlistFlavor import WatchlistFlavor
from resources.lib import OtakuBrowser


def get_anilist_res(mal_id):
    from resources.lib.AniListBrowser import AniListBrowser
    return AniListBrowser(control.getSetting("titlelanguage")).get_mal_to_anilist(mal_id)


def get_auth_dialog(flavor):
    from resources.lib.windows import wlf_auth
    platform = control.__sys__.platform
    if 'linux' in platform:
        auth = wlf_auth.AltWatchlistFlavorAuth(flavor).set_settings()
    else:
        auth = wlf_auth.WatchlistFlavorAuth(*('wlf_auth_%s.xml' % flavor, control.ADDON_PATH), flavor=flavor).doModal()
    return WatchlistFlavor.login_request(flavor) if auth else None


@route('watchlist_login/*')
def WL_LOGIN(payload, params):
    auth_dialog = bool(params.get('auth_dialog'))
    return get_auth_dialog(payload) if auth_dialog else WatchlistFlavor.login_request(payload)


@route('watchlist_logout/*')
def WL_LOGOUT(payload, params):
    return WatchlistFlavor.logout_request(payload)


@route('watchlist/*')
def WATCHLIST(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_request(payload), contentType="addons")


@route('watchlist_status_type/*')
def WATCHLIST_STATUS_TYPE(payload, params):
    flavor, status = payload.rsplit("/")
    next_up = bool(params.get('next_up'))
    return control.draw_items(WatchlistFlavor.watchlist_status_request(flavor, status, next_up))


@route('watchlist_status_type_pages/*')
def WATCHLIST_STATUS_TYPE_PAGES(payload, params):
    flavor, status, offset, page = payload.rsplit("/")
    next_up = bool(params.get('next_up'))
    return control.draw_items(WatchlistFlavor.watchlist_status_request_pages(flavor, status, next_up, offset, int(page)))


@route('watchlist_to_ep/*')
def WATCHLIST_TO_EP(payload, params):
    payload_list = payload.rsplit("/")
    anilist_id, mal_id, kitsu_id, eps_watched = payload_list
    if mal_id:
        show_meta = database.get_show_mal(mal_id)
        if not show_meta:
            show_meta = get_anilist_res(mal_id)
    else:
        show_meta = database.get_show(anilist_id)

    anilist_id = show_meta['anilist_id']
    kodi_meta = pickle.loads(show_meta['kodi_meta'])
    kodi_meta['eps_watched'] = eps_watched
    database.update_kodi_meta(anilist_id, kodi_meta)

    anime_general, content_type = OtakuBrowser.get_anime_init(anilist_id)
    return control.draw_items(anime_general, content_type)


@route('watchlist_context/*')
def CONTEXT_MENU(payload, params):
    payload_list = payload.rsplit('/')[1:]
    if len(payload_list) == 5:
        path, anilist_id, mal_id, kitsu_id, eps_watched = payload_list
    else:
        path, anilist_id, mal_id, kitsu_id = payload_list

    if not mal_id:
        show = database.get_show(anilist_id)
        if show:
            mal_id = show['mal_id']
    if not anilist_id:
        show = database.get_show_mal(mal_id)
        if show:
            anilist_id = show['anilist_id']
    else:
        show = None

    flavor = WatchlistFlavor.get_update_flavor()
    if flavor.flavor_name == 'mal':
        actions = [
            ("Add to On Currently Watching", "watching"),
            ("Add to Completed", "completed"),
            ("Add to On Hold", "on_hold"),
            ("Add to Dropped", "dropped"),
            ("Add to Plan to Watch", "plan_to_watch"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]
    else:
        actions = [
            ("Add to Current", "CURRENT"),
            ("Add to Re-Watching", "REPEATING"),
            ("Add to Plan to Watch", "PLANNING"),
            ("Add to Paused", "PAUSED"),
            ("Add to Completed", "COMPLETED"),
            ("Add to Dropped", "DROPPED"),
            ("Set Score", "set_score"),
            ("Delete", "DELETE")
        ]

    if not show:
        show = get_anilist_res(mal_id)

    kodi_meta = pickle.loads(show['kodi_meta'])
    title = kodi_meta['title_userPreferred'] or kodi_meta['name']

    mal_context = control.select_dialog(title, list(map(lambda x: x[0], actions)))
    if mal_context != -1:
        status = actions[mal_context][1]
        if status == 'DELETE':
            yesno = control.yesno_dialog(control.ADDON_NAME,
                                         f'Are you sure you want to delete "{title}" from {flavor.flavor_name}\n    Press YES to Continue')
            if yesno:
                delete_watchlist_anime(anilist_id)
                control.notify(control.ADDON_NAME, f'"{title}" was deleted from {flavor.flavor_name}')
        elif status == 'set_score':
            score_list = [
                "(10) Masterpiece",
                "(9) Great",
                "(8) Very Good",
                "(7) Good",
                "(6) Fine",
                "(5) Average",
                "(4) Bad",
                "(3) Very Bad",
                "(2) Horrible",
                "(1) Appalling",
                "(0) No Score"
            ]
            score = control.select_dialog(title, score_list)
            if score != -1:
                score = 10 - score
                set_watchlist_score(anilist_id, score)
                control.notify(control.ADDON_NAME, f'{title} was set to {score}')
        else:
            set_watchlist_status(anilist_id, status)
            control.notify(control.ADDON_NAME, f'"{title}" was added to "{status}"')

def add_watchlist(items):
    flavors = WatchlistFlavor.get_enabled_watchlists()
    if flavors:
        for flavor in flavors:
            items.insert(0, (
                "%s's %s" % (flavor.username, flavor.title),
                "watchlist/%s" % flavor.flavor_name,
                flavor.image,
            ))
    return items

def watchlist_update_episode(anilist_id, episode):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_update_episdoe(anilist_id, episode)

def set_watchlist_status(anilist_id, status):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_set_status(anilist_id, status)

def set_watchlist_score(anilist_id, score):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_set_score(anilist_id, score)

def delete_watchlist_anime(anilist_id):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_delete_anime(anilist_id)
