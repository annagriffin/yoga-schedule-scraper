# 🧘 Yoga Class Calendar Sync

Automatically sync yoga class schedules from the Yoga Pod Boulder (and optionally other locations) to a Google Calendar — every week, reliably and transparently.

---

## 📌 Overview

This tool scrapes upcoming yoga classes from the public Yoga Pod Boulder schedule and pushes them to a designated Google Calendar, keeping your calendar updated with accurate class times, teachers, and descriptions.

It is designed to:

- Detect and update existing events with changes.
- Avoid duplicating entries.
- Filter out non-public or internal listings (like “Front Desk Staff” or “Silent Practice”).
- Automatically delete previously synced events for the upcoming week.
- Log each sync action to an artifact file when run via GitHub Actions.

---

## 🛠️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/yoga-schedule-scraper.git
cd yoga-schedule-scraper
```

### 2. Set up your virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🔐 Configuration

.env File (for local development)
Create a .env file in the root of the project:

```
BOULDER_YOGA_CALENDAR_ID=your_calendar_id_here
TABLE_MESA_YOGA_CALENDAR_ID=optional_other_calendar
```

> Note: Your .env file is ignored by Git to protect sensitive data.

## 🔑 Google Calendar API

Follow the [Google Calendar API Python Quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python) to create and authorize your credentials.

Steps:

1. Visit the [Google Calendar API Quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python) and click **"Enable the Google Calendar API"**.
2. Download the `credentials.json` file and save it in the root of your project (this file is gitignored).
3. On your first local run, a browser window will open asking for authorization.
4. Once you authorize, a `token.json` file will be created — this file stores your access and refresh tokens.

> **Tip:** You'll only need to do this once locally. For GitHub Actions, you'll encode and upload these files as secrets (see below).

## 🚀 Running Locally

```
python create_event.py
```

## 🤖 GitHub Actions (Automated Sync)

### 📁 .github/workflows/sync.yml

Includes:

- A scheduled weekly sync (Fridays at 8am MT).
- A manual trigger via the GitHub Actions tab.
- Upload of a log artifact showing changes made during the sync.

### 🔐 GitHub Secrets

Set the following in your repo’s Settings → Secrets and variables → Actions → Repository secrets:

`BOULDER_YOGA_CALENDAR_ID`

`TABLE_MESA_YOGA_CALENDAR_ID`

`CREDENTIALS_JSON` (base64-encoded credentials.json)

`TOKEN_JSON` (base64-encoded token.json)

Encode locally like this:

```
base64 -i credentials.json | pbcopy
base64 -i token.json | pbcopy
```

## 📂 Outputs

When run via GitHub Actions, the script will upload a file named action_output_log.txt showing:

- Created events
- Updated events
- Skipped (unchanged) events
- Any errors or sync messages

You can find it under the Artifacts section of the GitHub Action run.

## 🧼 Privacy and Security

`.env`, `token.json`, and `credentials.json` are excluded from version control.
Use `.gitignore` for sensitive files.
All configuration should use environment variables to avoid leaks.

## 🏗️ Future Support

- Multiple locations (e.g., Longmont)
- Schedule previews via a web interface
- Slack or email notifications on sync

## 📄 License

MIT License. See LICENSE file for details.
