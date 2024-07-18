from resources.lib.windows.base_window import BaseWindow
from resources.lib.ui import control
from operator import itemgetter

SORT_METHODS = ['none', 'type', 'audio', 'resolution', 'size']

SORT_OPTIONS = {
    'sortmethod': SORT_METHODS,
    "none": [],
    "type": ['cloud', 'torrent', 'embeds', 'files', "none"],
    "audio": ['dualaudio', 'dub', 'sub', 'none'],
    "resolution": [],
    "size": []
}

audio = [1, 2, 0, 'none']
source_type = [['cloud'], ['torrent'], ['direct', 'embed'], ['local_files'], ['none']]


class SortSelect(BaseWindow):
    def __init__(self, xml_file, location):
        super().__init__(xml_file, location)
        self.sort_options = {}
        for inx, key in enumerate(SORT_OPTIONS):
            for i, options in enumerate(SORT_OPTIONS[key], 1):
                self.sort_options[f'{key}.{i}'] = int(control.getSetting(f"{key}.{i}"))
        for idx, sort_method in enumerate(SORT_METHODS, 1):
            setting_reverse = control.getSetting(f'sortmethod.{idx}.reverse') == 'True'
            self.sort_options[f'sortmethod.{idx}.reverse'] = setting_reverse

    def onInit(self):
        self.populate_all_lists()
        self.setFocusId(9001)

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()

        if actionID == 7:
            self.handle_action(7)

    def onClick(self, control_id):
        self.handle_action(control_id)

    def handle_action(self, control_id):
        if control_id == 9001:   # close
            self.close()
        elif control_id == 9002:
            self.save_settings()
            control.ok_dialog(control.ADDON_NAME, 'Saved Sort Configuration')
        elif control_id in [1111, 2222, 3333, 4444, 5555]:
            self.handle_reverse(int(control_id / 1111))
        else:
            self.cycle_info(int(control_id / 1000), (control_id % 1000) - 1)
            self.populate_all_lists()
            self.setFocusId(control_id)

    def reset_properties(self):
        for x in range(6):
            for j in range(6):
                self.clearProperty(f'sortmethod.{x}.label.{j}')

    def handle_reverse(self, level):
        setting = f"sortmethod.{level}.reverse"
        self.sort_options[setting] = not self.sort_options[setting]
        self.setProperty(setting, str(self.sort_options[setting]))
        control.setSetting(setting, str(self.sort_options[setting]))

    def cycle_info(self, level, idx):
        sort_method = f"sortmethod.{level}"
        method = SORT_METHODS[self.sort_options[sort_method]]
        setting = sort_method if idx == 0 else f'{method}.{idx}'
        current = self.sort_options[setting]
        category = setting.split('.')[0]
        new = (current + 1) % len(SORT_OPTIONS[category])
        self.sort_options[setting] = new

    def populate_all_lists(self):
        self.reset_properties()
        for control_id in [1000, 2000, 3000, 4000, 5000]:
            self.populate_list(int(control_id / 1000))

    def populate_list(self, level):
        sort_method = f"sortmethod.{level}"
        method = SORT_METHODS[self.sort_options[sort_method]]
        options = SORT_OPTIONS[method]
        loops = len(options) + 1
        for idx in range(loops):
            if idx == 0:
                self.setProperty(f'sortmethod.{level}.label.{idx}', method)
            else:
                self.setProperty(f'sortmethod.{level}.label.{idx}', options[self.sort_options[f'{method}.{idx}']])
        self.setProperty(f"{sort_method}.reverse", str(self.sort_options[f"{sort_method}.reverse"]))
        self.setProperty(f"{sort_method}", method)

    def save_settings(self):
        for setting in self.sort_options:
            control.setSetting(setting, str(self.sort_options[setting]))


def sort_by_none(list_, reverse):
    return list_


def sort_by_resolution(list_, reverse):
    list_.sort(key=itemgetter('quality'), reverse=reverse)
    return list_


def sort_by_size(list_, reverse):
    list_.sort(key=itemgetter('byte_size'), reverse=reverse)
    return list_


def sort_by_type(list_, reverse):
    for i in range(len(SORT_OPTIONS['type']), 0, -1):
        list_.sort(key=lambda x: x['type'] in source_type[int(control.getSetting(f'type.{i}'))], reverse=reverse)
    return list_


def sort_by_audio(list_, reverse):
    for i in range(len(SORT_OPTIONS['audio']), 0, -1):
        list_.sort(key=lambda x: x['lang'] == audio[int(control.getSetting(f'audio.{i}'))], reverse=reverse)
    return list_
