from resources.lib.ui import control, database

if control.getSetting('browser.api') == 'mal':
    from resources.lib.MalBrowser import MalBrowser
    BROWSER = MalBrowser()
else:
    from resources.lib.AniListBrowser import AniListBrowser
    BROWSER = AniListBrowser()

def get_anime_init(mal_id) -> tuple:
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
        if not data:
            from resources.lib.indexers import anizip
            data = anizip.ANIZIPAPI().get_episodes(mal_id, show_meta)
        if not data:
            from resources.lib.indexers import jikanmoe
            data = jikanmoe.JikanAPI().get_episodes(mal_id, show_meta)
        if not data:
            data = []
    return data, 'episodes'
