import xbmcvfs
import requests

import shutil
from resources.lib.ui import control
from pathlib import Path


def download_zip(url: str, path: Path) -> None:
    r = requests.get(url)
    with open(path, 'wb') as file:
        file.write(r.content)


def create_package(provider_name: str, p: Path) -> None:
    proider_path = Path.cwd() / 'here' / p.name
    Path.mkdir(proider_path, parents=True, exist_ok=True)
    with open(proider_path / '__init__.py', 'w'):
        pass
    source_providers = proider_path / provider_name
    if source_providers.exists():
        shutil.rmtree(source_providers)
        control.log(f'deleted {provider_name} from {p.name}')
    shutil.move(p / provider_name, proider_path)


def main():
    url = 'http://bit.ly/a4kScrapers'
    temp_path = control.dataPath / 'temp.zip'
    download_zip(url, temp_path)
    if not temp_path.exists():
        return
