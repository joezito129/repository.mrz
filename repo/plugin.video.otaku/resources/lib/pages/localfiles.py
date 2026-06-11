import os

from functools import partial
from resources.lib.ui import BrowserBase, source_utils, control

PATH = control.getString('download.location')


class Sources(BrowserBase.BrowserBase):
    def get_sources(self, titles: list, mal_id: int, episode: int):
        filenames = []
        for root, dirs, files in os.walk(PATH):
            for file in files:
                if source_utils.is_file_ext_valid(file):
                    filenames.append(str(os.path.join(root, file).replace(PATH, '')))

        # clean_filenames = [re.sub(r'\[.*?]\s*', '', os.path.basename(i).replace(',', '')) for i in filenames]
        filtered_list = source_utils.filter_sources(filenames, 0, episode)
        mapfunc = partial(self.process_offline_search, episode=episode)
        all_results = list(map(mapfunc, filtered_list))
        return all_results

    @staticmethod
    def process_offline_search(f, episode):
        full_path = os.path.join(PATH, f)
        source = {
            'release_title': os.path.basename(f),
            'link': os.path.join(PATH, f),
            'type': 'local_files',
            'quality': source_utils.getQuality(f),
            'debrid_provider': PATH,
            'provider': 'local_files',
            'episode_re': episode,
            'size': source_utils.get_size(os.path.getsize(full_path)),
            'byte_size': os.path.getsize(full_path),
            'info': source_utils.getInfo(f),
            'lang': source_utils.getAudio_lang(f)
        }
        return source
