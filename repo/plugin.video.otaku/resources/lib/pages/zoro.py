import itertools
import pickle
from functools import partial

from resources.lib.ui import control, database
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.indexers import anify, enime


class sources(BrowserBase):
    def get_sources(self, anilist_id, episode):
        all_results = []
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta.get('ename') or kodi_meta.get('name')
        title = self._clean_title(title)
        title = '{0} Ep-{1}'.format(title, episode)
        srcs = ['sub', 'dub']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            srcs.remove('sub')

        for x in srcs:
            r = database.get(
                anify.ANIFYAPI().get_sources_json,
                8,
                anilist_id,
                episode,
                'zoro',
                x
            )

            if r and r.get('sources'):
                srcs = r['sources']
                subs = r.get('subtitles')
                if subs:
                    subs = [x for x in subs if x.get('lang') != 'Thumbnails']
                mapfunc = partial(anify.process_anify, provider='zoro', title=title, lang=2 if x == 'dub' else 0, subs=subs)
                results = map(mapfunc, srcs)
                results = list(itertools.chain(*results))
                all_results += results

        if not all_results:
            r = database.get(
                enime.ENIMEAPI().get_sources,
                8,
                anilist_id,
                episode,
                'zoro'
            )
            if r and r.get('url'):
                slink = r['url'] + '|Referer={0}&User-Agent=iPad'.format(r.get('referer').split('?')[0])
                source = {
                    'release_title': title,
                    'hash': slink,
                    'type': 'direct',
                    'quality': 'EQ',
                    'debrid_provider': '',
                    'provider': 'zoro',
                    'size': 'NA',
                    'info': ['HLS'],
                    'lang': 0
                }
                if r.get('subtitle'):
                    source.update({'subs': [{'url': r['subtitle'], 'lang': 'English'}]})
                all_results.append(source)
        return all_results
