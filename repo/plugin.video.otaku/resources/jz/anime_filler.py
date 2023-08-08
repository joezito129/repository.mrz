import re
import requests

from bs4 import BeautifulSoup

url = "https://www.animefillerlist.com/shows"

def get_data(anime_eng_title):
    if not anime_eng_title:
        return []
    anime_url = re.sub(r'\W', '-', anime_eng_title)
    try:
        r = requests.get(f'{url}/{anime_url}')
        soup = BeautifulSoup(r.text, 'html.parser')
        soup_all = soup.find('table', class_="EpisodeList").tbody.find_all('tr')
        filler_list = [i.span.text for i in soup_all]
    except AttributeError:
        filler_list = []

    return filler_list
