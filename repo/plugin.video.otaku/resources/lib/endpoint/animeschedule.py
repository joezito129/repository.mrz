import requests
import datetime
import re

from dateutil.tz import tzlocal
from resources.lib.ui import database, control
from bs4 import BeautifulSoup

base_url = "https://animeschedule.net/api/v3"

def get_route(mal_id) -> str:
    params = {
        "mal-ids": mal_id
    }
    r = requests.get(f"{base_url}/anime", params=params)
    return r.json()['anime'][0]['route'] if r.ok else ''


def get_dub_time(mal_id) -> list:
    show = database.get_show(mal_id)
    route = show['anime_schedule_route']
    if not route:
        route = get_route(mal_id)
        database.update_show(mal_id, show['kodi_meta'], route)
    r = requests.get(f'https://animeschedule.net/anime/{route}')

    soup = BeautifulSoup(r.text, 'html.parser')
    soup_all = soup.find_all('div', class_='release-time-wrapper')
    dub_list = []
    for soup in soup_all:
        if 'dub:' in soup.text.lower():
            dub_soup = soup
            dub_text = dub_soup.span.text
            date_time = dub_soup.time.get('datetime')

            if '-' in dub_text:
                match = re.match(r'Episodes (\d+)-(\d+)', dub_text)
                ep_begin = int(match.group(1))
                ep_end = int(match.group(2))
                for ep_number in range(ep_begin, ep_end):
                    try:
                        dub_time = datetime.datetime.strptime(date_time, '%Y-%m-%dT%H:%M%z')
                    except TypeError:
                        import time
                        control.log('Unsupported strptime using fromtimestamp', 'warning')
                        dub_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date_time, '%Y-%m-%dT%H:%M%z')))
                    dub_time = str(dub_time.astimezone(tzlocal()))[:16]
                    dub_list.append({"season": 0, "episode": ep_number, "release_time": dub_time})
            else:
                match = re.match(r'Episode (\d+)', dub_text)
                ep_number = int(match.group(1))
                try:
                    dub_time = datetime.datetime.strptime(date_time, '%Y-%m-%dT%H:%M%z')
                except TypeError:
                    import time
                    control.log('Unsupported strptime using fromtimestamp', 'warning')
                    dub_time = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date_time, '%Y-%m-%dT%H:%M%z')))
                dub_time = str(dub_time.astimezone(tzlocal()))[:16]
                dub_list.append({"season": 0, "episode": ep_number, "release_time": dub_time})
            return dub_list
    return []
