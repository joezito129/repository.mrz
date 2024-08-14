import requests

from urllib import parse
from resources.lib.debrid import all_debrid, debrid_link, premiumize, real_debrid
from resources.lib.ui import control, source_utils
from resources.lib.windows.base_window import BaseWindow

control.sys.path.append(control.dataPath)


class Resolver(BaseWindow):
    def __init__(self, xml_file, location=None, actionArgs=None, source_select=False):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.return_data = {
            'link': None,
            'linkinfo': None,
            'sub': None
        }
        self.canceled = False
        self.sources = None
        self.args = None
        self.resolvers = {
            'all_debrid': all_debrid.AllDebrid,
            'debrid_link': debrid_link.DebridLink,
            'premiumize': premiumize.Premiumize,
            'real_debrid': real_debrid.RealDebrid
        }
        self.source_select = source_select
        self.pack_select = False

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
            if self.canceled:
                break
            debrid_provider = i.get('debrid_provider', 'None').replace('_', ' ')
            self.setProperty('release_title', str(i['release_title']))
            self.setProperty('debrid_provider', debrid_provider)
            self.setProperty('source_provider', i['provider'])
            self.setProperty('source_resolution', source_utils.res[i['quality']])
            self.setProperty('source_info', " ".join(i['info']))
            self.setProperty('source_type', i['type'])

            if 'uncached' in i['type']:
                self.return_data['link'] = self.resolve_uncache(i)
                break
            if i['type'] == 'torrent':
                stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i)
                if stream_link:
                    self.return_data['link'] = stream_link
                    break

            elif i['type'] == 'cloud' or i['type'] == 'hoster':
                if i['type'] == 'cloud' and i['debrid_provider'] in ['premiumize', 'all_debrid']:
                    stream_link = i['hash']
                else:
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
                    'local': True
                }
                break

        if self.return_data.get('local'):
            self.return_data['linkinfo'] = self.return_data
        else:
            self.return_data['linkinfo'] = self.prefetch_play_link(self.return_data['link'])

        if not self.return_data['linkinfo']:
            self.return_data = False
        self.close()

    def resolve_source(self, api, source):
        api = api()
        hash_ = source['hash']
        magnet = 'magnet:?xt=urn:btih:%s' % hash_
        if source['type'] == 'torrent':
            stream_link = api.resolve_single_magnet(hash_, magnet, source['episode_re'], self.pack_select)
        elif source['type'] == 'cloud' or source['type'] == 'hoster':
            if source['torrent_files']:
                best_match = source_utils.get_best_match('path', source['torrent_files'], source['episode'], self.pack_select)
                if not best_match or not best_match['path']:
                    return
                for f_index, torrent_file in enumerate(source['torrent_files']):
                    if torrent_file['path'] == best_match['path']:
                        hash_ = source['torrent_info']['links'][f_index]
                        break
            stream_link = api.resolve_hoster(hash_)
        else:
            stream_link = None
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
            control.log(str(e), level='warning')
            return

        return {
            "url": link if '|' in link else r.url,
            "headers": r.headers
        }


    def resolve_uncache(self, source):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        f_string = f'''
[I]{source['release_title']}[/I]

This source is not cached would you like to cache it now?        
        '''
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
        api = self.resolvers[source['debrid_provider']]()
        resolved_cache = api.resolve_uncached_source(source, runbackground)
        if not resolved_cache:
            self.canceled = True
        return resolved_cache

    def doModal(self, sources, args, pack_select):
        self.sources = sources
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
        super(Resolver, self).doModal()
        control.setSetting('last_played', self.sources[0]['release_title'])
        return self.return_data

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:
            self.canceled = True
            self.close()