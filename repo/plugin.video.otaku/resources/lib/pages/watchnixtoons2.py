import pickle
import requests

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import BrowserBase, control, database


class Sources(BrowserBase.BrowserBase):
    _BASE_URL = 'https://www.wcostream.tv' # wconflix.tv

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show['kodi_meta'])
        title = kodi_meta['name']
        title = self._clean_title(title)

        data = {
            'catara': f"{title.replace(' ', '+')}+S+1+E+{episode}",
            'konuara': 'episodes'
        }
        r = requests.post(f'{self._BASE_URL}/search', data=data)

        only_results = SoupStrainer("div", class_="cat-listview2 cat-listbsize2")
        soup = BeautifulSoup(r.text, 'html.parser', parse_only=only_results)
        soup_all = soup.find_all('a', class_='sonra')

        table = {}
        lang_int = control.getInt('general.source') # 0 SUB, 1 BOTH, 2 DUB
        for i, t in enumerate(soup_all):
            text = t.text.lower()
            if str(episode) in text:
                if lang_int == 1:
                    table[text] = t.get('href')
                elif 'dub' in text and lang_int == 2:
                    table[text] = t.get('href')
                elif 'sub' in text and lang_int == 0:
                    table[text] = t.get('href')





