import threading
import time
import xbmc

from resources.lib.pages import nyaa, animetosho, nekobt, debrid_cloudfiles, localfiles, torrentio
from resources.lib.ui import control, database, source_utils
from resources.lib.windows.get_sources_window import GetSources
from resources.lib.windows import sort_select


def get_kodi_sources(mal_id, episode, media_type, rescrape=False, source_select=False, silent=False):
    import pickle
    from resources.lib.OtakuBrowser import BROWSER
    if not (show := database.get_show(mal_id)):
        show = BROWSER.get_anime(mal_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    actionArgs = {
        'name': kodi_meta['name'],
        'ename': kodi_meta['ename'],
        'synonyms': kodi_meta['synonyms'],
        'mal_id': mal_id,
        'episode': episode,
        'episodes': kodi_meta['episodes'],
        'status': kodi_meta['status'],
        'media_type': media_type,
        'rescrape': rescrape,
        'source_select': source_select,
        'silent': silent
    }
    sources = Sources('get_sources.xml', control.ADDON_PATH, actionArgs=actionArgs).doModal()
    return sources


class Sources(GetSources):
    def __init__(self, xml_file, location, actionArgs=None):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.terminate_on_cloud = control.getBool('general.terminate.oncloud')
        self.torrent_func = [animetosho, nyaa, nekobt, torrentio]
        self.torrentProviders = [x.__name__.replace('resources.lib.pages.', '') for x in self.torrent_func]
        self.otherProviders = ['Local Files', 'Cloud Inspection']
        self.remainingProviders = self.torrentProviders + self.otherProviders

        self.torrents_qual_len = [0, 0, 0, 0]
        self.embeds_qual_len = [0, 0, 0, 0]
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
        title = args['name']
        title_en = args['ename']
        titles = [title, title_en] + args.get('synonyms', [])
        titles = [title, title_en]
        mal_id = args['mal_id']
        episode = args['episode']
        episodes = args['episodes']
        status = args['status']
        media_type = args['media_type']
        rescrape = args['rescrape']
        # source_select = args['source_select']
        self.setProperty('process_started', 'true')

        if control.enabled_debrid():
            t = threading.Thread(target=self.user_cloud_inspection, args=(title, title_en, mal_id, episode))
            t.start()
            self.threads.append(t)
            for inx, torrent_provider in enumerate(self.torrentProviders):
                if control.getBool(f'provider.{torrent_provider}'):
                    t = threading.Thread(target=self.torrent_worker, args=(self.torrent_func[inx], torrent_provider, titles, mal_id, episode, status, media_type, episodes))
                    t.start()
                    self.threads.append(t)
                else:
                    self.remainingProviders.remove(torrent_provider)
        else:
            self.remainingProviders.remove('Cloud Inspection')
            for torrent_provider in self.torrentProviders:
                self.remainingProviders.remove(torrent_provider)

#       ###  Other ###
        if control.getBool('provider.localfiles'):
            t = threading.Thread(target=self.localfiles_worker, args=(titles, mal_id, episode, rescrape))
            t.start()
            self.threads.append(t)
        else:
            self.remainingProviders.remove('Local Files')

        timeout = 60 if rescrape else control.getInt('general.timeout')
        start_time = time.perf_counter()
        runtime = 0

        while runtime < timeout:
            if not self.silent:
                self.updateProgress()
                self.update_properties("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                    control.colorstr(self.torrents_qual_len[0] + self.embeds_qual_len[0]),
                    control.colorstr(self.torrents_qual_len[1] + self.embeds_qual_len[1]),
                    control.colorstr(self.torrents_qual_len[2] + self.embeds_qual_len[2]),
                    control.colorstr(self.torrents_qual_len[3] + self.embeds_qual_len[3])
                ))
            xbmc.sleep(500)
            if self.canceled or not self.remainingProviders or (self.terminate_on_cloud and self.cloud_files):
                break
            runtime = time.perf_counter() - start_time
            self.progress = runtime / timeout * 100

        if self.torrentSources or self.embedSources or self.cloud_files or self.local_files:
            self.return_data = self.sortSources()
        else:
            self.return_data = []
        self.close()
        return self.return_data

#   ### Torrents ###
    def torrent_worker(self, torrent_func, torrent_name, titles, mal_id, episode, status, media_type, episodes) -> None:
        cleaned_titles = (source_utils.clean_title(t) for t in titles)
        titles = list(dict.fromkeys(cleaned_titles))
        all_sources = torrent_func.Sources().get_sources(titles, mal_id, episode, status, media_type, episodes)
        self.torrentUnCacheSources += all_sources['uncached']
        self.torrentCacheSources += all_sources['cached']
        self.torrentSources += all_sources['cached'] + all_sources['uncached']
        self.remainingProviders.remove(torrent_name)

    def localfiles_worker(self, titles, mal_id, episode, rescrape) -> None:
        self.local_files += localfiles.Sources().get_sources(titles, mal_id, episode)
        self.remainingProviders.remove('Local Files')

    def user_cloud_inspection(self, title, title_en, mal_id, episode) -> None:
        self.cloud_files += debrid_cloudfiles.Sources().get_sources(title, title_en, episode)
        self.remainingProviders.remove('Cloud Inspection')

    def sortSources(self) -> list:
        all_list = self.torrentSources + self.embedSources + self.cloud_files + self.local_files
        sortedList = [x for x in all_list if control.getInt('general.minResolution') <= x['quality'] <= control.getInt('general.maxResolution')]

        # Filter out sources
        if control.getBool('general.disable265'):
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]
        lang = control.getInt("general.source") # 0 SUB, 1 BOTH, 2 DUB
        if lang != 1:
            sortedList = [i for i in sortedList if i['lang'] in [1, lang]]

        # Sort Sources
        SORT_METHODS = sort_select.SORT_METHODS
        sort_options = sort_select.sort_options
        for x in range(len(SORT_METHODS), 0, -1):
            reverse = sort_options[f'sortmethod.{x}.reverse']
            method = SORT_METHODS[int(sort_options[f'sortmethod.{x}'])]
            sortedList = getattr(sort_select, f'sort_by_{method}')(sortedList, not reverse)
        return sortedList

    def updateProgress(self) -> None:
        self.torrents_qual_len = [
            len([i for i in self.torrentSources if i['quality'] == 4]),
            len([i for i in self.torrentSources if i['quality'] == 3]),
            len([i for i in self.torrentSources if i['quality'] == 2]),
            len([i for i in self.torrentSources if i['quality'] == 1])
        ]

        self.embeds_qual_len = [
            len([i for i in self.embedSources if i['quality'] == 4]),
            len([i for i in self.embedSources if i['quality'] == 3]),
            len([i for i in self.embedSources if i['quality'] == 2]),
            len([i for i in self.embedSources if i['quality'] == 0])
        ]