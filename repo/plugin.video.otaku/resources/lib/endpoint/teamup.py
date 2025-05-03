import datetime
import re
import requests

from dateutil.tz import tzlocal

api_key = '7d05c918d14d9a89347492f8916e3a76457de61dd3303e9a31aecb971d6c8149'
headers = {'Content-Type': "application/json", 'Teamup-Token': api_key}
token = "ksdhpfjcouprnauwda"
api_url = "https://api.teamup.com"


def get_dub_data(en_title):
    if en_title:
        # match first word or first two words (seperated by {space} )
        regex = r'([^ ]+)' if '-' in en_title else r'([^ ]+) ?([^ ]+)?'
        match = re.match(regex, en_title)
        if match.group(0).lower() == 'the':
            regex = r'([^ ]+) ?([^ ]+)?'
            match = re.match(regex, en_title)
        query_search = match.group(1) if "2n" in match.group(0) else match.group(0)
        parms = {
            'query': f'\"{query_search}\"',
            'startDate': datetime.datetime.today(),
            'endDate': datetime.datetime.today().date() + datetime.timedelta(days=90)
        }
        r = requests.get(f'{api_url}/{token}/events', headers=headers, params=parms)
        teamup_data = r.json()['events']

        dub_list = []
        for teamup_dat in teamup_data:
            title = teamup_dat['title']
            end_dt = teamup_dat["end_dt"]
            episode, season = match_episode(title)
            # if match.group(1) != "#":
            #     ep_number = match.group(2)
            #     delayed = match.group(1)
            #     dub_list.append({"season": season, "episode": ep_number, "release_time": delayed})
            if episode:
                # More than one episode in teamup_dat
                if len(episode) == 2:
                    ep_number1 , ep_number2 = episode
                    dub_time = datetime.datetime.strptime(end_dt, '%Y-%m-%dT%H:%M:%S%z')
                    dub_time = str(dub_time.astimezone(tzlocal()))[:16]
                    dub_list = [{"season": season, "episode": f'{i}', "release_time": dub_time} for i in range(int(ep_number1), int(ep_number2) + 1)]

                # Only one episode in teamup_dat
                elif len(episode) == 1:
                    ep_number = episode[0]
                    dub_time = datetime.datetime.strptime(end_dt, '%Y-%m-%dT%H:%M:%S%z')
                    dub_time = str(dub_time.astimezone(tzlocal()))[:16]
                    dub_list.append({"season": season, "episode": ep_number, "release_time": dub_time})
        return dub_list

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
