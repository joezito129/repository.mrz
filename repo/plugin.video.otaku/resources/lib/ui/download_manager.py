import math
import os
import time
import requests
import xbmcvfs

from resources.lib.ui import control
from urllib import parse

CLOCK = time.time
VALID_SOURCE_TYPES = ["torrent", "hoster", "cloud", "direct"]


class DownloadTask:
    download_init_status = {
        "speed": "0 B/s",
        "progress": "0",
        "filename": "",
        "eta": "99h",
        "filesize": "0",
        "downloaded": "0",
    }
    def __init__(self, filename=None):
        self.storage_location = control.getSetting('download.location')
        if not xbmcvfs.exists(self.storage_location):
            xbmcvfs.mkdir(self.storage_location)

        self.file_size = -1
        self.file_size_display = None
        self.progress = -1
        self.speed = -1
        self.remaining_seconds = -1
        self._output_path = None
        self._canceled = False
        self.bytes_consumed = 0
        self.output_filename = filename
        self._start_time = CLOCK()
        self.status = "Starting"

    def download(self, url):
        """

        :param url: Web Path to file eg:(http://google.com/images/randomimage.jpeg)
        :return: Bool - True = Completed successfully / False = Cancelled
        """

        if self.output_filename is None:
            self.output_filename = url.split("/")[-1]
            self.output_filename = parse.unquote(self.output_filename)
        self._output_path = os.path.join(self.storage_location, self.output_filename)

        yesno = control.yesno_dialog(control.ADDON_NAME, f'''
Do you want to download "[I]{self.output_filename}[/I]" to:
    {self._output_path[:50]}
    {self._output_path[50:100]}
''')
        if not yesno:
            return False

        control.log(f"Downloading {url} to {self._output_path}")

        self.progress = 0
        self.speed = 0
        self.status = "downloading"

        head = requests.head(url, allow_redirects=True)
        self.file_size = int(head.headers.get("content-length", None))
        self.file_size_display = self.get_display_size(self.file_size)

        r = requests.get(url, stream=True)
        chunks = r.iter_content(chunk_size=1024 * 1024 * 8)

        control.notify(control.ADDON_NAME, 'Download Started')
        control.progressDialog.create(control.ADDON_NAME, 'Downlaod Starting')

        with open(self._output_path, 'wb') as f:
            for chunk in chunks:
                if control.progressDialog.iscanceled():
                    self._canceled = True
                    break
                if chunk:
                    f.write(chunk)
                    self._update_status(len(chunk))
                    control.progressDialog.update(self.progress, f'''
Progress:   {self.progress}%            eta:  {self.get_remaining_time_display()}
Speed:      {self.get_display_speed()}                  
Downloaded: {self.get_display_size(self.bytes_consumed)}
filesize:   {self.file_size_display}
''')
        if self._canceled:
            control.progressDialog.close()
            os.remove(self._output_path)
            control.ok_dialog(control.ADDON_NAME, "Download Canceled")
        else:
            control.log(f"Download complete: {self._output_path}")
            control.ok_dialog(control.ADDON_NAME, "Download Complete")
        return not self._canceled

    def _update_status(self, chunk_size):

        """
        :param chunk_size: int
        :return: None
        """

        self.bytes_consumed += chunk_size
        self.progress = int((float(self.bytes_consumed) / self.file_size) * 100)
        self.speed = self.bytes_consumed / (CLOCK() - self._start_time)
        self.remaining_seconds = float(self.file_size - self.bytes_consumed) / self.speed

    @staticmethod
    def get_display_size(size_bytes):
        size_names = ("B", "KB", "MB", "GB", "TB")
        size = 0.0
        name_idx = 0

        if size_bytes is not None and size_bytes > 0:
            name_idx = int(math.floor(math.log(size_bytes, 1024)))
            if name_idx > (last_size_value := len(size_names) - 1):
                name_idx = last_size_value
            chunk = math.pow(1024, name_idx)
            size = round(size_bytes / chunk, 2)

        return f"{size} {size_names[name_idx]}"

    def get_display_speed(self):

        """
        Returns a display friendly version of the current speed
        :return: String
        """

        speed = self.speed
        speed_categories = ["B/s", "KB/s", "MB/s"]
        if self.progress >= 100:
            return "-"
        for i in speed_categories:
            if speed < 1024:
                return f"{self.safe_round(speed, 2)} {i}"
            else:
                speed = speed / 1024

    def get_remaining_time_display(self):
        """
        Returns a display friendly version of the remaining time
        :return: String
        """

        seconds = self.remaining_seconds
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    @staticmethod
    def safe_round(x, y=0):
        """
        equal rounding, its up to 15 digits behind the comma.

        :param x: value to round
        :type x: float
        :param y: decimals behind the comma
        :type y: int
        :return: rounded value
        :rtype: float
        """
        place = 10**y
        rounded = (int(x * place + 0.5 if x >= 0 else -0.5)) / place
        if rounded == int(rounded):
            rounded = int(rounded)
        return rounded