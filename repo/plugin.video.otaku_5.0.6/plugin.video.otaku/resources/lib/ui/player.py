import sys
import xbmc, xbmcgui, xbmcplugin


from resources.lib.ui import client, control, utils, database
from urllib import parse
from resources.lib.indexers import aniskip

HANDLE = control.HANDLE
playList = control.playList
player = control.player


class hook_mimetype:
    __MIME_HOOKS = {}

    @classmethod
    def trigger(cls, mimetype, item):
        if mimetype in cls.__MIME_HOOKS.keys():
            return cls.__MIME_HOOKS[mimetype](item)
        return item

    def __init__(self, mimetype):
        self._type = mimetype

    def __call__(self, func):
        assert self._type not in self.__MIME_HOOKS.keys()
        self.__MIME_HOOKS[self._type] = func
        return func


class watchlistPlayer(player):

    def __init__(self):
        super(watchlistPlayer, self).__init__()
        self._filter_lang = None
        self._episode = None
        self._build_playlist = None
        self._anilist_id = None
        self._watchlist_update = None
        self.current_time = 0
        self.updated = False
        self.media_type = None
        self.update_percent = int(control.getSetting('watchlist.update.percent'))

        self.total_time = None
        self.delay_time = int(control.getSetting('skipintro.delay'))
        self.skipintro_aniskip_enable = control.getSetting('skipintro.aniskip.enable') == 'true'
        self.skipoutro_aniskip_enable = control.getSetting('skipoutro.aniskip.enable') == 'true'
        self.skipintro_start_skip_time = 0
        self.skipintro_end_skip_time = 9999
        self.skipoutro_start_skip_time = 0
        self.skipoutro_end_skip_time = 0
        self.skipintro_aniskip_offset = int(control.getSetting('skipintro.aniskip.offset'))
        self.skipoutro_aniskip_offset = int(control.getSetting('skipoutro.aniskip.offset'))

    def handle_player(self, anilist_id, watchlist_update, build_playlist, episode, filter_lang):
        self._anilist_id = anilist_id
        self._watchlist_update = watchlist_update
        self._build_playlist = build_playlist
        self._episode = episode
        self._filter_lang = filter_lang

        if self.skipintro_aniskip_enable:
            mal_id = database.get_show(anilist_id)['mal_id']
            skipintro_aniskip_res = aniskip.get_skip_times(mal_id, episode, 'op')

            if skipintro_aniskip_res:
                skip_times = skipintro_aniskip_res['results'][0]['interval']
                self.skipintro_start_skip_time = int(skip_times['startTime']) + int(self.skipintro_aniskip_offset)
                self.skipintro_end_skip_time = int(skip_times['endTime']) + int(self.skipintro_aniskip_offset)

        if self.skipoutro_aniskip_enable:
            mal_id = database.get_show(anilist_id)['mal_id']
            skipoutro_aniskip_res = aniskip.get_skip_times(mal_id, episode, 'ed')

            if skipoutro_aniskip_res:
                skip_times = skipoutro_aniskip_res['results'][0]['interval']
                self.skipoutro_start_skip_time = int(skip_times['startTime']) + int(self.skipoutro_aniskip_offset)
                self.skipoutro_end_skip_time = int(skip_times['endTime']) + int(self.skipoutro_aniskip_offset)

        control.setSetting('skipintro.start.skip.time', str(self.skipintro_start_skip_time))
        control.setSetting('skipintro.end.skip.time', str(self.skipintro_end_skip_time))

        control.setSetting('skipoutro.start.skip.time', str(self.skipoutro_start_skip_time))
        control.setSetting('skipoutro.end.skip.time', str(self.skipoutro_end_skip_time))

        self.keepAlive()


    def onPlayBackStarted(self):
        current_ = playList.getposition()
        self.media_type = playList[current_].getVideoInfoTag().getMediaType()
        control.setSetting('addon.last_watched', self._anilist_id)

    def onPlayBackStopped(self):
        playList.clear()

    # def onPlayBackEnded(self):
    #     pass

    def onPlayBackError(self):
        playList.clear()
        sys.exit(1)

    def getWatchedPercent(self):
        current_position = self.getTime()
        media_length = self.getTotalTime()
        return float(current_position) / float(media_length) * 100 if int(media_length) != 0 else 0

    def onWatchedPercent(self):
        if not self._watchlist_update:
            return

        while self.isPlaying() and not self.updated:
            watched_percentage = self.getWatchedPercent()
            self.current_time = self.getTime()

            if watched_percentage > self.update_percent:
                self._watchlist_update(self._anilist_id, self._episode)
                self.updated = True
                break
            xbmc.sleep(5000)

    def keepAlive(self):

        for _ in range(60):
            xbmc.sleep(500)
            if self.isPlayingVideo():
                if self.getTime() < 5 and self.getTotalTime() != 0:
                    break
        if not self.isPlayingVideo():
            return

        self.total_time = int(self.getTotalTime())
        control.closeAllDialogs()

        subtitle_lang = self.getAvailableSubtitleStreams()
        if len(subtitle_lang) > 1:
            if 'eng' in subtitle_lang:
                subtitle_int = subtitle_lang.index('eng')
                self.setSubtitleStream(subtitle_int)

        if self.media_type == 'movie':
            return self.onWatchedPercent()


        if control.getSetting('smartplay.skipintrodialog') == 'true':
            if self.skipintro_aniskip_enable:
                while self.isPlaying():
                    self.current_time = int(self.getTime())
                    if self.current_time > 240:
                        break
                    elif self.skipintro_end_skip_time == 9999:
                        if self.current_time >= self.delay_time:
                            PlayerDialogs()._show_skip_intro()
                            break
                    elif self.current_time > self.skipintro_start_skip_time:
                        PlayerDialogs()._show_skip_intro()
                        break
                    xbmc.sleep(500)
            else:
                while self.isPlaying():
                    self.current_time = int(self.getTime())
                    if self.current_time > 240:
                        break
                    elif self.current_time >= self.delay_time:
                        PlayerDialogs()._show_skip_intro()
                        break
                    xbmc.sleep(500)

        self.onWatchedPercent()

        endpoint = int(control.getSetting('playingnext.time')) if control.getSetting('smartplay.playingnextdialog') == 'true' else False
        if endpoint:
            while self.isPlaying():
                self.current_time = int(self.getTime())
                if self.total_time - self.current_time <= endpoint or self.current_time > self.skipoutro_start_skip_time != 0:
                    PlayerDialogs().display_dialog()
                    break
                xbmc.sleep(5000)

class PlayerDialogs(xbmc.Player):

    def __init__(self):
        super(PlayerDialogs, self).__init__()
        self.playing_file = self.getPlayingFile()

    def display_dialog(self):
        if playList.size() == 0 or playList.getposition() == (playList.size() - 1):
            return
        target = self._show_playing_next
        if self.playing_file != self.getPlayingFile() or not self.isPlayingVideo() or not self._is_video_window_open():
            return
        target()

    def _show_playing_next(self):
        from resources.lib.windows.playing_next import PlayingNext
        if control.getSetting('skipoutro.aniskip.enable') == 'true' and int(control.getSetting('skipoutro.end.skip.time')) != 0:
            PlayingNext(*('playing_next_aniskip.xml', control.ADDON_PATH), actionArgs=self._get_next_item_args()).doModal()
        else:
            PlayingNext(*('playing_next.xml', control.ADDON_PATH),
                        actionArgs=self._get_next_item_args()).doModal()

    @staticmethod
    def _show_skip_intro():
        from resources.lib.windows.skip_intro import SkipIntro
        SkipIntro(*('skip_intro.xml', control.ADDON_PATH), actionArgs={'item_type': 'skip_intro'}).doModal()

    @staticmethod
    def _get_next_item_args():
        current_position = playList.getposition()
        _next_info = playList[current_position + 1]
        next_info = {
            'thumb': [_next_info.getArt('thumb')],
            'name': _next_info.getLabel(),
            'playnext': True
        }
        return next_info

    @staticmethod
    def _is_video_window_open():
        return False if xbmcgui.getCurrentWindowId() != 12005 else True


def cancelPlayback():
    playList.clear()
    xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def _prefetch_play_link(link):
    if callable(link):
        control.print('callable link')
        link = link()

    if not link:
        return
    url = link
    headers = {}

    if '|' in url:
        url, hdrs = link.split('|')
        headers = dict([item.split('=') for item in hdrs.split('&')])
        for header in headers:
            headers[header] = parse.unquote_plus(headers[header])

    limit = None if '.m3u8' in url else '0'

    linkInfo = client.request(url, headers=headers, limit=limit, output='extended', error=True)

    return {
        "url": link if '|' in link else linkInfo[5],
        "headers": linkInfo[2]
    }


def play_source(link, anilist_id=None, watchlist_update=None, build_playlist=None, episode=None, filter_lang=None, rescrape=False, source_select=False, subs=None):
    try:
        if isinstance(link, tuple):
            link, subs = link
        linkInfo = _prefetch_play_link(link)
        if not linkInfo:
            cancelPlayback()
            return
    except Exception as e:
        cancelPlayback()
        control.ok_dialog(control.ADDON_NAME, str(e))
        return

    item = xbmcgui.ListItem(path=linkInfo['url'])

    if subs:
        utils.del_subs()
        subtitles = []
        for sub in subs:
            sub_url = sub.get('url')
            sub_lang = sub.get('lang')
            subtitles.append(utils.get_sub(sub_url, sub_lang))
        item.setSubtitles(subtitles)

    if 'Content-Type' in linkInfo['headers'].keys():
        item.setProperty('MimeType', linkInfo['headers']['Content-Type'])
        # Run any mimetype hook
        item = hook_mimetype.trigger(linkInfo['headers']['Content-Type'], item)

    if rescrape or source_select:
        control.playList.add(linkInfo['url'], item)
        playlist_info = build_playlist(anilist_id, episode, filter_lang)
        episode_info = playlist_info[episode - 1]
        control.set_videotags(item, episode_info['info'])
        item.setArt(episode_info['image'])
        xbmc.Player().play(control.playList, item)
        watchlistPlayer().handle_player(anilist_id, watchlist_update, None, episode, filter_lang)
        return

    xbmcplugin.setResolvedUrl(HANDLE, True, item)
    watchlistPlayer().handle_player(anilist_id, watchlist_update, build_playlist, episode, filter_lang)


@hook_mimetype('application/dash+xml')
def _DASH_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('mpd')
    if is_helper.check_inputstream():
        item.setProperty('inputstream', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        item.setContentLookup(False)
    else:
        raise Exception("InputStream Adaptive is not supported.")
    return item


@hook_mimetype('application/vnd.apple.mpegurl')
def _HLS_HOOK(item):
    stream_url = item.getPath()
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('hls')
    if '|' not in stream_url and is_helper.check_inputstream():
        item.setProperty('inputstream', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    item.setProperty('MimeType', 'application/vnd.apple.mpegurl')
    item.setMimeType('application/vnd.apple.mpegstream_url')
    item.setContentLookup(False)
    return item
