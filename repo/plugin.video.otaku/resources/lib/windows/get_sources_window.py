import threading

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class GetSources(BaseWindow):

    def __init__(self, xml_file, xml_location, actionArgs=None):
        super(GetSources, self).__init__(xml_file, xml_location, actionArgs=actionArgs)

        self.setProperty('process_started', 'false')
        self.canceled = False
        self.return_data = None
        self.args = actionArgs
        self.progress = 0
        self.setProperty('progress', '0')
        self.silent = False
        control.closeBusyDialog()
        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.torrentCacheSources = []
        self.embedSources = []
        self.cloud_files = []
        self.remainingProviders = []
        self.remaining_providers_list = []

    def onInit(self):
        threading.Thread(target=self.getSources, args=[self.args]).start()

    def doModal(self):
        super(GetSources, self).doModal()
        return self.return_data

    def getSources(self, args):
        """
        Entry Point for initiating scraping
        :param args:
        :return:
        """

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:
            self.canceled = True

    def close(self):
        if not self.silent:
            control.dialogWindow.close(self)

    def setText(self, text=None):
        if self.silent:
            return
        if text:
            self.setProperty('notification_text', str(text))
        self.update_properties()

    def update_properties(self):

        self.setProperty('4k_sources', str(self.torrents_qual_len[0] + self.hosters_qual_len[0]))
        self.setProperty('1080p_sources', str(self.torrents_qual_len[1] + self.hosters_qual_len[1]))
        self.setProperty('720p_sources', str(self.torrents_qual_len[2] + self.hosters_qual_len[2]))
        self.setProperty('SD_sources', str(self.torrents_qual_len[3] + self.hosters_qual_len[3]))

        self.setProperty('total_torrents', str(len([i for i in self.torrentCacheSources])))
        self.setProperty('cached_torrents', str(len([i for i in self.torrentCacheSources])))
        self.setProperty('hosters_sources', str(len([i for i in self.embedSources])))
        self.setProperty('cloud_sources', str(len([i for i in self.cloud_files])))

        self.setProperty("remaining_providers_count", str((len(self.remainingProviders))))

        self.remaining_providers_list = self.getControl(2000)
        self.remaining_providers_list.reset()
        self.remaining_providers_list.addItems(self.remainingProviders)
        self.setProperty("remaining_providers_list", control.colorString(' | ').join([i.upper() for i in self.remainingProviders]))

    def setProgress(self):
        if not self.silent:
            self.setProperty('progress', str(self.progress))
