import json
import requests

from resources.lib.ui import control


def div_flavor(f):
    def wrapper(*args, **kwargs):
        if control.getSetting("divflavors.bool") == "true":
            dubsub_filter = control.getSetting("divflavors.menu")
            mal_dub = get_mal_dub()
            return f(mal_dub=mal_dub, dubsub_filter=dubsub_filter, *args, **kwargs)
        return f(*args, **kwargs)
    return wrapper


def get_mal_dub():
    try:
        with open(control.maldubFile) as mal_dub:
            mal_dub = json.load(mal_dub)
    except FileNotFoundError:
        with open(control.maldubFile, 'w') as file_to_dump:
            mal_dub_raw = requests.get('https://raw.githubusercontent.com/MAL-Dubs/MAL-Dubs/main/data/dubInfo.json')
            mal_dub_list = mal_dub_raw.json()["dubbed"]
            mal_dub = {str(item): {'dub': True} for item in mal_dub_list}
            json.dump(mal_dub, file_to_dump, indent=4)
    return mal_dub
