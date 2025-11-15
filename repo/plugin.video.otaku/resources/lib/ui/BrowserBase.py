import re
import json
import requests
import xbmcvfs

from resources.lib.ui import control, utils


class BrowserBase:
    _BASE_URL = None

    @staticmethod
    async def send_request(url, params=None):
        return requests.get(url, params)

    @staticmethod
    def handle_paging(hasnextpage: bool, base_url: str, page: int) -> list:
        if not hasnextpage or not control.is_addon_visible() and control.getBool('widget.hide.nextpage'):
            return []
        next_page = page + 1
        name = "Next Page (%d)" % next_page
        return [utils.allocate_item(name, base_url % next_page, True, False, [], 'next.png', {'plot': name}, 'next.png')]

    @staticmethod
    def open_completed() -> dict:
        if xbmcvfs.exists(control.completed_json):
            with open(control.completed_json) as file:
                completed = json.load(file)
        else:
            completed = {}
        return completed

    @staticmethod
    def duration_to_seconds(duration_str: str) -> int:
        # Regular expressions to match hours, minutes, and seconds
        hours_pattern = re.compile(r'(\d+)\s*hr')
        minutes_pattern = re.compile(r'(\d+)\s*min')
        seconds_pattern = re.compile(r'(\d+)\s*sec')

        # Extract hours, minutes, and seconds
        hours_match = hours_pattern.search(duration_str)
        minutes_match = minutes_pattern.search(duration_str)
        seconds_match = seconds_pattern.search(duration_str)

        # Convert to integers, default to 0 if not found
        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0
        seconds = int(seconds_match.group(1)) if seconds_match else 0

        # Calculate total duration in seconds
        total_seconds = hours * 3600 + minutes * 60 + seconds

        return total_seconds

    @staticmethod
    def _clean_title(text: str) -> str:
        return text.replace(u'×', ' x ')

    @staticmethod
    def clean_embed_title(text: str) -> str:
        return re.sub(r'\W', '', text).lower()

    @staticmethod
    def _sphinx_clean(text: str) -> str:
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
    def get_quality(qual):
        if qual > 1080:
            quality = 4
        elif qual > 720:
            quality = 3
        elif qual > 480:
            quality = 2
        elif qual > 360:
            quality = 1
        else:
            quality = 0
        return quality

    @staticmethod
    def embeds() -> list:
        # return [
        #     'doodstream', 'filelions', 'filemoon', 'hd-2', 'iga', 'kwik',
        #     'megaf', 'moonf', 'mp4upload', 'mp4u', 'mycloud', 'noads', 'noadsalt',
        #     'swish', 'streamtape', 'streamwish', 'vidcdn', 'vidplay', 'vidstream',
        #     'yourupload', 'zto']
        return control.getStringList('embed.config')