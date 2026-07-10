# University Tracker

## Phone-ready version (recommended)

`mobile_pwa/` is the responsive **Study Flow** version. It is a private,
offline-first web app: its data stays in the browser on the device and it has
JSON export/import backups. GitHub Pages serves it over HTTPS so it can be
installed as a Progressive Web App on iPhone, iPad, and other supported devices.

### Install on iPhone or iPad

1. Open [Laura's Study Flow](https://lauracontrerasx-code.github.io/University/)
   in Safari. Recent iOS versions can also offer the same action from Chrome.
2. Tap the **Share** button.
3. Tap **Add to Home Screen**. If it is not visible, scroll down or choose
   **Edit Actions** to add it.
4. Keep the name **Study Flow**, then tap **Add**.
5. Open Study Flow once while online so its files are cached for offline use.

The app's records are saved only in that installed app/browser on that device.
Use **Menu > Export backup** regularly, especially before clearing browser data
or changing phones. Import the JSON backup from the same menu when needed.

For a quick local preview, run:

```powershell
python run_mobile.py
```

Then open the phone address printed by the script while your computer and phone
are on the same Wi-Fi. Local network HTTP is useful for visual testing, but iOS
installation and service-worker testing must use the deployed HTTPS GitHub Pages
site (or localhost on the same device).

The prior desktop UI is preserved in `backups/desktop-ui-20260709-195841/` and
the original desktop source is still in `university_tracker/`.

---

## Legacy desktop version

A local-only desktop app for tracking university subjects, topics, homework, grades, and deadlines.

The app uses:

- Python
- PySide6 for the desktop interface
- SQLite for local storage

No server, login, or online sync is required. Your data is stored in `data/university_tracker.sqlite`.

## Features

- Signatures with name, semester, professor, teacher email, and schedule
- Signatures view with grading, topics, and homeworks managed inside each signature
- Topics linked to signatures with pending, studying, or seen status
- Editable grading categories per signature, each with its own percentage weight
- Homework linked to signatures and grading categories, with due dates, status, optional grade, and notes/link references
- Category-based grade calculations with a prominent overall grade per signature
- Colombian grading scale from 1.0 to 5.0, where 1.0-2.9 is Lost and 3.0-5.0 is Pass
- Dashboard with upcoming homework, calculated grades, and important deadlines
- Main navigation for Home, Dashboard, and Signatures
- Full-screen home menu with large buttons for Dashboard, Homeworks, Signatures, and Grades
- Sample data created automatically on first launch

## Project Structure

```text
university_tracker/
  app.py          # PySide6 desktop interface
  database.py     # SQLite schema, seed data, and database functions
  __init__.py
data/
  university_tracker.sqlite  # Created automatically when you run the app
run.py
requirements.txt
README.md
```

## Setup

Install Python 3.11 or newer from https://www.python.org/downloads/.

Then open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

If Windows says `python` was not found, install Python from python.org and make sure the installer option **Add python.exe to PATH** is enabled.

## Reset Sample Data

To start fresh, close the app and delete:

```text
data/university_tracker.sqlite
```

The app will create a new database with sample data the next time it starts.
