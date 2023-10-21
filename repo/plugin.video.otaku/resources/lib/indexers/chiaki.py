import requests


baseurl = 'https://chiaki.vercel.app'

def get_watch_order_list(mal_id):
    params = {
        "group_id": mal_id
    }
    r = requests.get(f'{baseurl}/get', params=params)
    res = r.json()
    return res
