import datetime
import re
import requests

from resources.lib.ui import utils

api_key = '7d05c918d14d9a89347492f8916e3a76457de61dd3303e9a31aecb971d6c8149'
headers = {'Content-Type': "application/json", 'Teamup-Token': api_key}
token = "kskkeo3eumor21p2hu"
api_url = "https://api.teamup.com"


def get_dub_data(mal_id: int, en_title: str):
    if en_title:
        clean_title = re.sub(r'[:!]', '', en_title)
        if '-' in clean_title:
            query_search = clean_title.split('-')[0].strip()
        else:
            match = re.search(r'(?:the\s+)?(\w+(?:\s+\w+)?)', clean_title, re.IGNORECASE)
            query_search = match.group(1) if match else clean_title
        query_search = '+' + " +".join(query_search.split()[:2])
        parms = {
            'query': query_search,
            'startDate': datetime.datetime.today().isoformat(),
            'endDate': (datetime.datetime.today().date() + datetime.timedelta(days=90)).isoformat()
        }
        r = requests.get(f'{api_url}/{token}/events', headers=headers, params=parms)
        teamup_data = r.json().get('events', [])
        dub_list = []
        re_ep = re.compile(r"<strong>episode:</strong>\s*(\d+)", re.IGNORECASE)
        re_mal = re.compile(r"mal:\s*(\d+)", re.IGNORECASE)
        for teamup_dat in teamup_data:
            title = teamup_dat['title']
            end_dt = teamup_dat["end_dt"]
            notes = teamup_dat['notes']

            mal_id_match = re_mal.search(notes)
            teamup_mal_id = int(mal_id_match.group(1)) if mal_id_match else None

            if teamup_mal_id and teamup_mal_id != mal_id:
                continue

            episode_match = re_ep.search(notes)
            episode = [int(episode_match.group(1))] if episode_match else None

            if mal_id:
                season = 0
            else:
                episode, season = match_episode(title)
            if episode is not None:
                # More than one episode in teamup_dat
                if len(episode) == 2:
                    ep_number1 , ep_number2 = episode
                    dub_time = utils.strp_time(end_dt, '%Y-%m-%dT%H:%M:%S%z')
                    if dub_time is not None:
                        dub_time = str(dub_time.astimezone())[:16]
                        dub_list = [{"season": season, "episode": f'{i}', "release_time": dub_time} for i in range(int(ep_number1), int(ep_number2) + 1)]

                # Only one episode in teamup_dat
                elif len(episode) == 1:
                    ep_number = episode[0]
                    dub_time = utils.strp_time(end_dt, '%Y-%m-%dT%H:%M:%S%z')
                    if dub_time is not None:
                        dub_time = str(dub_time.astimezone())[:16]
                        dub_list.append({"season": season, "episode": ep_number, "release_time": dub_time})
        return dub_list
    return None

def match_episode(item) -> tuple:
    match = re.search(r"#?(\d+)(?:-(\d+))?", item)
    if match:
        episode_number = (int(match.group(1)), int(match.group(2))) if match.group(2) else (int(match.group(1)),)
        season_number_match = re.search(r"Season (\d+)", item)
        season_number = int(season_number_match.group(1)) if season_number_match else 0
    else:
        episode_number = None
        season_number = None
    return episode_number, season_number
