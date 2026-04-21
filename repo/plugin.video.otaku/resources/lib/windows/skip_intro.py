import xbmc

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class SkipIntro(BaseWindow):
    def __init__(self, xml_file, xml_location, *args, actionArgs=None):
        super().__init__(xml_file, xml_location, actionArgs=actionArgs)
        self.player = xbmc.Player()
        self.total_time = int(self.player.getTotalTime())
        self.playing_file = self.player.getPlayingFile()
        self.current_time = 0
        self.skipintro_end_skip_time = actionArgs['skipintro_end']
        self.skipintro_aniskip = actionArgs['skipintro_aniskip']
        self.closed = False
        self.actioned = None

    def onInit(self):
        self.background_tasks()

    def background_tasks(self):
        self.current_time = self.player.getTime()
        while self.total_time - self.current_time > 2 and not self.closed and self.playing_file == self.player.getPlayingFile():
            self.current_time = self.player.getTime()
            if self.current_time > self.skipintro_end_skip_time:
                self.close()
                break
            xbmc.sleep(500)
        self.close()

    def close(self):
        self.closed = True
        super(SkipIntro, self).close()

    def onClick(self, controlId):
        self.handle_action(controlId)

    def handle_action(self, controlId):
        if controlId == 3001:
            self.actioned = True
            current_chapter = xbmc.getInfoLabel('Player.ChapterName').lower()
            if any(x in current_chapter for x in control.intro_keywords):
                xbmc.executebuiltin("Action(ChapterOrBigStepForward)")
            elif self.skipintro_aniskip:
                self.player.seekTime(self.skipintro_end_skip_time)
            else:
                self.player.seekTime(self.player.getTime() + control.getInt('skipintro.time'))
            self.close()

        elif controlId == 3002:
            self.actioned = True
            self.close()

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()
