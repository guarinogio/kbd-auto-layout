# Release Checklist

## Pre-release

- [ ] Update version in:
  - pyproject.toml
  - src/kbd_auto_layout/__init__.py
  - debian/changelog
- [ ] Update CHANGELOG.md
- [ ] Run tests
  ```bash
  make format
  make lint
  make test
  ```

## Build

```bash
debuild -us -uc
```

## Install test

```bash
sudo apt install --reinstall ../kbd-auto-layout_*.deb
kbd-auto-layoutctl --version
```

## Git

```bash
git add .
git commit -m "release: vx.y.z"
git tag -a vx.y.z -m "vx.y.z"
git push
git push origin vx.y.z
```

## GitHub Release

```bash
gh release create vx.y.z ../kbd-auto-layout_*_all.deb --title "vx.y.z" --generate-notes
```

## Post-release

- [ ] Verify download works
- [ ] Verify install instructions
- [ ] Announce (optional)
