import threading
import time
import xbmc

from resources.lib.pages import (nyaa, animetosho, debrid_cloudfiles, hianime, animess, animixplay, aniwave, gogoanime, localfiles)
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
        self.embedProviders = ['animess', 'animixplay', 'aniwave', 'gogo', 'hianime']
        self.otherProviders = ['Local Files']
        self.remainingProviders = self.embedProviders + self.torrentProviders + self.otherProviders

        self.torrents_qual_len = [0, 0, 0, 0]
        self.embeds_qual_len = [0, 0, 0, 0]
        self.silent = False
        self.return_data = []
        self.progress = 1
        self.threads = []

        self.cloud_files = []

        self.torrentSources = []
        self.torrentCacheSources = []
        self.torrentUnCacheSources = []
        self.embedSources = []
        self.usercloudSources = []
        self.local_files = []

    def getSources(self, args):
        query = args['query']
        anilist_id = args['anilist_id']
        episode = args['episode']
        status = args['status']
        media_type = args['media_type']
        rescrape = args['rescrape']
        # source_select = args['source_select']
        get_backup = args['get_backup']
        self.setProperty('process_started', 'true')

        if control.real_debrid_enabled() or control.all_debrid_enabled() or control.debrid_link_enabled() or control.premiumize_enabled():
            self.threads.append(threading.Thread(target=self.user_cloud_inspection, args=(query, anilist_id, episode, media_type)))

            if control.getSetting('provider.nyaa') == 'true':
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
            self.updateProgress()
            self.setProgress()
            self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                control.colorString(self.torrents_qual_len[0] + self.embeds_qual_len[0]),
                control.colorString(self.torrents_qual_len[1] + self.embeds_qual_len[1]),
                control.colorString(self.torrents_qual_len[2] + self.embeds_qual_len[2]),
                control.colorString(self.torrents_qual_len[3] + self.embeds_qual_len[3])
            ))
            xbmc.sleep(500)

            if self.canceled or len(self.remainingProviders) < 1 and runtime > 5 or control.bools.terminateoncloud and len(self.cloud_files) > 0:
                break
            runtime = time.perf_counter() - start_time
            self.progress = runtime / timeout * 100

        if len(self.torrentSources) + len(self.embedSources) + len(self.cloud_files) + len(self.local_files) == 0:
            self.return_data = []
        else:
            self.return_data = self.sortSources(self.torrentSources, self.embedSources, self.cloud_files, self.local_files)
        self.close()
        return self.return_data

    def nyaa_worker(self, query, anilist_id, episode, status, media_type, rescrape):
        all_sources = nyaa.Sources().get_sources(query, anilist_id, episode, status, media_type, rescrape)
        self.torrentUnCacheSources += all_sources['uncached']
        self.torrentCacheSources += all_sources['cached']
        self.torrentSources += all_sources['cached'] + all_sources['uncached']
        self.remainingProviders.remove('nyaa')

    def animetosho_worker(self, query, anilist_id, episode, status, media_type, rescrape):
        all_sources = animetosho.Sources().get_sources(query, anilist_id, episode, status, media_type, rescrape)
        self.torrentUnCacheSources += all_sources['uncached']
        self.torrentCacheSources += all_sources['cached']
        self.torrentSources += all_sources['cached'] + all_sources['uncached']
        self.remainingProviders.remove('animetosho')

#   ### embeds ###
    def hianime_worker(self, anilist_id, episode, rescrape):
        self.embedSources += hianime.Sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('hianime')

    def animess_worker(self, anilist_id, episode, rescrape):
        self.embedSources += animess.Sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('animess')

    def animixplay_worker(self, anilist_id, episode, rescrape):
        self.embedSources += animixplay.Sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('animixplay')

    def aniwave_worker(self, anilist_id, episode, rescrape):
        self.embedSources += aniwave.Sources().get_sources(anilist_id, episode)
        self.remainingProviders.remove('aniwave')

    def gogo_worker(self, anilist_id, episode, rescrape, get_backup):
        self.embedSources += gogoanime.Sources().get_sources(anilist_id, episode, get_backup)
        self.remainingProviders.remove('gogo')

    def localfiles_worker(self, query, anilist_id, episode, rescrape):
        if not rescrape:
            self.local_files += localfiles.Sources().get_sources(query, anilist_id, episode)
        self.remainingProviders.remove('Local Files')

    def user_cloud_inspection(self, query, anilist_id, episode, media_type):
        debrid = {}
        if control.real_debrid_enabled() and control.getSetting('rd.cloudInspection') == 'true':
            debrid['real_debrid'] = True
        if control.premiumize_enabled() and control.getSetting('premiumize.cloudInspection') == 'true':
            debrid['premiumize'] = True
        if control.all_debrid_enabled() and control.getSetting('alldebrid.cloudInspection') == 'true':
            debrid['all_debrid'] = True
        self.cloud_files += debrid_cloudfiles.Sources().get_sources(debrid, query, episode)
        self.remainingProviders.remove('Cloud Inspection')

    @staticmethod
    def resolutionList():
        max_res = int(control.getSetting('general.maxResolution'))
        if max_res == 4:
            resolutions = ['4k', '1080p', '720p', '480p', 'EQ']
        elif max_res == 3:
            resolutions = ['1080p', '720p', '480p', 'EQ']
        elif max_res == 2:
            resolutions = ['720p', '480p', 'EQ']
        elif max_res == 1:
            resolutions = ['480p', 'EQ']
        else:
            resolutions = ['EQ']
        return resolutions

    def sortSources(self, torrent_list, embed_list, cloud_files, other_list):
        sortedList = []
        resolutions = self.resolutionList()

        for resolution in resolutions:
            # for cloud_file in cloud_files:
            #     if cloud_file['quality'] == resolution:
            #         sortedList.append(cloud_file)

            # for other in other_list:
            #     if other['quality'] == resolution:
            #         sortedList.append(other)

            for torrent in torrent_list:
                if torrent['quality'] == resolution:
                    sortedList.append(torrent)

            for file in embed_list:
                if file['quality'] == resolution:
                    sortedList.append(file)

        if control.getSetting('general.disable265') == 'true':
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]

        sort_type = int(control.getSetting('general.sortsources'))  # torrents=0; embeds=1\
        if sort_type == 0:
            sortedList = sorted(sortedList, key=lambda x: x['type'] in ['torrent'], reverse=True)
        elif sort_type == 1:
            sortedList = sorted(sortedList, key=lambda x: x['type'] in ['embed', 'direct'], reverse=True)

        sort_lang = int(control.getSetting('general.sourcesort'))   # dub=0; None=1; sub=1
        if sort_lang == 2:
            sortedList = sorted(sortedList, key=lambda x: x['lang'] == 0, reverse=True)
        elif sort_lang == 0:
            sortedList = sorted(sortedList, key=lambda x: x['lang'] > 0, reverse=True)

        for cloud_file in cloud_files:
            sortedList.insert(0, cloud_file)

        for other in other_list:
            sortedList.insert(0, other)

        lang = int(control.getSetting("general.source"))
        if lang != 1:
            langs = [0, 1, 2]
            sortedList = [i for i in sortedList if i['lang'] != langs[lang]]
        return sortedList

    def updateProgress(self):
        self.torrents_qual_len = [
            len([i for i in self.torrentSources if i['quality'] == '4K']),
            len([i for i in self.torrentSources if i['quality'] == '1080p']),
            len([i for i in self.torrentSources if i['quality'] == '720p']),
            len([i for i in self.torrentSources if i['quality'] == '480p'])
        ]
        self.embeds_qual_len = [
            len([i for i in self.embedSources if i['quality'] == '4K']),
            len([i for i in self.embedSources if i['quality'] == '1080p']),
            len([i for i in self.embedSources if i['quality'] == '720p']),
            len([i for i in self.embedSources if i['quality'] == 'EQ'])
        ]
