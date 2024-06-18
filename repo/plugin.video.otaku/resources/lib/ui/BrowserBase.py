from resources.lib.ui import client
from urllib import parse


class BrowserBase:
    _BASE_URL = None

    @staticmethod
    def _clean_title(text):
        return text.replace(u'×', ' x ')

    @staticmethod
    def _sphinx_clean(text):
        text = text.replace('+', r'\+')
        text = text.replace('-', r'\-')
        text = text.replace('!', r'\!')
        text = text.replace('^', r'\^')
        text = text.replace('"', r'\"')
        text = text.replace('~', r'\~')
        text = text.replace('*', r'\*')
        text = text.replace('?', r'\?')
        text = text.replace(':', r'\:')
        return text

    @staticmethod
    def get_size(size=0):
        power = 1024.0
        n = 0
        power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
        while size > power:
            size /= power
            n += 1
        return '{0:.2f} {1}'.format(size, power_labels[n])

    @staticmethod
    def _get_request(url, data=None, headers=None, XHR=False):
        if data:
            url = "%s?%s" % (url, parse.urlencode(data))
        return client.request(url, post=None, headers=headers, XHR=XHR)

    @staticmethod
    def _send_request(url, data=None, headers=None, XHR=False):
        return client.request(url, post=data, headers=headers, XHR=XHR)

    @staticmethod
    def embeds():
        return [
            'doodstream', 'filelions', 'filemoon', 'iga', 'kwik', 'hd-2',
            'mp4upload', 'mycloud', 'streamtape', 'streamwish', 'vidcdn',
            'vidplay', 'yourupload', 'zto'
        ]
