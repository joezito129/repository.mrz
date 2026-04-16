import json

import requests
import xbmcgui
import xbmcplugin
import xbmc

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
    def __init__(self, xml_file, location, *, actionArgs=None):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.return_data = {}
        self.canceled = False
        self.sources = None
        self.resolvers = {
            'all_debrid': all_debrid.AllDebrid,
            'debrid_link': debrid_link.DebridLink,
            'premiumize': premiumize.Premiumize,
            'real_debrid': real_debrid.RealDebrid,
            'torbox': torbox.Torbox
        }
        self.mal_id = actionArgs['mal_id']
        self.episode = actionArgs.get('episode', 1)
        self.source_select = actionArgs.get('source_select')
        self.pack_select = actionArgs.get('pack_select')
        self.play = actionArgs.get('play')
        self.source_select_close = actionArgs.get('close')
        self.resume = actionArgs.get('resume')
        self.context = actionArgs.get('context')
        self.silent = actionArgs.get('silent')
        self.abort = False

    def onInit(self):
        self.resolve(self.sources)

    def resolve(self, sources):
        # last played source move to top of list
        if len(sources) > 1 and not self.source_select:
            last_played = control.getString('last_played')
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

            if i['type'] in ['torrent', 'cloud', 'hoster', 'torrentio']:
                stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i)
                if stream_link:
                    self.return_data['link'] = stream_link
                    break

            elif i['type'] in ['local_files']:
                stream_link = i['link']
                if stream_link:
                    if self.pack_select:
                        select = control.select_dialog(control.ADDON_NAME, [i['release_title']])
                        if select != -1:
                            self.return_data['url'] = stream_link
                    else:
                        self.return_data['url'] = stream_link
                    break

        if self.play and self.return_data.get('link'):
            if not self.return_data.get('url'):
                self.return_data = self.prefetch_play_link()

            if self.return_data.get('url'):
                if self.source_select_close:
                    self.source_select_close()
                item = xbmcgui.ListItem(path=self.return_data['url'], offscreen=True)

                if self.return_data.get('headers', {}).get('Content-Type'):
                    item.setProperty('MimeType', self.return_data['headers']['Content-Type'])
                    # Run any mimetype hook
                    item = HookMimetype.trigger(self.return_data['headers']['Content-Type'], item)

                if self.context:
                    params = control.window.getProperty('otaku.player.video_info')
                    control.window.clearProperty('otaku.player.video_info')
                    if params:
                        try:
                            params = json.loads(params)
                        except:
                            params = {}
                        if params.get('art') is not None:
                            item.setArt(params.pop('art'))
                        if params:
                            control.set_videotags(item, params)

                    control.playList.add(self.return_data['url'], item)
                    xbmc.Player().play(control.playList, item)
                else:
                    xbmcplugin.setResolvedUrl(control.HANDLE, True, item)
                    params = {}
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
                    player.WatchlistPlayer().handle_player(self.mal_id, watchlist_update_episode, self.episode, self.resume, params.get('path'), self.context)
        else:
            self.close()

    def resolve_source(self, api, source):
        api = api()
        hash_ = source['hash']

        magnet = f"magnet:?xt=urn:btih:{hash_}"
        stream_link = {}
        if source['type'] in ['torrent', 'torrentio']:
            stream_link = api.resolve_single_magnet(hash_, magnet, source['episode_re'], self.pack_select, source.get('filename'))
        elif source['type'] in ['cloud', 'hoster']:
            hash_ = api.resolve_cloud(source, self.pack_select)
            if hash_:
                stream_link = api.resolve_hoster(hash_)
        return stream_link


    def prefetch_play_link(self) -> dict:
        try:
            url = self.return_data['link']
        except KeyError:
            url = ''

        if not url:
            return {}

        try:
            r = requests.get(url, stream=True)
        except requests.exceptions.SSLError:
            yesno = control.yesno_dialog(f'{control.ADDON_NAME}: Request Error',
                                         f'{url}\nWould you like to try without verifying TLS certificate?')
            if yesno == 1:
                r = requests.get(url, stream=True, verify=False)
            else:
                return {}
        except Exception as e:
            control.log(repr(e), level='warning')
            return {}

        return {
            "url": r.url,
            "headers": r.headers
        }

    def resolve_uncache(self, source):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        f_string = (f"[I]{source['release_title']}[/I][CR]"
                    f"[CR]"
                    f"This source is not cached would you like to cache it now?")
        api = self.resolvers[source['debrid_provider']]()
        autorun = control.getBool('uncached.autorun')
        if autorun:
            resolved_cache = api.resolve_uncached_source_background(source, autorun)
        else:
            yesnocustom = control.yesnocustom_dialog(heading, f_string, "Cancel", "Run in Background", "Run in Forground")
            if yesnocustom == 0:
                resolved_cache = api.resolve_uncached_source_background(source, autorun)
            elif yesnocustom == 1:
                resolved_cache = api.resolve_uncached_source_forground(source, autorun)
            else:
                self.canceled = True
                resolved_cache = None
            if not resolved_cache:
                self.canceled = True
        return resolved_cache

    def doModal(self, sources) -> dict:
        self.sources = sources
        if self.sources:
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
            control.setString('last_played', self.sources[0]['release_title'])
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
        stream_url = item.getPath()
        item.setProperty('inputstream', is_helper.inputstream_addon)
        if '|' in stream_url:
            stream_url, headers = stream_url.split('|')
            item.setProperty('inputstream.adaptive.stream_headers', headers)
            if control.kodi_version > 21.8:
                item.setProperty('inputstream.adaptive.common_headers', headers)
            else:
                item.setProperty('inputstream.adaptive.stream_params', headers)
                item.setProperty('inputstream.adaptive.manifest_headers', headers)
    else:
        raise Exception("InputStream Adaptive is not supported.")
    return item


@HookMimetype('application/vnd.apple.mpegurl')
def _HLS_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():
        stream_url = item.getPath()
        item.setProperty('inputstream', is_helper.inputstream_addon)
        if '|' in stream_url:
            stream_url, headers = stream_url.split('|')
            item.setProperty('inputstream.adaptive.stream_headers', headers)
            if control.kodi_version > 21.8:
                item.setProperty('inputstream.adaptive.common_headers', headers)
            else:
                item.setProperty('inputstream.adaptive.stream_params', headers)
                item.setProperty('inputstream.adaptive.manifest_headers', headers)
    return item


@HookMimetype('video/MP2T')
def _HLS_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():
        stream_url = item.getPath()
        item.setProperty('inputstream', is_helper.inputstream_addon)
        if '|' in stream_url:
            stream_url, headers = stream_url.split('|')
            item.setProperty('inputstream.adaptive.stream_headers', headers)
            if control.kodi_version > 21.8:
                item.setProperty('inputstream.adaptive.common_headers', headers)
            else:
                item.setProperty('inputstream.adaptive.stream_params', headers)
                item.setProperty('inputstream.adaptive.manifest_headers', headers)
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