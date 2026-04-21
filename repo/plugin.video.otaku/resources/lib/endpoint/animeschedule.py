import requests
import re

from resources.lib.ui import database, utils
from bs4 import BeautifulSoup

base_url = "https://animeschedule.net/api/v3"


def get_route(mal_id) -> str:
    params = {"mal-ids": mal_id}
    r = requests.get(f"{base_url}/anime", params=params, timeout=10)
    return r.json()['anime'][0]['route'] if r.ok else ''


def get_dub_time(mal_id) -> list:
    route = database.get_show_id(mal_id, 'anime_schedule_route')
    if route is None:
        route = get_route(mal_id)
        database.update_mapping(mal_id, 'anime_schedule_route', route)
    r = requests.get(f'https://animeschedule.net/anime/{route}', timeout=10)
    soup = BeautifulSoup(r.text, 'html.parser')
    soup_all = soup.find_all('div', class_='release-time-wrapper')
    dub_list = []
    for div in soup_all:
        if 'dub:' in soup.text.lower():
            dub_text = div.span.text if div.span else None
            date_time = div.time.get('datetime') if div.time else None

            if dub_text is None or not isinstance(date_time, str):
                continue

            if '-' in dub_text:
                match = re.match(r'Episodes (\d+)-(\d+)', dub_text)
                if match is None:
                    continue
                ep_begin = int(match.group(1))
                ep_end = int(match.group(2))
                for ep_number in range(ep_begin, ep_end):
                    dub_time = utils.strp_time(date_time, '%Y-%m-%dT%H:%M%z')
                    if dub_time is not None:
                        dub_time = str(dub_time.astimezone())[:16]
                        dub_list.append({"season": 0, "episode": ep_number, "release_time": dub_time})
            else:
                match = re.match(r'Episode (\d+)', dub_text)
                if match is not None:
                    ep_number = int(match.group(1))
                    dub_time = utils.strp_time(date_time, '%Y-%m-%dT%H:%M%z')
                    if dub_time is not None:
                        dub_time = str(dub_time.astimezone())[:16]
                        dub_list.append({"season": 0, "episode": ep_number, "release_time": dub_time})
            return dub_list
    return []
