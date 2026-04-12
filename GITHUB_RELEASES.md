# GitHub Releases

## Build the package

```bash
debuild -us -uc
```

## Create a release manually

```bash
git tag -a vx.y.z -m "vx.y.z"
git push origin vx.y.z
gh release create vx.y.z ../kbd-auto-layout_x.y.z_all.deb --title "vx.y.z" --notes-file RELEASE_NOTES_x.y.z.md
```

## Verify the asset

Use the fixed tag URL format:

```bash
wget https://github.com/guarinogio/kbd-auto-layout/releases/download/vx.y.z/kbd-auto-layout_x.y.z_all.deb
```

For example:

```bash
wget https://github.com/guarinogio/kbd-auto-layout/releases/download/v1.0.5/kbd-auto-layout_1.0.5_all.deb
```

## Install from a release asset

```bash
sudo apt install ./kbd-auto-layout_x.y.z_all.deb
systemctl --user daemon-reload
systemctl --user enable --now kbd-auto-layout.service
```

## Notes

For public download testing, prefer the fixed tag URL over `releases/latest/download/...` until you have confirmed that your release asset naming and publication flow behave exactly as expected.
