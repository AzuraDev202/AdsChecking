"""Public desktop release metadata; never uses Google credentials or proxy."""
import re

import httpx

APP_VERSION = '0.2.1'
REPOSITORY = 'https://github.com/AzuraDev202/AdsChecking'
DOWNLOAD_URL = REPOSITORY + '/releases/latest/download/AdsChecking-windows-x64.zip'
RELEASE_API = 'https://api.github.com/repos/AzuraDev202/AdsChecking/releases/latest'


def version_tuple(value):
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value)
    if not match:
        raise ValueError('Expected a stable version such as v1.2.3')
    return tuple(map(int, match.groups()))


def check_update():
    """Return (version, pinned ZIP URL), or None when no newer ZIP exists."""
    with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
        response = client.get(RELEASE_API, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'AdsChecking/' + APP_VERSION,
        })
        if response.status_code == 404:
            return None
        response.raise_for_status()
        release = response.json()
    if release.get('draft') or release.get('prerelease'):
        return None
    tag = release['tag_name']
    if version_tuple(tag) <= version_tuple(APP_VERSION):
        return None
    expected = REPOSITORY + '/releases/download/' + tag + '/AdsChecking-windows-x64.zip'
    for asset in release.get('assets', []):
        if (asset.get('name') == 'AdsChecking-windows-x64.zip'
                and asset.get('state') == 'uploaded'
                and asset.get('size', 0) > 0
                and asset.get('browser_download_url') == expected):
            return tag, expected
    raise ValueError('Release ZIP is not available')
