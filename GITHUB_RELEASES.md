# GitHub Releases plan for kbd-auto-layout

This document prepares the repository for distributing Debian packages through GitHub Releases.

## What this gives you

- tagged versions in Git
- a repeatable release flow
- a `.deb` attached to each GitHub Release
- clear install instructions for users

## Suggested release flow

1. Update the project version:
   - `pyproject.toml`
   - `src/kbd_auto_layout/__init__.py`
   - `debian/changelog`
2. Run quality checks:
   - `make format`
   - `make lint`
   - `make test`
   - `debuild -us -uc`
3. Commit and tag the release
4. Create the GitHub Release and upload the `.deb`

## Manual release commands

Example for version `0.1.1`:

```bash
git add .
git commit -m "release: v0.1.1"
git tag -a v0.1.1 -m "v0.1.1"
git push
git push origin v0.1.1
gh release create v0.1.1 ../kbd-auto-layout_0.1.1_all.deb --title "v0.1.1" --notes-file CHANGELOG.md
```

## Recommended GitHub Actions workflow

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install packaging dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            devscripts debhelper dh-python pybuild-plugin-pyproject \
            python3-all python3-setuptools build-essential lintian

      - name: Build Debian package
        run: debuild -us -uc

      - name: Upload release asset
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release create "$GITHUB_REF_NAME" ../kbd-auto-layout_*_all.deb --title "$GITHUB_REF_NAME" --generate-notes
```

## User installation instructions for Releases

Users should download the `.deb` from the GitHub Release page and run:

```bash
sudo apt install ./kbd-auto-layout_VERSION_all.deb
systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Recommended repository checklist

- Keep `README.md` focused on install and usage
- Keep `CHANGELOG.md` updated for each release
- Keep `debian/changelog` aligned with the package version
- Tag each released version in Git
- Attach the built `.deb` to the corresponding GitHub Release
- Do not commit Debian build artifacts

## Nice next steps

- add a screenshot or demo GIF to the repository
- add a `CONTRIBUTING.md`
- add issue templates
- add a release checklist file for maintainers
