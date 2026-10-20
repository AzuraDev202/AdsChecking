"""Stage verified portable releases; installation is handled outside the running app."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import httpx

from .updates import APP_VERSION, REPOSITORY, version_tuple

MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
ALLOWED_HOSTS = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


def update_kind(version, current=APP_VERSION):
    return 'patch' if version_tuple(version)[:2] == version_tuple(current)[:2] else 'feature'


def release_zip(version):
    version_tuple(version)
    return REPOSITORY + '/releases/download/' + version + '/AdsChecking-windows-x64.zip'


def _download(client, url, destination, limit):
    # Resolve GitHub CDN redirects explicitly, before sending each request.
    for _ in range(6):
        parsed = httpx.URL(url)
        if parsed.scheme != 'https' or parsed.host not in ALLOWED_HOSTS or parsed.userinfo:
            raise ValueError('Unexpected update host')
        with client.stream('GET', url) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                url = str(response.url.join(response.headers['location']))
                continue
            response.raise_for_status()
            total = 0
            with destination.open('wb') as stream:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > limit:
                        raise ValueError('Update exceeds size limit')
                    stream.write(chunk)
            return
    raise ValueError('Too many download redirects')


def _extract(package, destination, version):
    seen = set()
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        if len(entries) > 10000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
            raise ValueError('Archive exceeds size limit')
        for entry in entries:
            name = entry.filename
            parts = PurePosixPath(name).parts
            if (not parts or parts[0] != 'AdsChecking' or '\\' in name
                    or any(not p or p in ('.', '..') or any(c in p for c in ':<>"|?*') or p.rstrip(' .') != p
                           or re.fullmatch(r'(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?', p)
                           for p in name.rstrip('/').split('/'))
                    or any(ord(c) < 32 for c in name)
                    or (entry.external_attr >> 16) & 0o170000 == 0o120000
                    or name.casefold() in seen):
                raise ValueError('Unsafe archive entry')
            seen.add(name.casefold())
        archive.extractall(destination)
    app = destination / 'AdsChecking'
    if (not (app / 'AdsChecking.exe').is_file()
            or version_tuple((app / 'VERSION.txt').read_text().strip()) != version_tuple(version)):
        raise ValueError('Incomplete or wrong version package')
    return app


def prepare_update(version, url, cache=None):
    if url != release_zip(version) or version_tuple(version) <= version_tuple(APP_VERSION):
        raise ValueError('Unexpected update release')
    parent = Path(cache) if cache else Path(tempfile.gettempdir())
    job = Path(tempfile.mkdtemp(prefix='adschecking-update-', dir=parent))
    try:
        package, sums = job / 'package.zip', job / 'SHA256SUMS.txt'
        with httpx.Client(timeout=30, trust_env=False, verify=True, follow_redirects=False) as client:
            _download(client, url.rsplit('/', 1)[0] + '/SHA256SUMS.txt', sums, 16384)
            expected = re.findall(r'^([a-fA-F0-9]{64})  AdsChecking-windows-x64\.zip$',
                                  sums.read_text(encoding='utf-8'), re.MULTILINE)
            if len(expected) != 1:
                raise ValueError('Missing release checksum')
            _download(client, url, package, MAX_DOWNLOAD)
        with package.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected[0].lower():
            raise ValueError('Release checksum mismatch')
        staged = _extract(package, job / 'payload', version)
        package.unlink()
        return staged
    except Exception:
        shutil.rmtree(job)
        raise


def discard_update(staged):
    if staged:
        shutil.rmtree(Path(staged).parent.parent, ignore_errors=True)


def launch_installer(staged):
    """Start a helper outside the install directory before exiting the GUI."""
    if not getattr(sys, 'frozen', False) or os.name != 'nt':
        raise ValueError('Automatic install requires the packaged Windows desktop')
    target = Path(sys.executable).resolve().parent
    staged = Path(staged).resolve()
    if not (staged / 'AdsChecking.exe').is_file() or target in staged.parents:
        raise ValueError('Invalid staged update')
    # Fail while the UI is still alive if the parent cannot accept a replacement.
    with tempfile.TemporaryFile(dir=target.parent):
        pass
    job = staged.parent.parent
    script = job / 'install.ps1'
    shutil.copyfile(Path(__file__).with_name('install_update.ps1'), script)
    config = job / 'install.json'
    config.write_text(json.dumps({'target': str(target), 'staged': str(staged),
                                 'pid': os.getpid()}), encoding='utf-8')
    # Paths are passed as process arguments, never interpolated into PowerShell code.
    subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                      'Bypass', '-File', str(script), '-Config', str(config)],
                     cwd=job, creationflags=subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
