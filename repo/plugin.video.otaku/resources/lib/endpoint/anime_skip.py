import requests

base_url = "https://api.anime-skip.com/graphql"
headers = {"X-Client-ID": "buT57NJMu4G65vxGJWdj4UXgnq65Agfi"}


def get_episode_ids(anilist_id: int, episode: int):
    query = '''
    query($service: ExternalService!, $serviceId: String!) {
        findShowsByExternalId(service: $service, serviceId: $serviceId) {
            episodes {
                id
                number
            }
        }
    }
'''
    variables = {
        'service': 'ANILIST',
        'serviceId': str(anilist_id)
    }

    r = requests.post(base_url, headers=headers, json={'query': query, 'variables': variables}, timeout=20)
    res = r.json()['data']['findShowsByExternalId']
    for resx in res:
        for x in resx['episodes']:
            if x['number'] and int(x['number']) == episode:
                return x['id']
    return None


def get_time_stamps(animeskip_id) -> dict:
    if animeskip_id is None:
        return {}
    query = '''
        query($episodeId: ID!) {
            findTimestampsByEpisodeId(episodeId: $episodeId) {
                at
                type {
                    name

                }  
            }
        }
    '''

    variables = {'episodeId': animeskip_id}
    r = requests.post(base_url, headers=headers, json={'query': query, 'variables': variables}, timeout=20)
    res = r.json()['data']['findTimestampsByEpisodeId']
    return res
