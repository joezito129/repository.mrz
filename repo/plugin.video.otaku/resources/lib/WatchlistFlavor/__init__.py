from resources.lib.ui import control
from resources.lib.WatchlistFlavor import AniList, Kitsu, MyAnimeList, Simkl
from resources.lib.WatchlistFlavor.WatchlistFlavorBase import WatchlistFlavorBase


class WatchlistFlavor:
    __SELECTED = None

    def __init__(self):
        raise Exception("Static Class should not be created")


    @staticmethod
    def get_enabled_watchlists() -> list:
        return [WatchlistFlavor.__instance_flavor(x) for x in control.enabled_watchlists()]


    @staticmethod
    def get_update_flavor():
        selected = control.watchlist_to_update()
        if selected is None:
            return None
        if WatchlistFlavor.__SELECTED is None:
            WatchlistFlavor.__SELECTED = WatchlistFlavor.__instance_flavor(selected)
        return WatchlistFlavor.__SELECTED


    @staticmethod
    def watchlist_request(name):
        return WatchlistFlavor.__instance_flavor(name).watchlist()


    @staticmethod
    def watchlist_action_statuses(name):
        return WatchlistFlavor.__instance_flavor(name).action_statuses()


    @staticmethod
    def watchlist_status_request(name, status, next_up, offset=0, page=1):
        return WatchlistFlavor.__instance_flavor(name).get_watchlist_status(status, next_up, offset, page)


    @staticmethod
    def login_request(flavor) -> None:
        if not WatchlistFlavor.__is_flavor_valid(flavor):
            raise Exception(f"Invalid flavor {flavor}")
        flavor_class = WatchlistFlavor.__instance_flavor(flavor)
        succeeded = flavor_class.login()
        if succeeded:
            control.ok_dialog('Login', 'Success')
        else:
            control.ok_dialog('Login', 'Incorrect username or password')
        return None


    @staticmethod
    def logout_request(flavor) -> None:
        control.setString('%s.authvar' % flavor, '')
        control.setString('%s.token' % flavor, '')
        control.setString('%s.refresh' % flavor, '')
        control.setString('%s.username' % flavor, '')
        control.setString('%s.password' % flavor, '')
        control.refresh()

    @staticmethod
    def __get_flavor_class(name):
        for flav in WatchlistFlavorBase.__subclasses__():
            if flav.name() == name:
                return flav
        return None


    @staticmethod
    def __is_flavor_valid(name) -> bool:
        return WatchlistFlavor.__get_flavor_class(name) is not None


    @staticmethod
    def __instance_flavor(name):
        auth_var = control.getString(f"{name}.authvar")
        token = control.getString(f"{name}.token")
        refresh = control.getString(f"{name}.refresh")
        username = control.getString(f"{name}.username")
        sort = control.getInt(f"{name}.sort")

        flavor_class = WatchlistFlavor.__get_flavor_class(name)
        return flavor_class(auth_var, username, token, refresh, sort)


    @staticmethod
    def watchlist_anime_entry_request(mal_id: int):
        return WatchlistFlavor.get_update_flavor().get_watchlist_anime_entry(mal_id)


    @staticmethod
    def context_statuses():
        return WatchlistFlavor.get_update_flavor().action_statuses()


    @staticmethod
    def watchlist_update_episode(mal_id, episode):
        return WatchlistFlavor.get_update_flavor().update_num_episodes(mal_id, episode)


    @staticmethod
    def watchlist_set_status(mal_id, status):
        return WatchlistFlavor.get_update_flavor().update_list_status(mal_id, status)


    @staticmethod
    def watchlist_set_score(mal_id, score):
        return WatchlistFlavor.get_update_flavor().update_score(mal_id, score)


    @staticmethod
    def watchlist_delete_anime(mal_id):
        return WatchlistFlavor.get_update_flavor().delete_anime(mal_id)
