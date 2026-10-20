# Desktop background updates implementation plan

Approved behavior: automatically download stable releases, classify patch versus feature
versions, and let the user restart to apply. Existing portable builds need one manual
upgrade to acquire this updater. This release uses version 0.2.0.

- [x] Test and implement version classification, bounded HTTPS downloads, release SHA-256
  validation, ZIP path and size checks, and staged version verification in updater.py.
- [x] Add an external PowerShell helper, bundled with PyInstaller, that waits for the old
  process, swaps the portable directory, smoke tests the new EXE, and restores the backup
  on failure. Never execute replacement code while the old app is running.
- [x] Integrate worker events and a restart button into desktop.py. Keep update events on
  disconnect; block apply during Google requests; clean up session before closing.
- [x] Update release packaging and README; test failures, hostile archives, UI event flow,
  and the Windows helper with isolated fixture applications, then build/smoke test ZIP.

The distribution source is the public GitHub repository over verified HTTPS. SHA-256
detects corrupted/inconsistent assets; it is not an independent publisher signature.
No OAuth secrets or Google proxy credentials go to GitHub. Updates download a complete
portable package internally; this is not binary delta patching or live code injection.

Validation: 59 tests passed, including real Windows fixture EXE replacement, rollback,
and waiting for the old process. PyInstaller build and packaged EXE smoke test passed.
GitHub publication and a live upgrade between published releases were not performed.
