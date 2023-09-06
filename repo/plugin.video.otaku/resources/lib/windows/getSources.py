from resources.lib.ui import control
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        super(Sources, self).__init__(xml_file, location, actionArgs)
        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.silent = False
        self.return_data = (None, None, None)
        self.progress = 1

    def getSources(self, args):
        self.setProperty('process_started', 'true')
        self.progress = 50
        self.setProgress()
        self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
            control.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
            control.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
            control.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
            control.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
        ))
        self.close()
