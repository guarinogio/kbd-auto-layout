# Release Checklist

## Pre-release

- [ ] Update version in:
  - `pyproject.toml`
  - `src/kbd_auto_layout/__init__.py`
  - `debian/changelog`
- [ ] Update `CHANGELOG.md`
- [ ] Update release notes file
- [ ] Run checks

```bash
make format
make lint
make test
```

## Build

```bash
rm -rf .pybuild build dist src/*.egg-info
find . -type d -name __pycache__ -prune -exec rm -rf {} +
debuild -us -uc
```

## Install test

```bash
sudo dpkg -i ../kbd-auto-layout_*.deb
kbd-auto-layoutctl --version
kbd-auto-layoutctl doctor
```

## Git

```bash
git add .
git commit -m "release: prepare vx.y.z"
git tag -a vx.y.z -m "vx.y.z"
git push
git push origin vx.y.z
```

## GitHub Release

```bash
gh release create vx.y.z ../kbd-auto-layout_*_all.deb --title "vx.y.z" --notes-file RELEASE_NOTES_x.y.z.md
```

## Post-release

- [ ] Verify the GitHub Release asset downloads correctly
- [ ] Verify install instructions from README
- [ ] Verify the packaged service can be enabled by users
