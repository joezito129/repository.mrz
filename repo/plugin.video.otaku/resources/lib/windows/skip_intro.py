import xbmc

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class SkipIntro(BaseWindow):

    def __init__(self, xml_file, xml_location, actionArgs=None):
        super(SkipIntro, self).__init__(xml_file, xml_location, actionArgs=actionArgs)
        self.player = control.player()
        self.total_time = int(self.player.getTotalTime())
        self.playing_file = self.player.getPlayingFile()
        self.skip_time = int(control.getSetting('skipintro.time'))
        self.close_durration = int(control.getSetting('skipintro.duration')) * 60
        self.closed = False
        self.actioned = None
        self.current_time = None
        self.skipintro_start_skip_time = None
        self.skipintro_end_skip_time = None
    
    def onInit(self):
        self.background_tasks()

    def background_tasks(self):
        self.skipintro_start_skip_time = int(control.getSetting('skipintro.start.skip.time'))
        self.skipintro_end_skip_time = int(control.getSetting('skipintro.end.skip.time'))

        self.current_time = int(self.player.getTime())
        while self.total_time - self.current_time > 2 and not self.closed and self.playing_file == self.player.getPlayingFile():
            self.current_time = int(self.player.getTime())
            if self.current_time > self.skipintro_end_skip_time:
                self.close()
                break
            elif self.current_time > self.close_durration > 0 and self.skipintro_end_skip_time == 9999:
                self.close()
                break
            xbmc.sleep(500)
        self.close()

    def doModal(self):
        super(SkipIntro, self).doModal()

    def close(self):
        self.closed = True
        super(SkipIntro, self).close()

    def onClick(self, controlId):
        self.handle_action(controlId)

    def handle_action(self, controlId):
        if controlId == 3001:
            self.actioned = True
            if self.skipintro_end_skip_time == 9999:
                self.player.seekTime(int(self.player.getTime()) + self.skip_time)
            else:
                self.player.seekTime(self.skipintro_end_skip_time)
            self.close()

        if controlId == 3002:
            self.actioned = True
            self.close()

    def onAction(self, action):

        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()

        if actionID == 7:
            self.handle_action(actionID)
