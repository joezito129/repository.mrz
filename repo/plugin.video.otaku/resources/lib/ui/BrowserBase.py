import re
import json
import xbmcvfs
import datetime

from resources.lib.ui import control, utils


class BrowserBase:
    _BASE_URL = None

    @staticmethod
    def handle_paging(hasnextpage: bool, base_url: str, page: int) -> list:
        if not hasnextpage or not control.is_addon_visible() and control.getBool('widget.hide.nextpage'):
            return []
        next_page = page + 1
        name = f"Next Page ({next_page})"
        return [utils.allocate_item(name, base_url % next_page, True, False, [], 'next.png', {'plot': name}, 'next.png')]

    @staticmethod
    def open_completed() -> dict:
        if xbmcvfs.exists(control.completed_json):
            with open(control.completed_json, encoding='utf-8') as file:
                completed = json.load(file)
        else:
            completed = {}
        return completed

    @staticmethod
    def get_season_year(offset: int):
        today = datetime.datetime.today()
        current_quarter = (today.month - 1) // 3
        total_quarters = (today.year * 4) + current_quarter + offset
        new_year = total_quarters // 4
        season_index = total_quarters % 4
        seasons = ['WINTER', 'SPRING', 'SUMMER', 'FALL']
        return seasons[season_index], new_year

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
