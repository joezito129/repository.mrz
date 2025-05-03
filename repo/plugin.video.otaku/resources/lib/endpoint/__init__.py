from resources.lib.ui.control import settingids


def get_second_label(info, dub_data, filler):
    code_dub = None

    if dub_data:
        episode = info['episode']
        for dub_dat in dub_data:
            season = int(info['season'])
            if (int(dub_dat['season']) == season or dub_dat['season'] == 0) and int(dub_dat['episode']) == episode:
                code_dub = dub_dat["release_time"]
                break

    if code_dub:
        code = f'Dub {code_dub}'
    elif settingids.filler:
        code = filler
    else:
        code = None
    return code
