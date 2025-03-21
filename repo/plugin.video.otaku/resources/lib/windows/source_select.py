import pickle
import xbmcgui

from resources.lib.ui import control, database
from resources.lib.windows.base_window import BaseWindow
from resources.lib.windows.resolver import Resolver
from resources.lib import OtakuBrowser


class SourceSelect(BaseWindow):
    def __init__(self, xml_file, location, *, actionArgs=None, sources=None, rescrape=False):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.actionArgs = actionArgs
        self.sources = sources
        self.rescrape = rescrape
        self.position = -1
        self.canceled = False
        self.display_list = None
        self.stream_link = None

        episode = actionArgs.get('episode')
        if episode:
            anime_init = OtakuBrowser.get_anime_init(actionArgs.get('mal_id'))
            episode = int(episode)
            self.info = anime_init[0][episode - 1]['info']
            self.setProperty('item.info.title', self.info.get('title', ''))
            self.setProperty('item.info.season', str(self.info.get('season', '')))
            self.setProperty('item.info.episode', str(self.info.get('episode', '')))
            self.setProperty('item.info.plot', self.info.get('plot', ''))
            self.setProperty('item.info.rating', str(self.info.get('rating', {}).get('score', '')))

            aired = self.info.get('aired', '')
            self.setProperty('item.info.aired', aired)
            aired_list = aired.split('-', 2)
            if len(aired_list) == 3:
                year, month, day = aired_list
                self.setProperty('item.info.year', year)

        else:
            show = database.get_show(actionArgs.get('mal_id'))
            if show:
                kodi_meta = pickle.loads(show.get('kodi_meta'))
                self.setProperty('item.info.plot', kodi_meta.get('plot', ''))
                self.setProperty('item.info.rating', str(kodi_meta.get('rating', {}).get('score', '')))
                aired = kodi_meta.get('start_date', '')
                self.setProperty('item.info.aired', aired)
                aired_list = aired.split('-', 2)
                if len(aired_list) == 3:
                    year, month, day = aired_list
                    self.setProperty('item.info.year', year)

    def onInit(self):
        self.display_list = self.getControl(1000)
        for i in self.sources:
            if i:
                menu_item = xbmcgui.ListItem(i['release_title'], offscreen=True)
                properties = {
                    'type': i['type'],
                    'debrid_provider': i['debrid_provider'],
                    'provider': i['provider'],
                    'quality': str(i['quality']),
                    'info': str(' '.join(i['info'])),
                    'seeders': str(i.get('seeders', '')) if i.get('seeders') != -1 else '',
                    'size': i['size']
                }
                menu_item.setProperties(properties)
                self.display_list.addItem(menu_item)
        self.setFocusId(1000)

    def doModal(self):
        super(SourceSelect, self).doModal()
        return self.stream_link

    def onClick(self, controlId):
        self.handle_action(controlId)

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            control.playList.clear()
            self.stream_link = False
            self.close()

        elif actionID == 117:
            context = control.context_menu(
                [
                    "Play",
                    "Download",
                    "File Select"
                ]
            )
            self.position = self.display_list.getSelectedPosition()
            if context == 0:  # Play
                self.resolve_item()
            elif context == 1:  # Download
                if not self.sources[self.position]['debrid_provider']:
                    control.notify(control.ADDON_NAME, "Please Select A Debrid File")
                else:
                    self.close()
                    source = [self.sources[self.display_list.getSelectedPosition()]]
                    self.actionArgs['play'] = False
                    return_data = Resolver('resolver.xml', control.ADDON_PATH, actionArgs=self.actionArgs, source_select=True).doModal(source, {}, False)
                    if isinstance(return_data, dict):
                        from resources.lib.windows.download_manager import Manager
                        Manager().download_file(return_data['link'])

            elif context == 2:  # File Selection
                if not self.sources[self.position]['debrid_provider']:
                    control.notify(control.ADDON_NAME, "Please Select A Debrid File")
                else:
                    self.resolve_item(True)

    def handle_action(self, controlID):
        if self.getFocusId() == 1000:
            self.position = self.display_list.getSelectedPosition()
            self.resolve_item()


    def resolve_item(self, pack_select=False):
        if control.getBool('general.autotrynext') and not pack_select:
            sources = self.sources[self.position:]
        else:
            sources = [self.sources[self.position]]
        if self.rescrape:
            selected_source = self.sources[self.position]
            selected_source['name'] = selected_source['release_title']
        self.actionArgs['close'] = self.close
        self.stream_link = Resolver('resolver.xml', control.ADDON_PATH, actionArgs=self.actionArgs, source_select=True).doModal(sources, {}, pack_select)
        if isinstance(self.stream_link, dict):
            self.close()
