import threading
import time
import xbmc

from resources.lib.pages import nyaa, animetosho, debrid_cloudfiles, hianime, gogoanime, animepahe, animix, aniwave, localfiles
from resources.lib.ui import control, database
from resources.lib.windows.get_sources_window import GetSources
from resources.lib.windows import sort_select


def get_kodi_sources(mal_id, episode, media_type, rescrape=False, source_select=False, silent=False):
    import pickle
    from resources.lib.OtakuBrowser import BROWSER
    if not (show := database.get_show(mal_id)):
        show = BROWSER.get_anime(mal_id)
    kodi_meta = pickle.loads(show['kodi_meta'])
    actionArgs = {
        'query': kodi_meta['query'],
        'mal_id': mal_id,
        'episode': episode,
        'status': kodi_meta['status'],
        'media_type': media_type,
        'rescrape': rescrape,
        'source_select': source_select,
        'silent': silent
    }
    sources_window = Sources('get_sources.xml', control.ADDON_PATH.as_posix(), actionargs=actionArgs)
    sources = sources_window.doModal()
    return sources


class Sources(GetSources):
    def __init__(self, xml_file, location, actionargs=None):
        super().__init__(xml_file, location, actionargs)
        self.torrent_func = [nyaa, animetosho]
        self.torrentProviders = [x.__name__.replace('resources.lib.pages.', '') for x in self.torrent_func]
        self.embed_func = [gogoanime, hianime, animepahe, animix, aniwave]
        self.embedProviders = [x.__name__.replace('resources.lib.pages.', '') for x in self.embed_func]
        self.otherProviders = ['Local Files', 'Cloud Inspection']
        self.remainingProviders = self.torrentProviders + self.embedProviders + self.otherProviders

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
        query = args['query']
        mal_id = args['mal_id']
        episode = args['episode']
        status = args['status']
        media_type = args['media_type']
        rescrape = args['rescrape']
        # source_select = args['source_select']
        self.setProperty('process_started', 'true')

        # set skipintro times to -1 before scraping
        control.setInt('hianime.skipintro.start', -1)
        control.setInt('hianime.skipintro.end', -1)
        control.setInt('aniwave.skipintro.start', -1)
        control.setInt('aniwave.skipintro.end', -1)

        # set skipoutro times to -1 before scraping
        control.setInt('hianime.skipoutro.start', -1)
        control.setInt('hianime.skipoutro.end', -1)
        control.setInt('aniwave.skipoutro.start', -1)
        control.setInt('aniwave.skipoutro.end', -1)

        if any(control.enabled_debrid().values()):
            t = threading.Thread(target=self.user_cloud_inspection, args=(query, mal_id, episode))
            t.start()
            self.threads.append(t)

            for inx, torrent_provider in enumerate(self.torrentProviders):
                if control.getBool(f'provider.{torrent_provider}'):
                    t = threading.Thread(target=self.torrent_worker, args=(self.torrent_func[inx], torrent_provider, query, mal_id, episode, status, media_type, rescrape))
                    t.start()
                    self.threads.append(t)
                else:
                    self.remainingProviders.remove(torrent_provider)
        else:
            self.remainingProviders.remove('Cloud Inspection')
            for torrent_provider in self.torrentProviders:
                self.remainingProviders.remove(torrent_provider)


#       ### embeds ###
        for inx, embed_provider in enumerate(self.embedProviders):
            if control.getBool(f'provider.{embed_provider}'):
                t = threading.Thread(target=self.embed_worker, args=(self.embed_func[inx], embed_provider, mal_id, episode, rescrape))
                t.start()
                self.threads.append(t)
            else:
                self.remainingProviders.remove(embed_provider)

#       ###  Other ###
        if control.getBool('provider.localfiles'):
            t = threading.Thread(target=self.localfiles_worker, args=(query, mal_id, episode, rescrape))
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

            if self.canceled or len(self.remainingProviders) < 1 and runtime > 5 or control.getBool('general.terminate.oncloud') and len(self.cloud_files) > 0:
                break
            runtime = time.perf_counter() - start_time
            self.progress = runtime / timeout * 100

        if len(self.torrentSources) + len(self.embedSources) + len(self.cloud_files) + len(self.local_files) == 0:
            self.return_data = []
        else:
            self.return_data = self.sortSources()
        self.close()
        return self.return_data

#   ### Torrents ###
    def torrent_worker(self, torrent_func, torrent_name, query, mal_id, episode, status, media_type, rescrape):
        try:
            all_sources = database.get_(torrent_func.Sources().get_sources, 8, query, mal_id, episode, status, media_type, rescrape, key=torrent_name)
        except Exception as e:
            control.log(repr(e), 'error')
            all_sources = {}
        if all_sources:
            self.torrentUnCacheSources += all_sources['uncached']
            self.torrentCacheSources += all_sources['cached']
            self.torrentSources += all_sources['cached'] + all_sources['uncached']
        self.remainingProviders.remove(torrent_name)

#   ### embeds ###
    def embed_worker(self, embed_func, embed_name, mal_id, episode, rescrape):
        try:
            embed_sources = database.get_(embed_func.Sources().get_sources, 8, mal_id, episode, key=embed_name)
        except Exception as e:
            control.log(repr(e), 'error')
            embed_sources = []
        if not isinstance(embed_sources, list):
            embed_sources = []
        self.embedSources += embed_sources
        if embed_name in ['hianime', 'aniwave']:
            for x in embed_sources:
                if x and x['skip'].get('intro') and x['skip']['intro']['start'] != 0:
                    control.setInt(f'{embed_name}.skipintro.start', int(x['skip']['intro']['start']))
                    control.setInt(f'{embed_name}.skipintro.end', int(x['skip']['intro']['end']))
                if x and x['skip'].get('outro') and x['skip']['outro']['start'] != 0:
                    control.setInt(f'{embed_name}.skipoutro.start', int(x['skip']['outro']['start']))
                    control.setInt(f'{embed_name}.skipoutro.end', int(x['skip']['outro']['end']))
        self.remainingProviders.remove(embed_name)

    def localfiles_worker(self, query, mal_id, episode, rescrape):
        self.local_files += localfiles.Sources().get_sources(query, mal_id, episode)
        self.remainingProviders.remove('Local Files')

    def user_cloud_inspection(self, query, mal_id, episode):
        debrid = {}
        if control.enabled_debrid()['rd'] and control.getBool('rd.cloudInspection'):
            debrid['real_debrid'] = True
        if control.enabled_debrid()['premiumize'] and control.getBool('premiumize.cloudInspection'):
            debrid['premiumize'] = True
        if control.enabled_debrid()['alldebrid'] and control.getBool('alldebrid.cloudInspection'):
            debrid['all_debrid'] = True
        if control.enabled_debrid()['torbox'] and control.getBool('torbox.cloudInspection'):
            debrid['torbox'] = True
        self.cloud_files += debrid_cloudfiles.Sources().get_sources(debrid, query, episode)
        self.remainingProviders.remove('Cloud Inspection')

    def sortSources(self):
        all_list = self.torrentSources + self.embedSources + self.cloud_files + self.local_files
        sortedList = [x for x in all_list if control.getInt('general.minResolution') <= x['quality'] <= control.getInt('general.maxResolution')]

        # Filter out sources
        if control.getBool('general.disable265'):
            sortedList = [i for i in sortedList if 'HEVC' not in i['info']]
        lang = control.getInt("general.source")
        if lang != 1:
            langs = [0, 1, 2]
            sortedList = [i for i in sortedList if i['lang'] != langs[lang]]

        # Sort Sources
        SORT_METHODS = sort_select.SORT_METHODS
        sort_options = sort_select.sort_options
        for x in range(len(SORT_METHODS), 0, -1):
            reverse = sort_options[f'sortmethod.{x}.reverse']
            method = SORT_METHODS[int(sort_options[f'sortmethod.{x}'])]
            sortedList = getattr(sort_select, f'sort_by_{method}')(sortedList, not reverse)
        return sortedList

    def updateProgress(self):
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
