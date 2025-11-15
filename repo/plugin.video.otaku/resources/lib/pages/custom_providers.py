import xbmcvfs
import requests

import json
import shutil
from resources.lib.ui import control
from pathlib import Path


def download_zip(url: str, path: Path) -> None:
    r = requests.get(url)
    xbmcvfs.mkdirs(path.parent.as_posix())
    with open(path, 'wb') as file:
        file.write(r.content)


def create_package(provider_name: str, p: Path) -> None:
    proider_path = control.dataPath / p.name
    Path.mkdir(proider_path, parents=True, exist_ok=True)
    with open(proider_path / '__init__.py', 'w'):
        pass
    source_providers = proider_path / provider_name
    if source_providers.exists():
        shutil.rmtree(source_providers)
        control.log(f'deleted {provider_name} from {p.name}')
    shutil.move(p / provider_name, proider_path)


def main() -> None:
    url = 'http://bit.ly/a4kScrapers'
    temp_path = Path(control.dataPath) / 'temp'
    temp_zip = temp_path / 'temp.zip'
    download_zip(url, temp_zip)
    if not temp_zip.exists():
        return
    shutil.unpack_archive(temp_zip, temp_path)

    custom_source = None
    p: Path
    for p in temp_path.iterdir():
        if p.is_dir():
            custom_source = p
    if not custom_source:
        return

    for p in custom_source.rglob('*meta.json'):
        with open(p, 'r') as file:
            meta = json.load(file)
        if not meta:
            return
        meta_path = control.dataPath / 'providerMeta' / meta['name']
        Path.mkdir(meta_path, parents=True, exist_ok=True)
        with open(meta_path / "meta.json", 'w') as file:
            json.dump(meta, file, indent=4)

    for p in custom_source.iterdir():
        if p.name in ['providers', 'providerModules', 'providerMedia']:
            create_package(meta['name'], p)

    Path(temp_zip).unlink()
    control.log('deleted temp.zip')
    shutil.rmtree(temp_path)
    control.log(f'deleted temp dir')
