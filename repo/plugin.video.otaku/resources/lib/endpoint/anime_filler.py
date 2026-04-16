import re
import requests

from bs4 import BeautifulSoup

url = "https://www.animefillerlist.com/shows"


def get_data(anime_eng_title):
    filler_list = []
    if anime_eng_title:
        anime_url = re.sub(r'\W', '-', anime_eng_title)
        r = requests.get(f'{url}/{anime_url}')
        if r.ok:
            soup = BeautifulSoup(r.text, 'html.parser')
            episode_list = soup.find('table', class_="EpisodeList")
            if episode_list:
                tbody = episode_list.tbody
                if tbody:
                    soup_all = tbody.find_all('tr')
                    filler_list = [i.span.text for i in soup_all if i.span is not None]
    return filler_list
