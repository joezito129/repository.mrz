import threading
import time

from resources.lib.pages import nyaa, animetosho, debrid_cloudfiles, nineanime, gogoanime, gogohd, animepahe, zoro, aniwatch, apahehd
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

        self.torrentCacheSources = []
        self.embedSources = []
        self.cloud_files = []
        self.torrentProviders = ['nyaa', 'animetosho']
        self.embedProviders = ['9anime', 'gogo', 'gogohd', 'animepahe', 'zoro', 'aniwatch', 'apahehd']
        self.remainingProviders = self.embedProviders + self.torrentProviders
        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.silent = False
        self.return_data = (None, None, None)
        self.progress = 1
        self.background_dialog = None
        self.nyaaSources = []
        self.animetoshoSources = []
        self.gogoSources = []
        self.gogohdSources = []
        self.nineSources = []
        self.animepaheSources = []
        self.zoroSources = []
        self.apahehdSources = []
        self.aniwatchSources = []
        self.threads = []
        self.usercloudSources = []
        self.terminate_on_cloud = control.getSetting('general.terminate.oncloud') == 'true'

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
        download = args['download']
        self.setProperty('process_started', 'true')

        if control.real_debrid_enabled() or control.all_debrid_enabled() or control.debrid_link_enabled() or control.premiumize_enabled():
            if control.getSetting('provider.nyaa') == 'true' or control.getSetting('provider.nyaaalt') == 'true':
                self.threads.append(
                    threading.Thread(target=self.nyaa_worker,
                                     args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('nyaa')

            if control.getSetting('provider.animetosho') == 'true':
                self.threads.append(
                threading.Thread(target=self.animetosho_worker,
                                 args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('animetosho')
        else:
            self.remainingProviders.remove('nyaa')
            self.remainingProviders.remove('animetosho')

        if not download:
            if control.getSetting('provider.gogo') == 'true':
                self.threads.append(
                    threading.Thread(target=self.gogo_worker, args=(anilist_id, episode, rescrape, get_backup)))
            else:
                self.remainingProviders.remove('gogo')

            if control.getSetting('provider.nineanime') == 'true':
                self.threads.append(
                    threading.Thread(target=self.nine_worker, args=(anilist_id, episode, rescrape)))
            else:
                self.remainingProviders.remove('9anime')

            if control.getSetting('provider.gogohd') == 'true':
                self.threads.append(
                    threading.Thread(target=self.gogohd_worker, args=(anilist_id, episode, rescrape)))
            else:
                self.remainingProviders.remove('gogohd')

            if control.getSetting('provider.animepahe') == 'true':
                self.threads.append(
                    threading.Thread(target=self.animepahe_worker, args=(anilist_id, episode, rescrape)))
            else:
                self.remainingProviders.remove('animepahe')

            if control.getSetting('provider.zoro') == 'true':
                self.threads.append(
                    threading.Thread(target=self.zoro_worker, args=(anilist_id, episode, rescrape)))
            else:
                self.remainingProviders.remove('zoro')

            if control.getSetting('provider.apahehd') == 'true':
                self.threads.append(
                    threading.Thread(target=self.apahehd_worker, args=(anilist_id, episode, rescrape)))
            else:
                self.remainingProviders.remove('apahehd')

            if control.getSetting('provider.aniwatch') == 'true':
                self.threads.append(
                    threading.Thread(target=self.aniwatch_worker, args=(anilist_id, episode, rescrape)))
            else:
                self.remainingProviders.remove('aniwatch')
        else:
            for embeds in self.embedProviders:
                self.remainingProviders.remove(embeds)

        cloud_thread = threading.Thread(target=self.user_cloud_inspection, args=(query, anilist_id, episode, media_type))
        cloud_thread.start()

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
            self.progress = runtime/timeout * 100

        # make sure cloud threads are finished before moving on
        cloud_thread.join()

        if len(self.torrentCacheSources) + len(self.embedSources) + len(self.cloud_files) == 0:
            self.return_data = []
            self.close()
            return

        sourcesList = self.sortSources(self.torrentCacheSources, self.embedSources, filter_lang)
        self.return_data = sourcesList

        self.close()

    def nyaa_worker(self, query, anilist_id, episode, status, media_type, rescrape):
        self.nyaaSources = nyaa.sources().get_sources(query, anilist_id, episode, status, media_type, rescrape)
        self.torrentCacheSources += self.nyaaSources
        self.remainingProviders.remove('nyaa')

    def animetosho_worker(self, query, anilist_id, episode, status, media_type, rescrape):
        self.animetoshoSources = animetosho.sources().get_sources(query, anilist_id, episode, status, media_type, rescrape)
        self.torrentCacheSources += self.animetoshoSources
        self.remainingProviders.remove('animetosho')

    def gogo_worker(self, anilist_id, episode, rescrape, get_backup):
        self.gogoSources = gogoanime.sources().get_sources(anilist_id, episode, get_backup)
        self.embedSources += self.gogoSources
        self.remainingProviders.remove('gogo')

    def gogohd_worker(self, anilist_id, episode, rescrape):
        self.gogohdSources = gogohd.sources().get_sources(anilist_id, episode)
        self.embedSources += self.gogohdSources
        self.remainingProviders.remove('gogohd')

    def nine_worker(self, anilist_id, episode, rescrape):
        self.nineSources = nineanime.sources().get_sources(anilist_id, episode)
        self.embedSources += self.nineSources
        self.remainingProviders.remove('9anime')

    def animepahe_worker(self, anilist_id, episode, rescrape):
        self.animepaheSources = animepahe.sources().get_sources(anilist_id, episode)
        self.embedSources += self.animepaheSources
        self.remainingProviders.remove('animepahe')

    def zoro_worker(self, anilist_id, episode, rescrape):
        self.zoroSources = zoro.sources().get_sources(anilist_id, episode)
        self.embedSources += self.zoroSources
        self.remainingProviders.remove('zoro')

    def apahehd_worker(self, anilist_id, episode, rescrape):
        self.apahehdSources = apahehd.sources().get_sources(anilist_id, episode)
        self.embedSources += self.apahehdSources
        self.remainingProviders.remove('apahehd')

    def aniwatch_worker(self, anilist_id, episode, rescrape):
        self.aniwatchSources = aniwatch.sources().get_sources(anilist_id, episode)
        self.embedSources += self.aniwatchSources
        self.remainingProviders.remove('aniwatch')

    def user_cloud_inspection(self, query, anilist_id, episode, media_type):
        self.remainingProviders.append('Cloud Inspection')

        debrid = {}
        if control.real_debrid_enabled() and control.getSetting('rd.cloudInspection') == 'true':
            debrid['real_debrid'] = True
        if control.premiumize_enabled() and control.getSetting('premiumize.cloudInspection') == 'true':
            debrid['premiumize'] = True

        self.usercloudSources = debrid_cloudfiles.sources().get_sources(debrid, query, episode)
        self.cloud_files += self.usercloudSources
        self.remainingProviders.remove('Cloud Inspection')

    @staticmethod
    def resolutionList():
        resolutions = []
        max_res = int(control.getSetting('general.maxResolution'))
        if max_res <= 3:
            resolutions.append('NA')
            resolutions.append('EQ')
        if max_res <= 2:
            resolutions.append('720p')
        if max_res <= 1:
            resolutions.append('1080p')
        if max_res <= 0:
            resolutions.append('4K')
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

    def sortSources(self, torrent_list, embed_list, filter_lang):
        sort_method = int(control.getSetting('general.sortsources'))
        sortedList = []
        resolutions = self.resolutionList()
        resolutions.reverse()

        if filter_lang:
            filter_lang = int(filter_lang)
            _torrent_list = torrent_list

            torrent_list = [i for i in _torrent_list if i['lang'] != filter_lang]
            embed_list = [i for i in embed_list if i['lang'] != filter_lang]

        debrid_priorities = self.debrid_priority()

        for resolution in resolutions:
            if sort_method == 0 or sort_method == 2:
                for debrid in debrid_priorities:
                    for torrent in torrent_list:
                        if debrid['slug'] == torrent['debrid_provider']:
                            if torrent['quality'] == resolution:
                                sortedList.append(torrent)

            if sort_method == 1 or sort_method == 2:
                for file in embed_list:
                    if file['quality'] == resolution:
                        sortedList.append(file)

        if sort_method == 1:
            for resolution in resolutions:
                for debrid in debrid_priorities:
                    for torrent in torrent_list:
                        if torrent['debrid_provider'] == debrid['slug']:
                            if torrent['quality'] == resolution:
                                sortedList.append(torrent)

        if sort_method == 0:
            for resolution in resolutions:
                for file in embed_list:
                    if file['quality'] == resolution:
                        sortedList.append(file)

        if control.getSetting('general.disable265') == 'true':
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]

        sort_option = control.getSetting('general.sourcesort')
        if sort_option == 'Sub':
            sortedList = sorted(sortedList, key=lambda x: x['lang'] == 0, reverse=True)
        elif sort_option == 'Dub':
            sortedList = sorted(sortedList, key=lambda x: x['lang'] > 0, reverse=True)

        preferences = control.getSetting("general.source")

        for cloud_file in self.cloud_files:
            sortedList.insert(0, cloud_file)

        lang_preferences = {'Dub': 0, 'Sub': 2}
        if preferences in lang_preferences:
            sortedList = [i for i in sortedList if i['lang'] != lang_preferences[preferences]]

        return sortedList

    def updateProgress(self):

        list1 = [
            len([i for i in self.nyaaSources if i['quality'] == '4K']),
            len([i for i in self.nyaaSources if i['quality'] == '1080p']),
            len([i for i in self.nyaaSources if i['quality'] == '720p']),
            len([i for i in self.nyaaSources if i['quality'] == 'NA']),
        ]

        self.torrents_qual_len = list1

        list2 = [
            len([i for i in self.embedSources if i['quality'] == '4K']),
            len([i for i in self.embedSources if i['quality'] == '1080p']),
            len([i for i in self.embedSources if i['quality'] == '720p']),
            len([i for i in self.embedSources if i['quality'] == 'NA']),
        ]

        self.hosters_qual_len = list2