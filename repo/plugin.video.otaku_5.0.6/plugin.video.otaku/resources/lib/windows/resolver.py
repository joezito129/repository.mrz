import sys

from resources.lib.debrid import all_debrid, debrid_link, premiumize,real_debrid
from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow

sys.path.append(control.dataPath)


class Resolver(BaseWindow):

    def __init__(self, xml_file, location=None, actionArgs=None):
        super(Resolver, self).__init__(xml_file, location, actionArgs=actionArgs)
        self.return_data = None
        self.canceled = False
        self.silent = False
        self.pack_select = None
        self.sources = None
        self.args = None
        self.resolvers = {
            'all_debrid': all_debrid.AllDebrid,
            'debrid_link': debrid_link.DebridLink,
            'premiumize': premiumize.Premiumize,
            'real_debrid': real_debrid.RealDebrid
        }

    def onInit(self):
        self.resolve(self.sources)

    def resolve(self, sources):
        # Begin resolving links
        for i in sources:
            debrid_provider = i.get('debrid_provider', 'None').replace('_', ' ')
            if self.is_canceled():
                break

            self.setProperty('release_title', str(i['release_title']))
            self.setProperty('debrid_provider', debrid_provider)
            self.setProperty('source_provider', i['provider'])
            self.setProperty('source_resolution', i['quality'])
            self.setProperty('source_info', " ".join(i['info']))
            self.setProperty('source_type', i['type'])

            if i['type'] == 'torrent':
                stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i)

                if stream_link:
                    self.return_data = stream_link
                    break

            elif i['type'] == 'cloud' or i['type'] == 'hoster':
                if i['type'] == 'cloud' and i['debrid_provider'] == 'premiumize':
                    stream_link = i['hash']
                else:
                    stream_link = self.resolve_source(self.resolvers[i['debrid_provider']], i)

                if stream_link:
                    self.return_data = stream_link
                    break

            elif i['type'] == 'direct':
                stream_link = i['hash']
                if stream_link:
                    self.return_data = stream_link
                    if i.get('subs'):
                        self.return_data = (stream_link, i['subs'])
                    break

            elif i['type'] == 'embed':
                from resources.lib.ui import embed_extractor
                stream_link = embed_extractor.load_video_from_url(i['hash'])
                if stream_link:
                    self.return_data = stream_link
                    break
        control.sleep(1000)
        self.close()

    @staticmethod
    def resolve_source(api, source):
        stream_link = None
        api = api()
        hash_ = source['hash']
        magnet = 'magnet:?xt=urn:btih:%s' % hash_
        if source['type'] == 'torrent':
            stream_link = api.resolve_single_magnet(hash_, magnet, source['episode_re'])
        elif source['type'] == 'cloud' or source['type'] == 'hoster':
            stream_link = api.resolve_hoster(hash_)
        return stream_link

    def doModal(self, sources, args, pack_select):

        if not sources:
            return None

        self.sources = sources
        self.args = args
        self.pack_select = pack_select
        self.setProperty('release_title', str(self.sources[0]['release_title']))
        self.setProperty('debrid_provider', self.sources[0].get('debrid_provider', 'None').replace('_', ' '))
        self.setProperty('source_provider', self.sources[0]['provider'])
        self.setProperty('source_resolution', self.sources[0]['quality'])
        self.setProperty('source_info', " ".join(self.sources[0]['info']))
        self.setProperty('source_type', self.sources[0]['type'])
        self.setProperty('source_size', self.sources[0]['size'])
        if not self.silent:
            super(Resolver, self).doModal()
        else:
            self.resolve(sources)
        return None if self.canceled else self.return_data

    def is_canceled(self):
        if not self.silent and self.canceled:
            return True

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:
            self.canceled = True
            self.close()


    def close(self):
        if not self.silent:
            control.dialogWindow.close(self)
