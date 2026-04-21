import sys
import xbmc

from urllib import parse

def get_video_info(li) -> dict:
    video_info = {}
    vinfo: xbmc.InfoTagVideo = li.getVideoInfoTag()
    if title := vinfo.getTitle():
        video_info['title'] = title
    if mediatype := vinfo.getMediaType():
        video_info['mediatype'] = mediatype
    if season := vinfo.getSeason():
        video_info['season'] = season
    if episode := vinfo.getEpisode():
        video_info['episode'] = episode
    if plot := vinfo.getPlot():
        video_info['plot'] = plot
    if tvshowtitle := vinfo.getTVShowTitle():
        video_info['tvshowtitle'] = tvshowtitle
    if premiered := vinfo.getPremieredAsW3C():
        video_info['premiered'] = premiered
    if year := vinfo.getYear():
        video_info['year'] = year
    if resume := vinfo.getResumeTime():
        video_info['resume'] = resume

    art = {}
    if tvshowposter := li.getArt('tvshow.poster'):
        art['tvshow.poster'] = tvshowposter
    if poster := li.getArt('thumb'):
        art['thumb'] = poster
    if fanart := li.getArt('fanart'):
        art['fanart'] = fanart
    if banner := li.getArt('banner'):
        art['banner'] = banner
    if clearart := li.getArt('clearart'):
        art['clearart'] = clearart
    if clearlogo := li.getArt('clearlogo'):
        art['clearlogo'] = clearlogo
    if landscape := li.getArt('landscape'):
        art['landscape'] = landscape
    if icon := li.getArt('icon'):
        art['icon'] = icon
    video_info['art'] = art
    return video_info

def set_video_info(video_info):
    import json
    import xbmcgui
    window = xbmcgui.Window(10000)
    window.setProperty('otaku.player.video_info', json.dumps(video_info))

def main():
    arg = sys.argv[1]
    item = sys.listitem
    path = item.getPath()
    params = {}
    plugin = 'plugin://plugin.video.otaku'
    if arg == 'findrecommendations':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"Container.Update({plugin}/find_recommendations{path})")
    elif arg == 'findrelations':
        path = path.split(plugin, 1)[1]
        xbmc.executebuiltin(f"Container.Update({plugin}/find_relations{path})")
    elif arg == 'rescrape':
        video_info = get_video_info(item)
        video_info['path'] = path
        set_video_info(video_info)
        if video_info.get('resume'):
            params['resume'] = video_info['resume']
        path = f"{path}?{parse.urlencode(params)}"
        xbmc.executebuiltin(f"PlayMedia({path})")
    elif arg == 'sourceselect':
        video_info = get_video_info(item)
        video_info['path'] = path
        set_video_info(video_info)
        params['source_select'] = 'true'
        if video_info.get('resume'):
            params['resume'] = video_info['resume']
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
        path = path.split(f'{plugin}/play', 1)[1].replace('_', '/', 1)
        xbmc.executebuiltin(f"RunPlugin({plugin}/marked_as_watched{path})")
    else:
        raise KeyError(f"Could Not find {arg} in Context Menu Action")


if __name__ == "__main__":
    main()
