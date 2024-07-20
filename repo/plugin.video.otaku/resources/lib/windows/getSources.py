from resources.lib.ui import control
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location, actionArgs)
        self.torrents_qual_len = [0, 0, 0, 0]
        self.embeds_qual_len = [0, 0, 0, 0]
        self.return_data = []

    def getSources(self, args):
        self.setProperty('process_started', 'true')
        self.update_properties("4K: %s | 1080: %s | 720: %s | SD: %s" % (
            control.colorstr(self.torrents_qual_len[0] + self.embeds_qual_len[0]),
            control.colorstr(self.torrents_qual_len[1] + self.embeds_qual_len[1]),
            control.colorstr(self.torrents_qual_len[2] + self.embeds_qual_len[2]),
            control.colorstr(self.torrents_qual_len[3] + self.embeds_qual_len[3]),
        ))
        self.close()
