import threading
import time

from resources.lib.pages import (nyaa, animetosho, debrid_cloudfiles, hianime, animess, animixplay, aniplay, aniwave, gogoanime, localfiles)
from resources.lib.ui import control
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow


def getSourcesHelper(actionArgs):
    sources_window = Sources(*('get_sources.xml', control.ADDON_PATH), actionArgs=actionArgs)
    sources = sources_window.doModal()
    del sources_window
    return sources


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        super(Sources, self).__init__(xml_file, location, actionArgs)

        self.torrentProviders = ['nyaa', 'animetosho', 'Cloud Inspection']
        self.embedProviders = ['animess', 'animixplay', 'aniplay', 'aniwave', 'gogo', 'hianime']
        self.otherProviders = ['Local Files']
        self.remainingProviders = self.embedProviders + self.torrentProviders + self.otherProviders

        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.silent = False
        self.return_data = (None, None, None)
        self.progress = 1
        self.threads = []

        self.cloud_files = []
        self.terminate_on_cloud = control.getSetting('general.terminate.oncloud') == 'true'

        self.torrentSources = []
        self.torrentCacheSources = []
        self.embedSources = []
        self.usercloudSources = []
        self.local_files = []

    def getSources(self, args):
        query = args['query']
        anilist_id = args['anilist_id']
        episode = args['episode']
        status = args['status']
        filter_lang = args['filter_lang']
        media_type = args['media_type']
        rescrape = args['rescrape']
        # source_select = args['source_select']
        get_backup = args['get_backup']
        self.setProperty('process_started', 'true')

        if control.real_debrid_enabled() or control.all_debrid_enabled() or control.debrid_link_enabled() or control.premiumize_enabled():
            self.threads.append(threading.Thread(target=self.user_cloud_inspection, args=(query, anilist_id, episode, media_type)))

            if control.getSetting('provider.nyaa') == 'true' or control.getSetting('provider.nyaaalt') == 'true':
                self.threads.append(threading.Thread(target=self.nyaa_worker, args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('nyaa')

            if control.getSetting('provider.animetosho') == 'true':
                self.threads.append(threading.Thread(target=self.animetosho_worker, args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('animetosho')
        else:
            for provider in self.torrentProviders:
                self.remainingProviders.remove(provider)

#       ###  Other ###
        if control.getSetting('provider.localfiles') == 'true':
            self.threads.append(threading.Thread(target=self.localfiles_worker, args=(query, anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('Local Files')

#       ### embeds ###
        if control.getSetting('provider.hianime') == 'true':
            self.threads.append(threading.Thread(target=self.hianime_worker, args=(anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('hianime')

        if control.getSetting('provider.animess') == 'true':
            self.threads.append(threading.Thread(target=self.animess_worker, args=(anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('animess')

        if control.getSetting('provider.animixplay') == 'true':
            self.threads.append(threading.Thread(target=self.animixplay_worker, args=(anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('animixplay')

        if control.getSetting('provider.aniplay') == 'true':
            self.threads.append(threading.Thread(target=self.aniplay_worker, args=(anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('aniplay')

        if control.getSetting('provider.aniwave') == 'true':
            self.threads.append(threading.Thread(target=self.aniwave_worker, args=(anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('aniwave')

        if control.getSetting('provider.gogo') == 'true':
            self.threads.append(threading.Thread(target=self.gogo_worker, args=(anilist_id, episode, rescrape, get_backup)))
        else:
            self.remainingProviders.remove('gogo')

        for thread in self.threads:
            thread.start()

        timeout = 60 if rescrape else int(control.getSetting('general.timeout'))
        start_time = time.perf_counter()
        runtime = 0

        while runtime < timeout:
            if self.canceled or len(self.remainingProviders) < 1 and runtime > 5 or \
                    self.terminate_on_cloud and len(self.cloud_files) > 0:
                self.updateProgress()
                self.setProgress()
                self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                    control.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
                    control.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
                    control.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
                    control.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
                ))
                time.sleep(.5)
                break
            self.updateProgress()
            self.setProgress()
            self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                control.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
                control.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
                control.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
                control.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
            ))

            # Update Progress
            time.sleep(.5)
            runtime = time.perf_counter() - start_time
            self.progress = runtime / timeout * 100

        if len(self.torrentCacheSources) + len(self.embedSources) + len(self.cloud_files) + len(self.local_files) == 0:
            self.return_data = []
            self.close()
            return

        sourcesList = self.sortSources(self.torrentCacheSources, self.embedSources, self.local_files, filter_lang)
        self.return_data = sourcesList
        self.close()

    def nyaa_worker(self, query, anilist_id, episode, status, media_type, rescrape):
        self.torrentCacheSources += nyaa.sources().get_sources(query, anilist_id, episode, status, media_type, rescrape)
        self.remainingProviders.remove('nyaa')

    def animetosho_worker(self, query, anilist_id, episode, status, media_type, rescrape):
        self.torrentCacheSources += animetosho.sources().get_sources(query, anilist_id, episode, status, media_type, rescrape)
        self.remainingProviders.remove('animetosho')

#   ### embeds ###
    def hianime_worker(self, anilist_id, episode, rescrape):
        self.embedSources += hianime.sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('hianime')

    def animess_worker(self, anilist_id, episode, rescrape):
        self.embedSources += animess.sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('animess')

    def animixplay_worker(self, anilist_id, episode, rescrape):
        self.embedSources += animixplay.sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('animixplay')

    def aniplay_worker(self, anilist_id, episode, rescrape):
        self.embedSources += aniplay.sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('aniplay')

    def aniwave_worker(self, anilist_id, episode, rescrape):
        self.embedSources += aniwave.sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('aniwave')

    def gogo_worker(self, anilist_id, episode, rescrape, get_backup):
        self.embedSources += gogoanime.sources().get_sources(anilist_id, episode, get_backup)
        self.remainingProviders.remove('gogo')

    def localfiles_worker(self, query, anilist_id, episode, rescrape):
        if not rescrape:
            self.local_files += localfiles.sources().get_sources(query, anilist_id, episode)
        self.remainingProviders.remove('Local Files')

    def user_cloud_inspection(self, query, anilist_id, episode, media_type):
        debrid = {}
        if control.real_debrid_enabled() and control.getSetting('rd.cloudInspection') == 'true':
            debrid['real_debrid'] = True
        if control.premiumize_enabled() and control.getSetting('premiumize.cloudInspection') == 'true':
            debrid['premiumize'] = True
        if control.all_debrid_enabled() and control.getSetting('alldebrid.cloudInspection') == 'true':
            debrid['alldebrid'] = True
        self.cloud_files += debrid_cloudfiles.sources().get_sources(debrid, query, episode)
        self.remainingProviders.remove('Cloud Inspection')

    @staticmethod
    def resolutionList():
        max_res = int(control.getSetting('general.maxResolution'))
        if max_res == 4:
            resolutions = ['EQ', '480p', '720p', '1080p', '4k']
        elif max_res == 3:
            resolutions = ['EQ', '480p', '720p', '1080p']
        elif max_res == 2:
            resolutions = ['EQ', '480p', '720p']
        elif max_res == 1:
            resolutions = ['EQ', '480p']
        else:
            resolutions = ['EQ']
        return resolutions

    @staticmethod
    def debrid_priority():
        p = []
        if control.getSetting('premiumize.enabled') == 'true':
            p.append({'slug': 'premiumize', 'priority': int(control.getSetting('premiumize.priority'))})
        if control.getSetting('realdebrid.enabled') == 'true':
            p.append({'slug': 'real_debrid', 'priority': int(control.getSetting('rd.priority'))})
        if control.getSetting('alldebrid.enabled') == 'true':
            p.append({'slug': 'all_debrid', 'priority': int(control.getSetting('alldebrid.priority'))})
        if control.getSetting('dl.enabled') == 'true':
            p.append({'slug': 'debrid_link', 'priority': int(control.getSetting('dl.priority'))})
        p.append({'slug': '', 'priority': 11})
        p = sorted(p, key=lambda i: i['priority'])
        return p

    def sortSources(self, torrent_list, embed_list, other_list, filter_lang):
        sort_method = int(control.getSetting('general.sortsources'))
        sortedList = []
        resolutions = self.resolutionList()
        debrid_priorities = self.debrid_priority()

        for resolution in resolutions:
            if sort_method == 0:
                for debrid in debrid_priorities:
                    for torrent in torrent_list:
                        if debrid['slug'] == torrent['debrid_provider']:
                            if torrent['quality'] == resolution:
                                sortedList.append(torrent)

            elif sort_method == 1:
                for file in embed_list:
                    if file['quality'] == resolution:
                        sortedList.append(file)
        if sort_method == 0:
            for resolution in resolutions:
                for file in embed_list:
                    if file['quality'] == resolution:
                        sortedList.append(file)

        elif sort_method == 1:
            for resolution in resolutions:
                for debrid in debrid_priorities:
                    for torrent in torrent_list:
                        if torrent['debrid_provider'] == debrid['slug']:
                            if torrent['quality'] == resolution:
                                sortedList.append(torrent)

        if control.getSetting('general.disable265') == 'true':
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]

        sort_option = int(control.getSetting('general.sourcesort'))
        if sort_option == 2:
            sortedList = sorted(sortedList, key=lambda x: x['lang'] == 0, reverse=True)
        elif sort_option == 0:
            sortedList = sorted(sortedList, key=lambda x: x['lang'] > 0, reverse=True)

        lang = int(control.getSetting("general.source"))

        for cloud_file in self.cloud_files:
            sortedList.insert(0, cloud_file)

        for other in other_list:
            sortedList.insert(0, other)

        if lang != 1:
            langs = [0, 1, 2]
            sortedList = [i for i in sortedList if i['lang'] != langs[lang]]
        return sortedList

    def updateProgress(self):
        list1 = [
            len([i for i in self.torrentSources if i['quality'] == '4K']),
            len([i for i in self.torrentSources if i['quality'] == '1080p']),
            len([i for i in self.torrentSources if i['quality'] == '720p']),
            len([i for i in self.torrentSources if i['quality'] == '480p']),
        ]

        self.torrents_qual_len = list1
        list2 = [
            len([i for i in self.embedSources if i['quality'] == '4K']),
            len([i for i in self.embedSources if i['quality'] == '1080p']),
            len([i for i in self.embedSources if i['quality'] == '720p']),
            len([i for i in self.embedSources if i['quality'] == 'EQ']),
        ]

        self.hosters_qual_len = list2
