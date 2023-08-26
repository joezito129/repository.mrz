import itertools
import pickle

from functools import partial
from resources.lib.ui import database, control
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.indexers import anify


class sources(BrowserBase):

    def get_sources(self, anilist_id, episode):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta['ename'] or kodi_meta['name']
        title = self._clean_title(title)
        title = '{0} Ep-{1}'.format(title, episode)
        langs = ['sub', 'dub']
        if control.getSetting('general.source') == 'Sub':
            langs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            langs.remove('sub')

        all_results = []
        for lang in langs:
            r = database.get_(anify.ANIFYAPI().get_sources_json, 8, anilist_id, episode, 'gogoanime', lang)

            if r and r.get('sources'):
                srcs = r['sources']
                subs = r.get('subtitles')
                if subs:
                    subs = [x for x in subs if x.get('lang') != 'Thumbnails']
                mapfunc = partial(anify.process_anify, provider='gogohd', title=title, lang=2 if lang == 'dub' else 0, subs=subs)
                results = map(mapfunc, srcs)
                results = list(itertools.chain(*results))
                all_results += results
        return all_results
