import requests

base_url = "https://api.anime-skip.com/graphql"

headers = {"X-Client-ID": "buT57NJMu4G65vxGJWdj4UXgnq65Agfi"}


def get_episode_ids(anilist_id, episode):
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
        'serviceId': anilist_id
    }

    r = requests.post(base_url, headers=headers, json={'query': query, 'variables': variables}, timeout=10)
    res = r.json()['data']['findShowsByExternalId']
    id_list = []
    for resx in res:
        for x in resx['episodes']:
            if x['number'] and int(x['number']) == episode:
                id_list.append(x['id'])
    return id_list


def get_time_stamps(id_list):
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

    variables = {}
    res = {}
    for x, in range(len(id_list)):
        variables['episodeId'] = id_list[x]
        r = requests.post(base_url, headers=headers, json={'query': query, 'variables': variables}, timeout=10)
        res = r.json()['data']['findTimestampsByEpisodeId']
        if res:
            break
    return res
