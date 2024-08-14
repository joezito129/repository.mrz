import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.ui import control, database
from resources.lib.indexers import aniskip

playList = control.playList
player = xbmc.Player


class HookMimetype:
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


class WatchlistPlayer(player):
    def __init__(self):
        super(WatchlistPlayer, self).__init__()
        self.vtag = None
        self.resume_time = None
        self.episode = None
        self._build_playlist = None
        self.anilist_id = None
        self._watchlist_update = None
        self.current_time = 0
        self.updated = False
        self.media_type = None
        self.update_percent = int(control.getSetting('watchlist.update.percent'))

        self.total_time = None
        self.delay_time = int(control.getSetting('skipintro.delay'))
        self.skipintro_aniskip_enable = control.getBool('skipintro.aniskip.enable')
        self.skipoutro_aniskip_enable = control.getBool('skipoutro.aniskip.enable')

        self.skipintro_aniskip = False
        self.skipoutro_aniskip = False
        self.skipintro_start = int(control.getSetting('skipintro.delay'))
        self.skipintro_end = self.skipintro_start + int(control.getSetting('skipintro.duration')) * 60
        self.skipoutro_start = 0
        self.skipoutro_end = 0
        self.skipintro_offset = int(control.getSetting('skipintro.aniskip.offset'))
        self.skipoutro_offset = int(control.getSetting('skipoutro.aniskip.offset'))

    def handle_player(self, anilist_id, watchlist_update, build_playlist, episode, resume_time):
        self.anilist_id = anilist_id
        self._watchlist_update = watchlist_update
        self._build_playlist = build_playlist
        self.episode = episode
        self.resume_time = resume_time

        # process skip times
        self.process_hianime()
        self.process_aniwave()
        self.process_aniskip()

        self.keepAlive()

    def onPlayBackStarted(self):
        current_ = playList.getposition()
        self.vtag = playList[current_].getVideoInfoTag()
        self.media_type = self.vtag.getMediaType()
        control.setSetting('addon.last_watched', self.anilist_id)

    def onPlayBackStopped(self):
        control.closeAllDialogs()
        playList.clear()

    def onPlayBackEnded(self):
        control.closeAllDialogs()

    def onPlayBackError(self):
        control.closeAllDialogs()
        playList.clear()
        control.exit_(1)

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
                self._watchlist_update(self.anilist_id, self.episode)
                self.updated = True
                break
            xbmc.sleep(5000)

    def keepAlive(self):
        for inx in range(60):
            xbmc.sleep(500)
            if self.isPlayingVideo() and self.getTime() < 5 and self.getTotalTime() != 0:
                break
        if not self.isPlayingVideo():
            return

        self.total_time = int(self.getTotalTime())
        control.closeAllDialogs()
        if self.resume_time:
            player().seekTime(self.resume_time)

        if self.media_type == 'movie':
            return self.onWatchedPercent()

        if control.getBool('smartplay.skipintrodialog'):
            if self.skipintro_start < 1:
                self.skipintro_start = 1
            while self.isPlaying():
                self.current_time = int(self.getTime())
                if self.current_time > self.skipintro_end:
                    break
                elif self.current_time > self.skipintro_start:
                    PlayerDialogs().show_skip_intro(self.skipintro_aniskip, self.skipintro_end)
                    break
                xbmc.sleep(1000)
        self.onWatchedPercent()

        endpoint = int(control.getSetting('playingnext.time')) if control.getBool('smartplay.playingnextdialog') else 0
        if endpoint != 0:
            while self.isPlaying():
                self.current_time = int(self.getTime())
                if (not self.skipoutro_aniskip and self.total_time - self.current_time <= endpoint) or self.current_time > self.skipoutro_start != 0:
                    PlayerDialogs().display_dialog(self.skipoutro_aniskip, self.skipoutro_end)
                    break
                xbmc.sleep(5000)

    def process_aniskip(self):
        if self.skipintro_aniskip_enable:
            mal_id = database.get_show(self.anilist_id)['mal_id']
            skipintro_aniskip_res = aniskip.get_skip_times(mal_id, self.episode, 'op')
            if skipintro_aniskip_res:
                skip_times = skipintro_aniskip_res['results'][0]['interval']
                self.skipintro_start = int(skip_times['startTime']) + self.skipintro_offset
                self.skipintro_end = int(skip_times['endTime']) + self.skipintro_offset
                self.skipintro_aniskip = True

        if self.skipoutro_aniskip_enable:
            mal_id = database.get_show(self.anilist_id)['mal_id']
            skipoutro_aniskip_res = aniskip.get_skip_times(mal_id, self.episode, 'ed')
            if skipoutro_aniskip_res:
                skip_times = skipoutro_aniskip_res['results'][0]['interval']
                self.skipoutro_start = int(skip_times['startTime']) + self.skipoutro_offset
                self.skipoutro_end = int(skip_times['endTime']) + self.skipoutro_offset
                self.skipoutro_aniskip = True

    def process_aniwave(self):
        if self.skipintro_aniskip_enable:
            aniwave_skipintro_start = int(control.getSetting('aniwave.skipintro.start'))
            if aniwave_skipintro_start != -1:
                self.skipintro_start = aniwave_skipintro_start + self.skipintro_offset
                self.skipintro_end = int(control.getSetting('aniwave.skipintro.end')) + self.skipintro_offset
                self.skipintro_aniskip = True

        if self.skipoutro_aniskip_enable:
            aniwave_skipoutro_start = int(control.getSetting('aniwave.skipoutro.start'))
            if aniwave_skipoutro_start != -1:
                self.skipoutro_start = aniwave_skipoutro_start + self.skipoutro_offset
                self.skipoutro_end = int(control.getSetting('aniwave.skipoutro.end')) + self.skipoutro_offset
                self.skipoutro_aniskip = True

    def process_hianime(self):
        if self.skipintro_aniskip_enable:
            hianime_skipintro_start = int(control.getSetting('hianime.skipintro.start'))
            if hianime_skipintro_start != -1:
                self.skipintro_start = hianime_skipintro_start + self.skipintro_offset
                self.skipintro_end = int(control.getSetting('hianime.skipintro.end')) + self.skipintro_offset
                self.skipintro_aniskip = True
        if self.skipoutro_aniskip_enable:
            hianime_skipoutro_start = int(control.getSetting('hianime.skipoutro.start'))
            if hianime_skipoutro_start != -1:
                self.skipoutro_start = hianime_skipoutro_start + self.skipoutro_offset
                self.skipoutro_end = int(control.getSetting('hianime.skipoutro.end')) + self.skipoutro_offset
                self.skipoutro_aniskip = True


class PlayerDialogs(xbmc.Player):
    def __init__(self):
        super(PlayerDialogs, self).__init__()
        self.playing_file = self.getPlayingFile()

    def display_dialog(self, skipoutro_aniskip, skipoutro_end):
        if playList.size() == 0 or playList.getposition() == (playList.size() - 1):
            return
        if self.playing_file != self.getPlayingFile() or not self.isPlayingVideo() or not self._is_video_window_open():
            return
        self._show_playing_next(skipoutro_aniskip, skipoutro_end)

    def _show_playing_next(self, skipoutro_aniskip, skipoutro_end):
        from resources.lib.windows.playing_next import PlayingNext
        args = self._get_next_item_args()
        args['skipoutro_end'] = skipoutro_end
        if skipoutro_aniskip:
            PlayingNext(*('playing_next_aniskip.xml', control.ADDON_PATH), actionArgs=args).doModal()
        else:
            PlayingNext(*('playing_next.xml', control.ADDON_PATH), actionArgs=args).doModal()

    @staticmethod
    def show_skip_intro(skipintro_aniskip, skipintro_end):
        from resources.lib.windows.skip_intro import SkipIntro
        args = {
            'item_type': 'skip_intro',
            'skipintro_aniskip': skipintro_aniskip,
            'skipintro_end': skipintro_end
        }
        SkipIntro(*('skip_intro.xml', control.ADDON_PATH), actionArgs=args).doModal()

    @staticmethod
    def _get_next_item_args():
        current_position = playList.getposition()
        _next_info = playList[current_position + 1]
        next_info = {
            'item_type': "playing_next",
            'thumb': [_next_info.getArt('thumb')],
            'name': _next_info.getLabel()
        }
        return next_info

    @staticmethod
    def _is_video_window_open():
        return False if xbmcgui.getCurrentWindowId() != 12005 else True


def cancelPlayback():
    playList.clear()
    xbmcplugin.setResolvedUrl(control.HANDLE, False, xbmcgui.ListItem(offscreen=True))


def play_source(linkInfo, subs, anilist_id, watchlist_update, build_playlist, episode, source_select=False, resume_time=None):
    control.print(linkInfo)
    item = xbmcgui.ListItem(path=linkInfo['url'], offscreen=True)
    if subs:
        from resources.lib.ui import embed_extractor
        embed_extractor.del_subs()
        subtitles = []
        for sub in subs:
            sub_url = sub.get('url')
            sub_lang = sub.get('lang')
            subtitles.append(embed_extractor.get_sub(sub_url, sub_lang))
        item.setSubtitles(subtitles)

    if linkInfo['headers'].get('Content-Type'):
        item.setProperty('MimeType', linkInfo['headers']['Content-Type'])
        # Run any mimetype hook
        item = HookMimetype.trigger(linkInfo['headers']['Content-Type'], item)

    if source_select:
        control.playList.add(linkInfo['url'], item)
        playlist_info = build_playlist(anilist_id, episode)
        episode_info = playlist_info[episode - 1]
        control.set_videotags(item, episode_info['info'])
        item.setArt(episode_info['image'])
        player().play(control.playList, item)
        WatchlistPlayer().handle_player(anilist_id, watchlist_update, build_playlist, episode, resume_time)
        return

    xbmcplugin.setResolvedUrl(control.HANDLE, True, item)
    WatchlistPlayer().handle_player(anilist_id, watchlist_update, build_playlist, episode, resume_time)


@HookMimetype('application/dash+xml')
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


@HookMimetype('application/vnd.apple.mpegurl')
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
