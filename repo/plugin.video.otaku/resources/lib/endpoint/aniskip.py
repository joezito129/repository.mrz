import requests


def get_skip_times(mal_id, episodenum, skip_type) -> dict:
    # skip_types = op, recap, mixed-ed, mixed-op, ed
    url = f"https://api.aniskip.com/v2/skip-times/{mal_id}/{episodenum}"
    params = {
        'types': skip_type,
        'episodeLength': 0
    }
    r = requests.get(url, params=params, timeout=10)
    res = r.json() if r.ok else {}
    return res
