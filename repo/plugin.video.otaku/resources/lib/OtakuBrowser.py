from resources.lib.ui import control, database

if control.getString('browser.api') == 'mal':
    from resources.lib.MalBrowser import MalBrowser
    BROWSER = MalBrowser()
else:
    from resources.lib.AniListBrowser import AniListBrowser
    BROWSER = AniListBrowser()


def get_anime_init(mal_id: int) -> tuple:
    show = database.get_show(mal_id)
    if show is None:
        show = BROWSER.get_anime(mal_id)
        if show is None:
            return [], 'episodes'

    if control.getBool('override.meta.api'):
        meta_api = control.getString('meta.api')
        if meta_api == 'simkl':
            from resources.lib.indexers import simkl
            data = simkl.SIMKLAPI().get_episodes(mal_id, show)
        elif meta_api == 'anizip':
            from resources.lib.indexers import anizip
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show)
        else:  # elif meta_api == 'jikanmoa':
            from resources.lib.indexers import jikanmoe
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show)
    else:
        from resources.lib.indexers import simkl
        data = simkl.SIMKLAPI().get_episodes(mal_id, show)
        if not data:
            from resources.lib.indexers import anizip
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show)
        if not data:
            from resources.lib.indexers import jikanmoe
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show)
        if not data:
            data = []
    return data, 'episodes'
