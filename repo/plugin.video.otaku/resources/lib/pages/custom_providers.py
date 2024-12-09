import os
import xbmcvfs
import json
import requests

from resources.lib.ui import control

folder_list = ['meta', 'media', 'module', 'provider']


def main():
    create_package()
    control.print('done')


def fetch_data(url):
    r = requests.get(url)


def create_package():
    created_folder = [False, False, False, False]
    for i, x in enumerate(folder_list):
        folder_path = os.path.join(control.dataPath, x)
        if not xbmcvfs.exists(folder_path):
            created_folder[i] = xbmcvfs.mkdir(folder_path)
    return created_folder


def list_packages(meta_path):
    packages = []
    for root, _, files in os.walk(meta_path):
        for filename in files:
            if filename.endswith(".json"):
                with open(os.path.join(root, filename)) as f:
                    meta = json.load(f)
                    try:
                        packages.append((meta["name"], meta["author"], meta["remote_meta"], meta["version"], "|".join(meta.get("services", []))))
                    except KeyError:
                        continue
    return packages
