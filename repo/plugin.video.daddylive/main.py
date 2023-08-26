# -*- coding: utf-8 -*-
import sys
import requests
import xbmcgui
import xbmcplugin
import xbmcaddon
import re
import html
import datetime
import time

from urllib.parse import urlencode, quote, unquote, parse_qsl
   
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.daddylive')

# mode = addon.getSetting('mode')
baseurl = 'https://daddylivehd.com/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0'

ADDON_NAME = addon.getAddonInfo('name')
ADDON_PATH = addon.getAddonInfo('path')
FANART = addon.getAddonInfo('fanart')
ICON = addon.getAddonInfo('icon')


def print(string, *args):
    for i in list(args):
        string = f'{string} {i}'
    xbmcgui.Dialog().textviewer('print', f'{string}')
    del args, string


def get_time(time_string):
    date_now = datetime.datetime.now().date()
    time_string = time_string.replace(':', '')
    date_time = str(date_now) + time_string
    strp_time = datetime.datetime(*(time.strptime(date_time, "%Y-%m-%d%H%M")[0:7])) - datetime.timedelta(hours=5)
    return strp_time.strftime("%I:%M %p")

    
def build_url(query):
    return f'{base_url}?{urlencode(query)}'

def Main_Menu():
    menu = [
        ('LIVE SPORTS','sched'),
        ('LIVE TV','live_tv')
    ]
    for m in menu:
        li = xbmcgui.ListItem(m[0], offscreen=True)
        li.setProperty("IsPlayable", 'false')
        li.setInfo(type='video', infoLabels={'title': '', 'sorttitle': '', 'plot': ''})
        li.setArt({'thumb': '', 'poster': '', 'banner': '', 'icon': ICON, 'fanart': FANART})
        url_li = build_url({'mode': 'menu', 'serv_type': m[1]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_li, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)
    
def Menu_Trans():
    categs=getCategTrans()
    for c in categs:
        li=xbmcgui.ListItem(c, offscreen=True)
        li.setProperty("IsPlayable", 'false')
        li.setInfo(type='video', infoLabels={'title': '', 'sorttitle': '', 'plot': ''})
        li.setArt({'thumb': '', 'poster': '', 'banner': '', 'icon': ICON, 'fanart': FANART})
        url_li = build_url({'mode':'trList', 'trType': c})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_li, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)
        
def getCategTrans():
    headers = {
        'User-Agent':UA
    }
    resp = requests.get(baseurl, headers=headers).text

    blocks = resp.split('<h2 style')
    categs = []
    for b in blocks:
        if 'background-color' in b:
            categ=re.compile('>([^<]+)</h2>').findall(b)
            if len(categ) == 1:
                categs.append(categ[0])
    return categs

def getTransData(categ):
    headers = {
        'User-Agent': UA
    }
    resp = requests.get(baseurl, headers=headers).text
    blocks = resp.split('<h2 style')
    trns = []
    for b in blocks: # transmisje dla danej kategorii
        if 'background-color' in b and categ+'</h2>' in b: #    if 'noopener' in b and '<h4>' in b and categ+'</span></h4>' in b:

            ar_tr = ([v for v in re.findall('(<hr>.*?</span>)', b,re.DOTALL)])

            for a in ar_tr: #dane konkretnej transmisji
                if '<hr>' in a:
                    if ' | ' not in a:  # jedno źródło transmisji
                        ii = a.replace('\n','')
                        title = re.compile('<hr>(.*)<span style').findall(a)[0]
                        try:
                            if title[:1] == '<':
                                re_match = re.match(r'<[^>]+>', title)
                                null, title_right = title.rsplit(re_match.group(0))
                                title = re_match.group(0) + get_time(title_right[:5]) + title_right[5:]
                            else:
                                title = get_time(title[:5]) + title[5:]
                        except ValueError:
                            pass
                        links = re.compile('href=\"(.*)" target').findall(a)
                        srcs = re.compile('\"noopener\">(.*)</a>').findall(a)
                        trns.append([title,links,srcs])
                    else:
                        aa = a.split('</span> | <span')
                        title=re.compile('<hr>(.*)<span style').findall(aa[0])[0]
                        l = []
                        s = []
                        for aaa in aa:
                            links=re.compile('href=\"(.*)" target').findall(aaa)[0]
                            srcs=re.compile('\"noopener\">(.*)</a>').findall(aaa)[0]
                            l.append(links)
                            s.append(srcs)
                        trns.append([title,l,s])
            break
    addon.setSetting('trns',str(trns))
    return trns
    
def TransList(categ):
    trns=getTransData(categ)
    for t in trns:
        title = html.unescape(t[0])
        li = xbmcgui.ListItem(title, offscreen=True)
        li.setInfo(type='video', infoLabels={'title': '', 'sorttitle': '', 'plot': ''})
        li.setArt({'thumb': '', 'poster': '', 'banner': '', 'icon': ICON, 'fanart': FANART})
        li.setProperty("IsPlayable", 'true')
        if len(t[1]) == 1:
            tr = t[1][0] 
            tr = 'https://daddylivehd.sx' + tr if tr.startswith('/') else tr
            url_stream = build_url({'mode':'play', 'url': tr})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_stream, listitem=li, isFolder=False)
        else:
            url_li = build_url({'mode': 'trLinks', 'trData': str(t)})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_li, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def getSource(trData):
    data = eval(unquote(trData))
    select = xbmcgui.Dialog().select('Źródła', data[2])
    if select > -1:
        url_stream = data[1][select]
        url_stream = 'https://daddylivehd.sx' + url_stream if url_stream.startswith('/') else url_stream
        xbmcplugin.setContent(addon_handle, 'videos')
        PlayStream(url_stream)
    else:
        quit()
    return
        
def list_gen():
    base_url = baseurl
    chData=channels()
    for c in chData:   
        li = xbmcgui.ListItem(c[1], offscreen=True)
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': c[1],'sorttitle': '', 'plot': ''})
        li.setArt({'thumb': '', 'poster': '', 'banner': '', 'icon': ICON, 'fanart': FANART})
        url_stream = build_url({'mode': 'play', 'url': base_url+c[0]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_stream, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def channels():
    url=baseurl + '/24-7-channels.php'
    do_adult = xbmcaddon.Addon().getSetting('adult_pw')
    
    headers={
        'Referer': baseurl + '/',
        'user-agent': UA
    }

    resp = requests.post(url, headers=headers).text
        
    ch_block = re.compile('<center><h1(.+?)tab-2', re.MULTILINE | re.DOTALL).findall(str(resp))     
    chan_data = re.compile('href=\"(.*)\" target(.*)<strong>(.*)</strong>').findall(ch_block[0])
    channels = []
    for c in chan_data:
        if not "18+" in c[2] :
            channels.append([c[0],c[2]])
        if do_adult == 'lol' and "18+" in c[2] :
            channels.append([c[0],c[2]])
            
    return channels

def PlayStream(link):
    url = link

    headers = {
        'Referer':baseurl+'/',
        'user-agent':UA
    }
    
    resp = requests.post(url, headers=headers).text
    url_1 = re.compile('iframe src="(.*)" width').findall(resp)[0]
    
    headers={
        'Referer':url,
        'user-agent':UA
    }
    
    resp = requests.post(url_1, headers=headers).text
    stream = re.compile('source:\'(.*)\'').findall(resp)[-1]
    stream_url = stream
    hdr='Referer=' + quote(str(url_1)) + '&User-Agent=' + UA
    play_item = xbmcgui.ListItem(path=stream + '|'+ hdr)
    
    import inputstreamhelper
    PROTOCOL = 'hls'
    is_helper = inputstreamhelper.Helper(PROTOCOL)
    if is_helper.check_inputstream():
        play_item = xbmcgui.ListItem(path=stream)
        play_item.setMimeType('application/x-mpegurl')
        play_item.setContentLookup(False)
        if sys.version_info >= (3,0,0):
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
        else:
            play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        play_item.setProperty('inputstream.adaptive.stream_headers', hdr)        
        play_item.setProperty("IsPlayable", "true")
        play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
    
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
   
def toggle_reuselanguageinvoker(forced_state=None):
    import os
    import xbmc

    def _store_and_reload(output):
        with open(file_path, "w+") as addon_xml_:
            addon_xml_.writelines(output)
        xbmcgui.Dialog().ok(ADDON_NAME, 'Language Invoker option has been changed, reloading kodi profile')
        xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))

    file_path = os.path.join(ADDON_PATH, "addon.xml")

    with open(file_path, "r") as addon_xml:
        file_lines = addon_xml.readlines()

    for i in range(len(file_lines)):
        line_string = file_lines[i]
        if "reuselanguageinvoker" in file_lines[i]:
            if ("false" in line_string and forced_state is None) or ("false" in line_string and forced_state):
                file_lines[i] = file_lines[i].replace("false", "true")
                addon.setSetting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            elif ("true" in line_string and forced_state is None) or ("true" in line_string and forced_state is False):
                file_lines[i] = file_lines[i].replace("true", "false")
                addon.setSetting("reuselanguageinvoker.status", "Disabled")
                _store_and_reload(file_lines)
            break


mode = params.get('mode')

if not mode:
    Main_Menu()
else:
    if mode == 'menu':
        servType = params.get('serv_type')
        if servType == 'sched':
            Menu_Trans()
        if servType == 'live_tv':
            list_gen()
    
    if mode == 'trList':
        transType = params.get('trType')
        TransList(transType)
    
    if mode == 'trLinks':
        trData = params.get('trData')
        getSource(trData)
    
    if mode == 'play':
        link = params.get('url')
        PlayStream(link)

    if mode == 'toggleLanguageInvoker':
        toggle_reuselanguageinvoker()
