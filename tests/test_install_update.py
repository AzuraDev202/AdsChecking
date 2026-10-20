"""Exercise the real Windows helper with harmless fixture EXEs, not the installed app."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest


@pytest.fixture(scope='module')
def fixture_exe(tmp_path_factory):
    root = tmp_path_factory.mktemp('update-fixture')
    source = root / 'fixture.cs'
    source.write_text('''using System;
using System.IO;
using System.Reflection;
class Fixture {
 static int Main(string[] args) {
  string dir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
  if(args.Length == 2 && args[0] == "--smoke-test") {
   if(File.Exists(Path.Combine(dir, "fail.flag"))) return 7;
   File.WriteAllText(args[1], "ok"); return 0;
  }
  File.WriteAllText(Path.Combine(dir, "launched.txt"), File.ReadAllText(Path.Combine(dir, "identity.txt")));
  return 0;
 }
}''')
    exe = root / 'AdsChecking.exe'
    env = dict(os.environ, FIXTURE_SOURCE=str(source), FIXTURE_EXE=str(exe))
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
        'Add-Type -Path $env:FIXTURE_SOURCE -OutputAssembly $env:FIXTURE_EXE -OutputType ConsoleApplication'],
        env=env, capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stderr
    return exe


@pytest.mark.skipif(os.name != 'nt', reason='Windows helper')
@pytest.mark.parametrize('fail', [False, True])
def test_install_or_restore(fixture_exe, tmp_path, fail):
    target = tmp_path / "portable app's folder"
    job = tmp_path / 'job'
    staged = job / 'payload' / 'AdsChecking'
    for directory, identity in [(target, 'old'), (staged, 'new')]:
        directory.mkdir(parents=True)
        shutil.copyfile(fixture_exe, directory / 'AdsChecking.exe')
        (directory / 'identity.txt').write_text(identity)
    if fail:
        (staged / 'fail.flag').touch()
    script = job / 'install.ps1'
    shutil.copyfile(Path('adschecking/install_update.ps1'), script)
    config = job / 'install.json'
    config.write_text(json.dumps({'target': str(target), 'staged': str(staged), 'pid': 2147483000}))
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
        'Bypass', '-File', str(script), '-Config', str(config)],
        capture_output=True, text=True, timeout=50)
    deadline = time.monotonic() + 10
    while not (target / 'launched.txt').exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    log = (job / 'install.log').read_text()
    assert result.returncode == (1 if fail else 0), log + result.stderr
    assert (target / 'launched.txt').read_text() == ('old' if fail else 'new'), log
    assert (target / 'identity.txt').read_text() == ('old' if fail else 'new')
    if not fail:
        backups = list(tmp_path.glob("portable app's folder.backup-*"))
        assert len(backups) == 1
        assert (backups[0] / 'identity.txt').read_text() == 'old'


@pytest.mark.skipif(os.name != 'nt', reason='Windows helper')
def test_helper_waits_for_running_process(fixture_exe, tmp_path):
    target = tmp_path / 'app'
    job = tmp_path / 'job'
    staged = job / 'payload' / 'AdsChecking'
    for directory, identity in [(target, 'old'), (staged, 'new')]:
        directory.mkdir(parents=True)
        shutil.copyfile(fixture_exe, directory / 'AdsChecking.exe')
        (directory / 'identity.txt').write_text(identity)
    script = job / 'install.ps1'
    shutil.copyfile(Path('adschecking/install_update.ps1'), script)
    old = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])
    helper = None
    try:
        config = job / 'install.json'
        config.write_text(json.dumps({'target': str(target), 'staged': str(staged), 'pid': old.pid}))
        helper = subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
            'Bypass', '-File', str(script), '-Config', str(config)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        assert helper.poll() is None
        assert (target / 'identity.txt').read_text() == 'old'
        old.terminate()
        old.wait(timeout=10)
        assert helper.wait(timeout=40) == 0
        assert (target / 'identity.txt').read_text() == 'new'
    finally:
        if old.poll() is None:
            old.terminate()
            old.wait(timeout=10)
        if helper and helper.poll() is None:
            helper.terminate()
            helper.wait(timeout=10)
