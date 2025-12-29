# Developer Setup Guide  
### Building FancyClock as a Flatpak

This document describes all prerequisites and steps required to build
FancyClock inside a Flatpak using the script:

```bash
./build_flatpak.sh
```

The Flatpak build is **offline** for Python dependencies, meaning all wheels and
sdists must be pre-populated into a local `vendor/` directory.

Follow this guide on any machine before running the build.

---

## 1. System Requirements

### 1.1 Install Flatpak and the KDE SDK runtime

FancyClock builds against KDE Runtime 6.8.

Install the following (one-time setup):

```bash
flatpak install flathub org.kde.Sdk//6.8
flatpak install flathub org.kde.Platform//6.8
```

These provide:

- Python 3.12 inside the sandbox
- Qt 6 frameworks
- ffmpeg backend for video skins  
- SDK tools needed for building krb5

---

## 2. Install Git LFS (required for MP4 skins)

FancyClock’s animated backgrounds are stored using **Git LFS**.  
If LFS is not installed, the `media/*.mp4` files will be *pointer stubs* and video
skins will fail.

Install Git LFS for your platform:

**Ubuntu / Debian / Mint / Pop!_OS:**

```bash
sudo apt install git-lfs
```

**Fedora:**

```bash
sudo dnf install git-lfs
```

**Arch / Manjaro:**

```bash
sudo pacman -S git-lfs
```

Then initialize LFS:

```bash
git lfs install
git lfs fetch --all
git lfs checkout   # Replace LFS pointer files with actual MP4 assets
```

Verify:

```bash
ls -lh media/*.mp4   # Files should be large (MB), not 130 bytes
```

---

## 3. Python Environment for Generating `vendor/`

FancyClock’s Flatpak build installs Python dependencies **offline** using wheels
stored in `vendor/`.  
You must generate these wheels before building.

Create a venv:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Code quality checks:

```bash
python -m black .
python -m flake8 .
python -m pytest
```

Upgrade pip:

```bash
pip install --upgrade pip
```

---

## 4. Generate the `vendor/` directory

The Flatpak build uses:

```bash
python3 -m pip install --no-index --find-links=vendor --prefix=/app -r requirements.txt
```

So all required packages must exist locally.

Rebuild `vendor/` from scratch as follows:

```bash
rm -rf vendor
mkdir -p vendor

pip download -r requirements.txt -d vendor
```

### 4.1 Fix charset_normalizer incompatibility

The Flatpak runtime uses **Python 3.12**, so if pip downloaded a CPython-specific
wheel for `charset_normalizer`, replace it with a universal sdist:

```bash
rm vendor/charset_normalizer-*.whl
pip download --no-binary=charset_normalizer "charset_normalizer<4,>=2" -d vendor
```

After this, `vendor/` should contain:

- PySide6 wheels  
- shiboken6 wheels  
- pyside6-addons & essentials  
- babel, pytz, requests, idna, urllib3, certifi  
- tzlocal  
- charset_normalizer (as `.tar.gz`)

---

## 5. Krb5 Native Dependency (for QtMultimedia)

QtMultimedia requires `libgssapi_krb5.so.2`.  
The Flatpak manifest automatically builds this via an embedded `krb5` module:

```yaml
modules:
  - name: krb5
    # ...
```

You do **not** need to install krb5 manually.

---

## 6. Build the Flatpak

Once:

- Git LFS assets are retrieved  
- `vendor/` contains all Python deps  
- Flatpak runtimes are installed

Run:

```bash
./build_flatpak.sh
```

This will:

1. Build krb5 inside the sandbox  
2. Install Python wheels from `vendor/`  
3. Copy app files, media, translations, LICENSE  
4. Package and install the app locally

Run the result:

```bash
flatpak run uk.codecrafter.FancyClock
```

---

## 7. Troubleshooting

### 7.1 Video skins show “moov atom not found”

Your MP4s are Git LFS pointer files.  
Run:

```bash
git lfs fetch --all
git lfs checkout
```

### 7.2 Missing charset_normalizer

Ensure the universal sdist exists:

```bash
ls vendor/charset_normalizer-*.tar.gz
```

### 7.3 Build cannot reach PyPI

Correct — this is intentional.  
Rebuild your `vendor/` directory following Section 4.

---

## 8. Summary Checklist

Before running `./build_flatpak.sh`:

- [ ] Git LFS installed  
- [ ] Real MP4 files present (not pointer files)  
- [ ] Python venv created  
- [ ] `vendor/` generated with `pip download`  
- [ ] charset_normalizer sdist included  
- [ ] Flatpak runtimes installed (SDK + Platform 6.8)  

Then:

```bash
./build_flatpak.sh
flatpak run uk.codecrafter.FancyClock
```

---

## 9. Regenerate vendor quickly

To fully regenerate:

```bash
rm -rf vendor
source venv/bin/activate
pip download -r requirements.txt -d vendor
rm vendor/charset_normalizer-*.whl
pip download --no-binary=charset_normalizer "charset_normalizer<4,>=2" -d vendor
```

---

_End of document._

---

# 10. Installing, Running, and Uninstalling the Flatpak Build

Once you have built the Flatpak bundle, you can install, run, and uninstall it easily.

## Install with:
```bash
flatpak install dist/FancyClock.flatpak
```

## Run with:
```bash
flatpak run uk.codecrafter.FancyClock
```

## Uninstall with:
```bash
flatpak uninstall uk.codecrafter.FancyClock
```

These commands allow developers to install and test FancyClock exactly as an end user would.

---
