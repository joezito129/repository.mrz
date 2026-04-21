from resources.lib.ui import control


def get_second_label(info, dub_data, filler):
    if filler is not None and filler == 'Filler':
        filler = control.colorstr(filler, color="red")
    code_dub = None
    code = None
    if dub_data is not None:
        episode = info['episode']
        for dub_dat in dub_data:
            season = info['season']
            if (int(dub_dat['season']) == season or dub_dat['season'] == 0) and int(dub_dat['episode']) == episode:
                code_dub = dub_dat["release_time"]
                break
    if code_dub is not None:
        code = f'Dub {code_dub}'
    elif control.getBool('jz.filler'):
        code = filler
    return code
