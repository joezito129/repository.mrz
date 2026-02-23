import xbmc
import xbmcgui
import pickle

from resources.lib.ui import control, database
from resources.lib.endpoint import anime_skip, aniskip
from resources.lib import indexers

playList = control.playList
player = xbmc.Player


class WatchlistPlayer(player):
    def __init__(self):
        super().__init__()
        self.vtag = None
        self.episode = None
        self.mal_id = None
        self._watchlist_update = None
        self.current_time = 0
        self.updated = False
        self.media_type = None
        self.update_percent = control.getInt('watchlist.update.percent')
        self.resume = None
        self.path = ''
        self.context = False

        self.total_time = None
        self.delay_time = control.getInt('skipintro.delay')
        self.skipintro_aniskip_enable = control.getBool('skipintro.aniskip.enable')
        self.skipoutro_aniskip_enable = control.getBool('skipoutro.aniskip.enable')

        self.skipintro_aniskip = False
        self.skipoutro_aniskip = False
        self.skipintro_start = control.getInt('skipintro.delay')
        self.skipintro_end = self.skipintro_start + control.getInt('skipintro.duration') * 60
        self.skipoutro_start = 0
        self.skipoutro_end = 0
        self.skipintro_offset = control.getInt('skipintro.aniskip.offset')
        self.skipoutro_offset = control.getInt('skipoutro.aniskip.offset')

    def handle_player(self, mal_id, watchlist_update, episode, resume, path, context):
        self.mal_id = mal_id
        self._watchlist_update = watchlist_update
        self.episode = episode
        self.resume = resume
        self.path = path
        self.context = context

        # process skip times
        self.process_embed('aniwave')
        self.process_embed('hianime')
        self.process_embed('animix')
        self.process_aniskip()
        self.process_animeskip()

        self.keepAlive()

    # def onPlayBackStarted(self):
    #     pass

    def onPlayBackStopped(self):
        control.closeAllDialogs()
        playList.clear()
        if self.context and self.path:
            if 20 < self.getWatchedPercent() < 80:
                query = {
                    'jsonrpc': '2.0',
                    'method': 'Files.SetFileDetails',
                    'params': {
                        'file': self.path,
                        'media': 'video',
                        'resume': {
                            'position': self.current_time,
                            'total': self.total_time
                        }
                    },
                    'id': 1
                }
                res = control.jsonrpc(query)

    def onPlayBackEnded(self):
        control.closeAllDialogs()

    def onPlayBackError(self):
        control.closeAllDialogs()
        playList.clear()

    def build_playlist(self):
        episodes = database.get_episode_list(self.mal_id)
        video_data = indexers.process_episodes(episodes, '') if episodes else []
        playlist = control.bulk_dir_list(video_data)[self.episode:]
        maxplaylist = control.getInt('general.playlist.size')
        if maxplaylist > 0:
            playlist = playlist[:maxplaylist - 1]
        for i in playlist:
            control.playList.add(url=i[0], listitem=i[1])

    def getWatchedPercent(self):
        return (self.current_time / self.total_time) * 100 if self.total_time != 0 else 0

    def onWatchedPercent(self):
        if self._watchlist_update:
            while self.isPlaying() and not self.updated:
                self.current_time = self.getTime()
                watched_percentage = self.getWatchedPercent()
                if watched_percentage > self.update_percent:
                    self._watchlist_update(self.mal_id, self.episode)
                    self.updated = True
                    break
                xbmc.sleep(5000)

    def keepAlive(self):
        monitor = Monitor()
        for _ in range(20):
            if monitor.playbackerror:
                return control.log('playbackerror', 'warning')
            if self.isPlayingVideo() and self.getTotalTime() != 0:
                break
            monitor.waitForAbort(0.25)
        del monitor

        if not self.isPlayingVideo():
            return control.log('Not playing Video', 'warning')

        if self.resume:
            self.seekTime(self.resume)


        if control.getBool('subtitle.enable'):
            query = {
                "jsonrpc": "2.0",
                "method": "Player.GetProperties",
                "params": {
                "playerid": 1,
                    "properties": ["currentaudiostream", 'subtitles']
                },
                "id": 1
            }
            res = control.jsonrpc(query)['result']
            current_audio = res.get('currentaudiostream', {})
            subtitles = res.get('subtitles', [])
            subtitles = sorted(subtitles, key=lambda x: x['isforced'], reverse=True)
            enable_subtitles = False
            for s in subtitles:
                if s['language'] == 'eng':
                    enable_subtitles = True
                    if current_audio['language'] == 'eng':
                        matches = ['signs', 'songs', 'forced']
                    else:
                        matches = ['full', 'dialogue']
                    if any(x in s['name'].lower() for x in matches):
                        self.setSubtitleStream(s['index'])
                        break
            if enable_subtitles:
                self.showSubtitles(enable_subtitles)

        control.setSetting('addon.last_watched', self.mal_id)
        control.closeAllDialogs()

        self.vtag = self.getVideoInfoTag()
        self.media_type = self.vtag.getMediaType()
        self.total_time = int(self.getTotalTime())

        if self.media_type == 'movie':
            self.onWatchedPercent()
        else:
            if self.media_type == 'episode' and playList.size() == 1:
                self.build_playlist()
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

            endpoint = control.getInt('playingnext.time') if control.getBool('smartplay.playingnextdialog') else 0
            if endpoint != 0:
                while self.isPlaying():
                    self.current_time = int(self.getTime())
                    if (not self.skipoutro_aniskip and self.total_time - self.current_time <= endpoint) or self.current_time > self.skipoutro_start != 0:
                        PlayerDialogs().display_dialog(self.skipoutro_aniskip, self.skipoutro_end)
                        break
                    xbmc.sleep(5000)

        while self.isPlaying():
            self.current_time = int(self.getTime())
            xbmc.sleep(5000)

        return None

    def process_aniskip(self):
        if self.skipintro_aniskip_enable and not self.skipintro_aniskip:
            skipintro_aniskip_res = aniskip.get_skip_times(self.mal_id, self.episode, 'op')
            control.log(f'aniskip times: {skipintro_aniskip_res}')
            if skipintro_aniskip_res:
                skip_times = skipintro_aniskip_res['results'][0]['interval']
                self.skipintro_start = int(skip_times['startTime']) + self.skipintro_offset
                self.skipintro_end = int(skip_times['endTime']) + self.skipintro_offset
                self.skipintro_aniskip = True
                control.log(f'found skip times aniskip: {self.skipintro_start} - {self.skipintro_end}')

        if self.skipoutro_aniskip_enable and not self.skipoutro_aniskip:
            skipoutro_aniskip_res = aniskip.get_skip_times(self.mal_id, self.episode, 'ed')
            if skipoutro_aniskip_res:
                skip_times = skipoutro_aniskip_res['results'][0]['interval']
                self.skipoutro_start = int(skip_times['startTime']) + self.skipoutro_offset
                self.skipoutro_end = int(skip_times['endTime']) + self.skipoutro_offset
                self.skipoutro_aniskip = True
                control.log(f'found skip times aniskip: {self.skipoutro_start} - {self.skipoutro_end}')

    def process_animeskip(self):
        show_meta = database.get_show_meta(self.mal_id)
        anilist_id = pickle.loads(show_meta['meta_ids'])['anilist_id']

        if (self.skipintro_aniskip_enable and not self.skipintro_aniskip) or (self.skipoutro_aniskip_enable and not self.skipoutro_aniskip):
            skip_times = anime_skip.get_time_stamps(anime_skip.get_episode_ids(str(anilist_id), int(self.episode)))
            intro_start = None
            intro_end = None
            outro_start = None
            outro_end = None
            if skip_times:
                for skip in skip_times:
                    if self.skipintro_aniskip_enable and not self.skipintro_aniskip:
                        if intro_start is None and skip['type']['name'] in ['Intro', 'New Intro', 'Branding']:
                            intro_start = int(skip['at'])
                        elif intro_end is None and intro_start is not None and skip['type']['name'] in ['Canon']:
                            intro_end = int(skip['at'])
                    if self.skipoutro_aniskip_enable and not self.skipoutro_aniskip:
                        if outro_start is None and skip['type']['name'] in ['Credits', 'New Credits']:
                            outro_start = int(skip['at'])
                        elif outro_end is None and outro_start is not None and skip['type']['name'] in ['Canon', 'Preview']:
                            outro_end = int(skip['at'])

            if intro_start is not None and intro_end is not None:
                self.skipintro_start = intro_start + self.skipintro_offset
                self.skipintro_end = intro_end + self.skipintro_offset
                self.skipintro_aniskip = True
                control.log(f'found skip times animeskip: {self.skipintro_start} - {self.skipintro_end}')
            if outro_start is not None and outro_end is not None:
                self.skipoutro_start = int(outro_start) + self.skipoutro_offset
                self.skipoutro_end = int(outro_end) + self.skipoutro_offset
                self.skipoutro_aniskip = True
                control.log(f'found skip times animeskip: {self.skipoutro_start} - {self.skipoutro_end}')

    def process_embed(self, embed):
        if self.skipintro_aniskip_enable and not self.skipintro_aniskip:
            embed_skipintro_start = control.getInt(f'{embed}.skipintro.start')
            if embed_skipintro_start != -1:
                self.skipintro_start = embed_skipintro_start + self.skipintro_offset
                self.skipintro_end = control.getInt(f'{embed}.skipintro.end') + self.skipintro_offset
                self.skipintro_aniskip = True
                control.log(f'found skip times {embed}: {self.skipintro_start} - {self.skipintro_end}')
        if self.skipoutro_aniskip_enable and not self.skipoutro_aniskip:
            embed_skipoutro_start = control.getInt(f'{embed}.skipoutro.start')
            if embed_skipoutro_start != -1:
                self.skipoutro_start = embed_skipoutro_start + self.skipoutro_offset
                self.skipoutro_end = control.getInt(f'{embed}.skipoutro.end') + self.skipoutro_offset
                self.skipoutro_aniskip = True
                control.log(f'found skip times {embed}: {self.skipoutro_start} - {self.skipoutro_end}')



class PlayerDialogs(xbmc.Player):
    def __init__(self):
        super().__init__()
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
            PlayingNext('playing_next_aniskip.xml', control.ADDON_PATH, actionArgs=args).doModal()
        else:
            PlayingNext('playing_next.xml', control.ADDON_PATH, actionArgs=args).doModal()

    @staticmethod
    def show_skip_intro(skipintro_aniskip, skipintro_end):
        from resources.lib.windows.skip_intro import SkipIntro
        args = {
            'item_type': 'skip_intro',
            'skipintro_aniskip': skipintro_aniskip,
            'skipintro_end': skipintro_end
        }
        SkipIntro('skip_intro.xml', control.ADDON_PATH, actionArgs=args).doModal()

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


class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.playbackerror = False

    def onNotification(self, sender, method, data):
        if method == 'Player.OnStop':
            self.playbackerror = True