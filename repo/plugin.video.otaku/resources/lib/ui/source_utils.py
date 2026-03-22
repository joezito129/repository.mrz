import re
import string
import xbmc
import difflib

from resources.lib.ui import control


res = ['EQ', '480p', '720p', '1080p', '4k']


def getAudio_lang(release_title):
    release_title = cleanTitle(release_title)
    if any(i in release_title for i in ['dual audio']):
        lang = 1
    elif any(i in release_title for i in ['dub', 'dubbed']):
        lang = 2
    else:
        lang = 0
    return lang


def getQuality(release_title):
    release_title = release_title.lower()
    if '4k' in release_title or '2160' in release_title:
        quality = 4
    elif '1080' in release_title:
        quality = 3
    elif '720' in release_title:
        quality = 2
    else:
        quality = 1
    return quality


def getInfo(release_title):
    info = []
    release_title = cleanTitle(release_title)
    # info.video
    if any(i in release_title for i in ['x264', 'x 264', 'h264', 'h 264', 'avc']):
        info.append('AVC')
    if any(i in release_title for i in ['x265', 'x 265', 'h265', 'h 265', 'hevc']):
        info.append('HEVC')
    if any(i in release_title for i in ['xvid']):
        info.append('XVID')
    if any(i in release_title for i in ['divx']):
        info.append('DIVX')
    if any(i in release_title for i in ['mp4']):
        info.append('MP4')
    if any(i in release_title for i in ['wmv']):
        info.append('WMV')
    if any(i in release_title for i in ['mpeg']):
        info.append('MPEG')
    if any(i in release_title for i in ['remux', 'bdremux']):
        info.append('REMUX')
    if any(i in release_title for i in [' hdr ', 'hdr10', 'hdr 10']):
        info.append('HDR')
    if any(i in release_title for i in [' sdr ']):
        info.append('SDR')

    # info.audio
    if any(i in release_title for i in ['aac']):
        info.append('AAC')
    if any(i in release_title for i in ['dts']):
        info.append('DTS')
    if any(i in release_title for i in ['hd ma', 'hdma']):
        info.append('HD-MA')
    if any(i in release_title for i in ['atmos']):
        info.append('ATMOS')
    if any(i in release_title for i in ['truehd', 'true hd']):
        info.append('TRUEHD')
    if any(i in release_title for i in ['ddp', 'dd+', 'eac3']):
        info.append('DD+')
    if any(i in release_title for i in [' dd ', 'dd2', 'dd5', 'dd7', ' ac3']):
        info.append('DD')
    if any(i in release_title for i in ['mp3']):
        info.append('MP3')
    if any(i in release_title for i in [' wma']):
        info.append('WMA')
    if any(i in release_title for i in ['dub', 'dubbed']):
        info.append('DUB')
    if any(i in release_title for i in ['dual audio']):
        info.append('DUAL-AUDIO')

    # info.channels
    if any(i in release_title for i in ['2 0 ', '2 0ch', '2ch']):
        info.append('2.0')
    if any(i in release_title for i in ['5 1 ', '5 1ch', '6ch']):
        info.append('5.1')
    if any(i in release_title for i in ['7 1 ', '7 1ch', '8ch']):
        info.append('7.1')

    # info.source
    # no point at all with WEBRip vs WEB-DL cuz it's always labeled wrong with TV Shows
    # WEB = WEB-DL in terms of size and quality
    if any(i in release_title for i in ['bluray', 'blu ray', 'bdrip', 'bd rip', 'brrip', 'br rip']):
        info.append('BLURAY')
    if any(i in release_title for i in [' web ', 'webrip', 'webdl', 'web rip', 'web dl']):
        info.append('WEB')
    if any(i in release_title for i in ['hdrip', 'hd rip']):
        info.append('HDRIP')
    if any(i in release_title for i in ['dvdrip', 'dvd rip']):
        info.append('DVDRIP')
    if any(i in release_title for i in ['hdtv']):
        info.append('HDTV')
    if any(i in release_title for i in ['pdtv']):
        info.append('PDTV')
    if any(i in release_title for i in
           [' cam ', 'camrip', 'hdcam', 'hd cam', ' ts ', 'hd ts', 'hdts', 'telesync', ' tc ', 'hd tc', 'hdtc',
            'telecine', 'xbet']):
        info.append('CAM')
    if any(i in release_title for i in ['dvdscr', ' scr ', 'screener']):
        info.append('SCR')
    if any(i in release_title for i in ['korsub', ' kor ', ' hc']):
        info.append('HC')
    if any(i in release_title for i in ['blurred']):
        info.append('BLUR')
    if any(i in release_title for i in [' 3d']):
        info.append('3D')
    return info


def convert_to_bytes(size, units):
    unit = units.upper()
    multiplier = {
        'B': 1,
        'KIB': 1024,
        'MIB': 1024 ** 2,
        'GIB': 1024 ** 3,
        'TIB': 1024 ** 4,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }
    return size * multiplier.get(unit, 1)


def get_size(size=0) -> str:
    power = 1024.0
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power:
        size /= power
        n += 1
    return '{0:.2f} {1}'.format(size, power_labels[n])


def get_cache_check_reg(episode: str):
    season = ''
    reg_string = r'''(?ix)                              # Ignore case (i), and use verbose regex (x)
                 (?:                                    # non-grouping pattern
                   s|season                             # s or season
                   )?
                 ({})?                                  # season num format
                 (?:                                    # non-grouping pattern
                   e|x|episode|ep|ep\.|_|-|\(           # e or x or episode or start of a line
                   )                                    # end non-grouping pattern
                 \s*                                    # 0-or-more whitespaces
                 (?<![\d])
                 ({}|{}|{})                             # episode num format: xx or xxx or xxxx
                 (?![\d])
                 '''.format(season, episode.zfill(2), episode.zfill(3), episode.zfill(4))
    return re.compile(reg_string)


def get_best_match(dict_key, dictionary_list, episode: str, pack_select=False) -> dict:
    regex = get_cache_check_reg(episode)
    all_files = []
    pattern = re.compile(r'\[.*?\]')
    for item in dictionary_list:
        i = item.copy()
        path = pattern.sub('', i[dict_key].rsplit('/')[-1])
        i['regex_matches'] = regex.findall(path)
        i['short_name'] = i.get('short_name', '').removeprefix('[CR]').strip()
        all_files.append(i)
    if not all_files:
        return {}
    if pack_select:
        files = user_select(all_files, dict_key)
    else:
        files = [i for i in all_files if len(i['regex_matches']) > 0]
        if not files:
            files = user_select(all_files, dict_key)
        else:
            files.sort(key=lambda x: len(' '.join(list(x['regex_matches'][0]))), reverse=True)
            if len(files) != 1:
                files = user_select(files, dict_key)
    return files[0]


def filter_sources(list_, season: int, episode: int, _id=None, titles=None) -> list:
    regex_season = r"(?i)\b(?:s(?:eason)?[\s._-]?(\d{1,2})|(\d{1,2})(?:st|nd|rd|th)?[\s._-]?s(?:eason)?)(?:(?=[^0-9a-z])|(?=[ex])|$)"
    rex_season = re.compile(regex_season)

    regex_ep = r"(?i)(?:s(?:eason)?\s?\d{1,2})?[ ._-]?(?:e(?:p)?\s?(\d{1,4})(?:v\d+)?)?(?:[ ._-]?[-~][ ._-]?e?(?:p)?\s?(\d{1,4}))?|(?:-\s?(\d{1,4})\b)"
    rex_ep = re.compile(regex_ep)

    filtered_list= []

    if titles:
        fuzz_titles = [t.lower() for t in titles]
    else:
        fuzz_titles = None
    for torrent in list_:
        title = torrent['name'] if isinstance(torrent, dict) else torrent
        title = clean_torrent(title)

        # filter episode number
        ep_match = [int(g) for m in rex_ep.finditer(title) for g in m.groups() if g]
        if ep_match and ep_match[0] != episode:
            if not (len(ep_match) > 1 and ep_match[0] <= episode <= ep_match[1]):
                continue

        # filter season
        if not _id:
            season_match = [int(g) for m in rex_season.finditer(title) for g in m.groups() if g]
            if season_match and season:
                if not (season_match[0] <= int(season) <= season_match[-1]):
                    continue

        # filter out junk
        if fuzz_titles:
            best_ratio = max(difflib.SequenceMatcher(None, title, t).ratio() for t in fuzz_titles)
            if best_ratio < 0.3:
                continue
        filtered_list.append(torrent)
    return filtered_list


def clean_title(text: str) -> str:
    text = re.sub(r'\s*\([^)]*\)', '', text.lower())
    return text


def clean_torrent(text):
    text = text.lower()
    patterns = [
        r"\b(?:360p|480p|720p|1080p|2160p|4k)(?!\d)",
        r"\b10\s?bits?\b",
        r"\b(?:h\.?\s?264|x\.?\s?264|h\.?\s?265|x\.?\s?265|hevc|avc|hls)(?!\d)",
        r"\b(?:web-dl|webrip|bluray|hdrip|dvdrip|hdtv|pdtv|cam|screener)\b",
        r"\b(?:hdr10|hdr|sdr|dv|dolby vision|dovi)\b",
        r"\b(?:mp4|vp9|av1|mpeg|xvid|divx|wmv|flac)\b",
        r"\b(?:aac|mp3|opus|ddp|dd(?:\s?(?:2|5|7))|ac3|dts(?:-hdma|-hdhr|-x)?|atmos|truehd)(?:\d+(?:\.\d+)?)?\b",
        r"\b(?:1\.0|2\.0|5\.1|7\.1|2ch|5ch|7ch|8ch)\b",
        r"\b(?:3d|60[-\s]?fps)\b",
        r"\b(?:multi audio|dual audio|dub(?:bed)?|multi sub|batch|complete series)\b"
    ]
    combined_pattern = "|".join(patterns)
    text = re.sub(combined_pattern, '', text)
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    # text = re.sub(r"[:/,!?()'\"\\\[\]_.]", " ", text)
    text = re.sub(r"[:/,!?()'\"\\\[\]_.|~-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cleanTitle(title: str) -> str:
    title = title.lower()
    result = ''.join(char for char in title if char in string.printable)
    title = result.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
    apostrophe_replacement = 's'
    title = title.replace("\\'s", apostrophe_replacement)
    title = title.replace("'s", apostrophe_replacement)
    title = title.replace("&#039;s", apostrophe_replacement)
    title = title.replace(" 039 s", apostrophe_replacement)
    title = re.sub(r'[:/,!?()\'"\\\[\]\-_.]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'&', 'and', title)
    return title.strip()


def is_file_ext_valid(file_name: str) -> bool:
    return False if '.' + file_name.split('.')[-1] not in video_ext() else True


def video_ext():
    COMMON_VIDEO_EXTENSIONS = xbmc.getSupportedMedia('video').rsplit('|')
    COMMON_VIDEO_EXTENSIONS = [i for i in COMMON_VIDEO_EXTENSIONS if i != '' and i != '.zip']
    return COMMON_VIDEO_EXTENSIONS


def user_select(files, dict_key) -> list:
    idx = control.select_dialog('Select File', [i[dict_key].rsplit('/')[-1] for i in files])
    if idx == -1:
        file = [{'path': ''}]
    else:
        file = [files[idx]]
    return file
