import sys
import xbmc

from urllib import parse


def get_video_info(li) -> dict:
    params = {}
    vinfo: xbmc.InfoTagVideo = li.getVideoInfoTag()
    if title := vinfo.getTitle():
        params['title'] = title
    if mediatype := vinfo.getMediaType():
        params['mediatype'] = mediatype
    if season := vinfo.getSeason():
        params['season'] = str(season)
    if episode := vinfo.getEpisode():
        params['episode'] = str(episode)
    if plot := vinfo.getPlot():
        params['plot'] = str(plot)
    if tvshowtitle := vinfo.getTVShowTitle():
        params['tvshowtitle'] = tvshowtitle
    # if premiered := vinfo.getPremieredAsW3C():
    #     params['premiered'] = premiered
    if year := vinfo.getYear():
        params['year'] = str(year)
    if resume := vinfo.getResumeTime():
        params['resume'] = str(resume)

    if tvshowposter := li.getArt('tvshow.poster'):
        params['tvshow.poster'] = tvshowposter
    if poster := li.getArt('thumb'):
        params['thumb'] = poster

    # if fanart := li.getArt('fanart'):
    #     params['fanart'] = fanart
    # if banner := li.getArt('banner'):
    #     params['banner'] = banner
    # if clearart := li.getArt('clearart'):
    #     params['clearart'] = clearart
    # if clearlogo := li.getArt('clearlogo'):
    #     params['clearlogo'] = clearlogo
    # if landscape := li.getArt('landscape'):
    #     params['landscape'] = landscape
    # if icon := li.getArt('icon'):
    #     params['icon'] = icon
    return params

def main():
    arg = sys.argv[1]
    item = sys.listitem
    path = item.getPath()
    plugin = 'plugin://plugin.video.otaku'
    if arg == 'findrecommendations':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"ActivateWindow(Videos,{plugin}/find_recommendations{path})")
    elif arg == 'findrelations':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"ActivateWindow(Videos,{plugin}/find_relations{path})")
    elif arg == 'rescrape':
        params = get_video_info(item)
        params['rescrape'] = 'true'
        path = f"{path}?{parse.urlencode(params)}"
        xbmc.executebuiltin(f"PlayMedia({path})")
    elif arg == 'sourceselect':
        params = get_video_info(item)
        params['source_select'] = 'true'
        path = f"{path}?{parse.urlencode(params)}"
        xbmc.executebuiltin(f"PlayMedia({path})")
    elif arg == 'logout':
        path = path.split(f'{plugin}/watchlist', 1)[1]
        xbmc.executebuiltin(f"RunPlugin({plugin}/watchlist_logout{path})")
    elif arg == 'deletefromdatabase':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"RunPlugin({plugin}/delete_anime_database{path})")
    elif arg == 'watchlist':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"RunPlugin({plugin}/watchlist_manager{path})")
    elif arg == 'markedaswatched':
        path = path.split(f'{plugin}/play', 1)[1]
        xbmc.executebuiltin(f"RunPlugin({plugin}/marked_as_watched{path})")
    elif arg == 'fanartselect':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"ActivateWindow(Videos,{plugin}/fanart_select{path})")
    else:
        raise KeyError("Could Not find %s in Context Menu Action" % arg)


if __name__ == "__main__":
    main()
