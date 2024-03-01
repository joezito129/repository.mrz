import requests
import datetime
import re

from bs4 import BeautifulSoup
from resources.lib.ui import database

# from resources.lib.ui import control

base_url = "https://animeschedule.net/api/v3"


def get_route(anilist_id):
    params = {
        "anilist-ids": anilist_id
    }
    r = requests.get(f'{base_url}/anime', params=params)
    return r.json()['anime'][0]['route']


def get_dub_time(anilist_id):
    show = database.get_show(anilist_id)
    route = show['anime_schedule_route']
    if not route:
        route = get_route(anilist_id)
        database.update_show(anilist_id, show['mal_id'], show['simkl_id'], show['kitsu_id'], show['kodi_meta'], show['last_updated'], route)
    r = requests.get(f'https://animeschedule.net/anime/{route}')
    soup = BeautifulSoup(r.text, 'html.parser')
    soup_all = soup.find_all('div', class_='release-time-wrapper')
    if len(soup_all) >= 3:
        dub_soup = soup_all[2]
        ep_number = int(dub_soup.span.text[7:])

        date_time = dub_soup.time.get('datetime')
        try:
            dub_time = str(datetime.datetime.strptime(date_time[:16], "%Y-%m-%dT%H:%M") - datetime.timedelta(hours=5))[:16]
        except TypeError:
            import time
            date_time = re.sub('T', '', date_time)
            date_time = re.sub(':', '', date_time)
            dub_time = str(datetime.datetime(*(time.strptime(date_time[:14], "%Y-%m-%d%H%M")[0:7])) - datetime.timedelta(hours=5))[:16]
        dub_data = {"season": 0, "episode": ep_number, "release_time": dub_time}
        return [dub_data]
