import itertools
import pickle

from functools import partial
from urllib import parse
from resources.lib.ui import control, database
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.indexers import anify


class sources(BrowserBase):
    def get_sources(self, anilist_id, episode):
        all_results = []
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

        for lang in langs:
            r = database.get_(anify.ANIFYAPI().get_sources_json, 8,
                              anilist_id, episode, '9anime', lang)

            if r and r.get('sources'):
                srcs = r['sources']
                for i in range(len(srcs)):
                    srcs[i]['type'] = lang.upper()
                referer = r.get('headers', {}).get('Referer', '')
                if referer:
                    referer = parse.urljoin(referer, '/')
                mapfunc = partial(anify.process_anify, provider='9anime', title=title, lang=2 if lang == 'dub' else 0, referer=referer)
                results = map(mapfunc, srcs)
                results = list(itertools.chain(*results))
                all_results += results
        return all_results
