import requests
import xbmcgui
import xbmcplugin
import xbmc

from urllib import parse
from resources.lib.WatchlistIntegration import watchlist_update_episode
from resources.lib.debrid import all_debrid, debrid_link, premiumize, real_debrid, torbox
from resources.lib.ui import control, source_utils, player
from resources.lib.windows.base_window import BaseWindow


class HookMimetype:
    __MIME_HOOKS = {}

    @classmethod
    def trigger(cls, mimetype, item):
        if mimetype in cls.__MIME_HOOKS.keys():
            return cls.__MIME_HOOKS[mimetype](item)
        return item

    def __init__(self, mimetype):
        self._type = mimetype

    def __call__(self, func):
        assert self._type not in self.__MIME_HOOKS.keys()
        self.__MIME_HOOKS[self._type] = func
        return func


class Resolver(BaseWindow):
    def __init__(self, xml_file, location, *, actionArgs=None, source_select=False):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.return_data = {
            'link': None,
            'linkinfo': None,
            'source': None
        }
        self.canceled = False
        self.sources = None
        self.args = None
        self.resolvers = {
            'all_debrid': all_debrid.AllDebrid,
            'debrid_link': debrid_link.DebridLink,
            'premiumize': premiumize.Premiumize,
            'real_debrid': real_debrid.RealDebrid,
            'torbox': torbox.Torbox
        }
        self.source_select = source_select
        self.pack_select = False
        self.mal_id = actionArgs['mal_id']
        self.episode = int(actionArgs.get('episode', 1))
        self.play = actionArgs.get('play')
        self.source_select_close = actionArgs.get('close')
        self.resume = actionArgs.get('resume')
        self.context = actionArgs.get('context')
        self.silent = actionArgs.get('silent')
        self.params = actionArgs.get('params', {})
        self.abort = False

    def onInit(self):
        self.resolve(self.sources)

    def resolve(self, sources):
        # last played source move to top of list
        if len(sources) > 1 and not self.source_select:
            last_played = control.getSetting('last_played')
            for index, source in enumerate(sources):
                if str(source['release_title']) == last_played:
                    sources.insert(0, sources.pop(index))
                    break

        # Begin resolving links
        for i in sources:
            self.return_data['source'] = i
            if self.canceled:
                break
            debrid_provider = i.get('debrid_provider', 'None').replace('_', ' ')
            self.setProperty('debrid_provider', debrid_provider)
            self.setProperty('source_provider', i['provider'])
            self.setProperty('release_title', str(i['release_title']))
            self.setProperty('source_resolution', source_utils.res[i['quality']])
            self.setProperty('source_info', " ".join(i['info']))
            self.setProperty('source_type', i['type'])

            if 'uncached' in i['type']:
                self.return_data['link'] = self.resolve_uncache(i)
                break

            if i['type'] in ['torrent', 'cloud', 'hoster']:
                stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i)
                if stream_link:
                    self.return_data['link'] = stream_link
                    break

            elif i['type'] == 'direct':
                stream_link = i['hash']
                if stream_link:
                    self.return_data['link'] = stream_link
                    if i.get('subs'):
                        self.return_data['link'] = stream_link
                        self.return_data['sub'] = i['subs']
                    break

            elif i['type'] == 'embed':
                from resources.lib.ui import embed_extractor
                stream_link = embed_extractor.load_video_from_url(i['hash'])
                if stream_link:
                    self.return_data['link'] = stream_link
                    break

            elif i['type'] == 'local_files':
                stream_link = i['hash']
                self.return_data = {
                    'url': stream_link,
                    'local': True,
                    'headers': {}
                }
                break

        if self.return_data.get('local'):
            self.return_data['linkinfo'] = self.return_data
        else:
            self.return_data['linkinfo'] = self.prefetch_play_link(self.return_data['link'])

        if not self.return_data['linkinfo']:
            self.return_data = False
        if self.play and isinstance(self.return_data, dict):
            if self.source_select_close:
                self.source_select_close()
            linkInfo = self.return_data['linkinfo']

            item = xbmcgui.ListItem(path=linkInfo['url'], offscreen=False)
            if self.return_data.get('sub'):
                from resources.lib.ui import embed_extractor
                embed_extractor.del_subs()
                subtitles = []
                for sub in self.return_data['sub']:
                    sub_url = sub.get('url')
                    sub_lang = sub.get('lang')
                    subtitles.append(embed_extractor.get_sub(sub_url, sub_lang))
                item.setSubtitles(subtitles)

            if linkInfo['headers'].get('Content-Type'):
                item.setProperty('MimeType', linkInfo['headers']['Content-Type'])
                # Run any mimetype hook
                item = HookMimetype.trigger(linkInfo['headers']['Content-Type'], item)

            if self.context:
                control.set_videotags(item, self.params)
                art = {
                    'tvshow.poster': self.params.get('tvshow.poster'),
                    'thumb': self.params.get('thumb')
                }
                item.setArt(art)
                control.playList.add(linkInfo['url'], item)
                xbmc.Player().play(control.playList, item)
            else:
                xbmcplugin.setResolvedUrl(control.HANDLE, True, item)
            monitor = Monitor()
            for _ in range(30):
                if monitor.waitForAbort(1) or monitor.playbackerror or monitor.abortRequested():
                    xbmcplugin.setResolvedUrl(control.HANDLE, False, item)
                    control.playList.clear()
                    self.abort = True
                    break
                if monitor.playing:
                    break
            else:
                control.log('no xbmc playing source found; Continuing code', 'warning')
            del monitor
            self.close()
            if not self.abort:
                player.WatchlistPlayer().handle_player(self.mal_id, watchlist_update_episode, self.episode, self.resume, self.params.get('path', ''), self.context)
        else:
            self.close()

    def resolve_source(self, api, source):
        api = api()
        hash_ = source['hash']
        magnet = f"magnet:?xt=urn:btih:{hash_}"
        stream_link = {}
        if source['type'] == 'torrent':
            stream_link = api.resolve_single_magnet(hash_, magnet, source['episode_re'], self.pack_select)
        elif source['type'] == 'cloud' or source['type'] == 'hoster':
            hash_ = api.resolve_cloud(source, self.pack_select)
            if hash_:
                stream_link = api.resolve_hoster(hash_)
        return stream_link

    @staticmethod
    def prefetch_play_link(link):
        if not link:
            return
        url = link
        if '|' in url:
            url, hdrs = link.split('|')
            headers = dict([item.split('=') for item in hdrs.split('&')])
            for header in headers:
                headers[header] = parse.unquote_plus(headers[header])
        else:
            headers = None
        try:
            r = requests.get(url, headers=headers, stream=True)
        except requests.exceptions.SSLError:
            yesno = control.yesno_dialog(f'{control.ADDON_NAME}: Request Error',
                                         f'{url}\nWould you like to try without verifying TLS certificate?')
            if yesno == 1:
                r = requests.get(url, headers=headers, stream=True, verify=False)
            else:
                return
        except Exception as e:
            control.log(repr(e), level='warning')
            return

        return {
            "url": link if '|' in link else r.url,
            "headers": r.headers
        }

    def resolve_uncache(self, source):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        f_string = (f"[I]{source['release_title']}[/I][CR]"
                    f"[CR]"
                    f"This source is not cached would you like to cache it now?")
        if not control.getBool('uncached.autoruninforground'):
            yesnocustom = control.yesnocustom_dialog(heading, f_string, "Cancel", "Run in Background", "Run in Forground")
            if yesnocustom == -1 or yesnocustom == 2:
                self.canceled = True
                return
            if yesnocustom == 0:
                runbackground = True
            elif yesnocustom == 1:
                runbackground = False
            else:
                return
        else:
            runbackground = False
        api = self.resolvers[source['debrid_provider']]()
        try:
            resolved_cache = api.resolve_uncached_source(source, runbackground)
        except Exception as e:
            control.progressDialog.close()
            import traceback
            control.ok_dialog(control.ADDON_NAME, f'error; {e}')
            control.log(traceback.format_exc(), 'error')
            return
        if not resolved_cache:
            self.canceled = True
        return resolved_cache

    def doModal(self, sources, args, pack_select) -> any:
        self.sources = sources
        if self.sources:
            self.args = args
            self.pack_select = pack_select
            self.setProperty('release_title', str(self.sources[0]['release_title']))
            self.setProperty('debrid_provider', self.sources[0].get('debrid_provider', 'None').replace('_', ' '))
            self.setProperty('source_provider', self.sources[0]['provider'])
            self.setProperty('source_resolution', source_utils.res[self.sources[0]['quality']])
            self.setProperty('source_info', " ".join(self.sources[0]['info']))
            self.setProperty('source_type', self.sources[0]['type'])
            self.setProperty('source_size', self.sources[0]['size'])
            self.setProperty('source_seeders', str(self.sources[0].get('seeders', '')))
            if self.silent:
                if self.source_select_close:
                    self.source_select_close()
                self.resolve(sources)
            else:
                super(Resolver, self).doModal()
            control.setSetting('last_played', self.sources[0]['release_title'])
        return self.return_data

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.canceled = True
            self.close()

@HookMimetype('application/dash+xml')
def _DASH_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('mpd')
    if is_helper.check_inputstream():
        item.setProperty('inputstream', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        item.setContentLookup(False)
    else:
        raise Exception("InputStream Adaptive is not supported.")
    return item


@HookMimetype('application/vnd.apple.mpegurl')
def _HLS_HOOK(item):
    stream_url = item.getPath()
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('hls')
    if '|' not in stream_url and is_helper.check_inputstream():
        item.setProperty('inputstream', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    item.setProperty('MimeType', 'application/vnd.apple.mpegurl')
    item.setMimeType('application/vnd.apple.mpegstream_url')
    item.setContentLookup(False)
    return item

class Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.playbackerror = False
        self.playing = False

    def onNotification(self, sender, method, data):
        if method == 'Player.OnAVStart':
            self.playing = True
        elif method == 'Player.OnStop':
            self.playbackerror = True