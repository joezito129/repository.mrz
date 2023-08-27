import datetime
import re
import requests
import time

# from resources.lib.ui import control

class TeamUp:
    def __init__(self):
        self.api_key = '7d05c918d14d9a89347492f8916e3a76457de61dd3303e9a31aecb971d6c8149'
        self.headers = {'Content-Type': "application/json", 'Teamup-Token': self.api_key}
        self.token = "ksdhpfjcouprnauwda"
        self.api_url = "https://api.teamup.com"

    def get_dub_data(self, en_title):
        if en_title:
            # match first word or first two words (seperated by {space} )
            regex = r'([^ ]+)' if '-' in en_title else r'([^ ]+) ?([^ ]+)?'
            match = re.match(regex, en_title)


            query_search = match.group(1) if "2n" in match.group(0) else match.group(0)
            parms = {
                'query': f'\"{query_search}\"',
                'startDate': datetime.datetime.today(),
                'endDate': datetime.datetime.today().date() + datetime.timedelta(days=90)
            }
            r = requests.get(f'{self.api_url}/{self.token}/events', headers=self.headers, params=parms)
            teamup_data = r.json()['events']

            dub_data = []
            for teamup_dat in teamup_data:
                title = teamup_dat['title']
                end_dt = teamup_dat["end_dt"]
                match = re.match(r'(.)(\d+) ?(-)? ?(\d+)?[^|]+?\D+(\d+)?', title)
                season = match.group(5) or 0
                if match.group(1) != "#":
                    ep_number = match.group(2)
                    delayed = match.group(1)
                    dub_data.append({"season": season, "episode": ep_number, "release_time": delayed})
                else:
                    # More than one episode in teamup_dat
                    if match.group(3) is not None:
                        ep_number1 = match.group(2)
                        ep_number2 = match.group(4)
                        end_dt_formated = datetime.datetime.strptime(end_dt, "%Y-%m-%dT%H:%M:%S%z")
                        end_time = f'{end_dt_formated - datetime.timedelta(hours=5)}'[:16]
                        dub_data = [{"season": season, "episode": f'{i}', "release_time": end_time} for i in range(int(ep_number1), int(ep_number2) + 1)]

                    # Only one episode in teamup_dat
                    else:
                        ep_number = match.group(2)
                        try:
                            end_dt_formated = datetime.datetime.strptime(end_dt[:19], "%Y-%m-%dT%H:%M:%S")
                        except TypeError:
                            end_dt = re.sub('T', '', end_dt)
                            end_dt = re.sub(':', '', end_dt)
                            end_dt_formated = datetime.datetime(*(time.strptime(end_dt[:14], "%Y-%m-%d%H%M")[0:7]))

                        end_time = f'{end_dt_formated - datetime.timedelta(hours=5)}'[:16]
                        dub_data.append({"season": season, "episode": ep_number, "release_time": end_time})
            return dub_data

teamup = TeamUp()
