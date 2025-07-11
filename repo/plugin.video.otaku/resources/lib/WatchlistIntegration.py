import pickle

from resources.lib.ui import control, database
from resources.lib.ui.router import Route
from resources.lib.WatchlistFlavor import WatchlistFlavor
from resources.lib import OtakuBrowser

BROWSER = OtakuBrowser.BROWSER


def get_auth_dialog(flavor):
    from resources.lib.windows import wlf_auth
    platform = control.sys.platform
    if 'linux' in platform:
        auth = wlf_auth.AltWatchlistFlavorAuth(flavor).set_settings()
    else:
        auth = wlf_auth.WatchlistFlavorAuth('wlf_auth_%s.xml' % flavor, control.ADDON_PATH, flavor=flavor).doModal()
    return WatchlistFlavor.login_request(flavor) if auth else None


@Route('watchlist_login/*')
def WL_LOGIN(payload: str, params: dict):
    auth_dialog = bool(params.get('auth_dialog'))
    get_auth_dialog(payload) if auth_dialog else WatchlistFlavor.login_request(payload)
    control.exit_code()


@Route('watchlist_logout/*')
def WL_LOGOUT(payload: str, params: dict):
    WatchlistFlavor.logout_request(payload)
    control.refresh()
    control.exit_code()


@Route('watchlist/*')
def WATCHLIST(payload: str, params: dict):
    control.draw_items(WatchlistFlavor.watchlist_request(payload), 'addons')


@Route('watchlist_status_type/*')
def WATCHLIST_STATUS_TYPE(payload: str, params: dict):
    flavor, status = payload.split("/", 1)
    next_up = bool(params.get('next_up'))
    content_type = 'videos' if next_up else 'tvshows'
    control.draw_items(WatchlistFlavor.watchlist_status_request(flavor, status, next_up), content_type)


@Route('watchlist_status_type_pages/*')
def WATCHLIST_STATUS_TYPE_PAGES(payload: str, params: dict):
    flavor, status, offset = payload.split("/", 2)
    page = int(params.get('page', 1))
    next_up = bool(params.get('next_up'))
    content_type = 'videos' if next_up else 'tvshows'
    control.draw_items(WatchlistFlavor.watchlist_status_request(flavor, status, next_up, offset, page), content_type)


@Route('watchlist_to_ep/*')
def WATCHLIST_TO_EP(payload: str, params: dict):
    mal_id, eps_watched = payload.split("/", 1)
    show_meta = database.get_show(mal_id)
    if not show_meta:
        show_meta = BROWSER.get_anime(mal_id)
    kodi_meta = pickle.loads(show_meta['kodi_meta'])
    kodi_meta['eps_watched'] = eps_watched
    database.update_kodi_meta(mal_id, kodi_meta)
    control.draw_items(*OtakuBrowser.get_anime_init(mal_id))


@Route('watchlist_manager/*')
def CONTEXT_MENU(payload: str, params: dict):
    if not control.getBool('watchlist.update.enabled'):
        control.ok_dialog(control.ADDON_NAME, 'No Watchlist Enabled: \n\nPlease enable [B]Update Watchlist[/B] before using the Watchlist Manager')
        return control.exit_code()
    path, mal_id, eps_watched  = payload.split('/', 2)

    if not (show := database.get_show(mal_id)):
        show = BROWSER.get_anime(mal_id)

    if not (flavor := WatchlistFlavor.get_update_flavor()):
        control.ok_dialog(control.ADDON_NAME, 'No Watchlist Enabled: \n\nPlease Enable a Watchlist before using the Watchlist Manager')
        return control.exit_code()

    actions = WatchlistFlavor.context_statuses()

    kodi_meta = pickle.loads(show['kodi_meta'])
    title = kodi_meta['title_userPreferred']

    context = control.select_dialog(f"{title}  {control.colorstr(f'({str(flavor.flavor_name).capitalize()})', 'blue')}", list(map(lambda x: x[0], actions)))
    if context != -1:
        heading = f'{control.ADDON_NAME} - ({str(flavor.flavor_name).capitalize()})'
        status = actions[context][1]
        if status == 'DELETE':
            yesno = control.yesno_dialog(heading, f'Are you sure you want to delete [I]{title}[/I] from [B]{flavor.flavor_name}[/B]\n\nPress YES to Continue:')
            if yesno:
                delete = delete_watchlist_anime(mal_id)
                if delete:
                    control.ok_dialog(heading, f'[I]{title}[/I] was deleted from [B]{flavor.flavor_name}[/B]')
                else:
                    control.ok_dialog(heading, 'Unable to delete from Watchlist')
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
            score = control.select_dialog(f'{title}: ({str(flavor.flavor_name).capitalize()})', score_list)
            if score != -1:
                score = 10 - score
                set_score = set_watchlist_score(mal_id, score)
                if set_score:
                    control.ok_dialog(heading, f'[I]{title}[/I]   was set to [B]{score}[/B]')
                else:
                    control.ok_dialog(heading, 'Unable to Set Score')
        else:
            set_status = set_watchlist_status(mal_id, status)
            if set_status == 'watching':
                control.ok_dialog(heading, 'This show is still airing, so we\'re keeping it in your "Watching" list and marked all aired episodes as watched.')
            elif set_status:
                control.ok_dialog(heading, f'[I]{title}[/I]  was added to [B]{status}[/B]')
            else:
                control.ok_dialog(heading, 'Unable to Set Watchlist')
    return control.exit_code()


def add_watchlists(items: list) -> list:
    flavors = WatchlistFlavor.get_enabled_watchlists()
    if flavors:
        for flavor in flavors:
            items.append((f"{flavor.username}'s {flavor.title}", f"watchlist/{flavor.flavor_name}", flavor.image, {}))
    return items


def watchlist_update_episode(mal_id, episode):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_update_episode(mal_id, episode)


def set_watchlist_status(mal_id, status):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_set_status(mal_id, status)


def set_watchlist_score(mal_id, score):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_set_score(mal_id, score)


def delete_watchlist_anime(mal_id):
    flavor = WatchlistFlavor.get_update_flavor()
    if flavor:
        return WatchlistFlavor.watchlist_delete_anime(mal_id)
