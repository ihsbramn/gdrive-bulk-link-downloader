# 📥 Google Drive Bulk Downloader

A fully automated Google Drive downloader with support for:

- ✔ Exporting Google Docs → **.docx**
- ✔ Exporting Google Sheets → **.xlsx**
- ✔ Exporting Google Slides → **.pptx**
- ✔ Exporting Google Drawings → **.png**
- ✔ Downloading binary files (PDF, ZIP, images, etc.)
- ✔ Full recursive **folder download** + auto ZIP
- ✔ Automatic duplicate-skip (no re-download)
- ✔ Per-script Google OAuth token
- ✔ Detailed logging

This script is ideal for pulling files from Google Drive based on URLs stored in a CSV file — especially when working with Jira, project documentation, or bulk Drive exports.

---

## 🚀 Features

- Detects Google Drive file type and exports correctly.
- Supports Google Shared Drives (`supportsAllDrives=true`).
- Handles unlimited nested folders.
- Automatically converts Google formats to Office-compatible files.
- Creates ZIP archives for downloaded folders.
- Fully logs all actions to a log file.
- Automatically detects which CSV column contains links.

---

## 📦 Project Structure

```bash
.
├── script.py # Main script
├── drive_links.csv # Your input CSV file
├── client_secret_xxxx.json # Google OAuth client
├── download.log # Auto-generated log file
└── downloads/ # Output results
```

---
# ⚙️ Requirements

### **1. Python Version**
Requires **Python 3.8 or higher**.

### **2. Install Dependencies**

#### CLI: Install Required Packages
```bash
pip install pandas requests google-auth google-auth-oauthlib google-auth-httplib2
```
Or create a `requirements.txt` file with:
```
pandas
requests
google-auth
google-auth-oauthlib
google-auth-httplib2
```
Then run:
```bash
pip install -r requirements.txt
```

#### Step: Google API Setup (REQUIRED)
1. **Create Google Cloud Project**
   - Go to: https://console.cloud.google.com/
2. **Enable Google Drive API**
   - Menu → APIs & Services → Library
   - Search: Google Drive API → Enable
3. **Set Up OAuth Consent Screen**
   - Choose External or Internal
   - Add scopes for Google Drive
4. **Create OAuth Client**
   - Menu → APIs & Services → Credentials → Create Credentials → OAuth Client ID
   - Application type: Desktop Application
   - Download the JSON file
   - Rename it: `client_secret_xxxx.json`
   - Place in the same directory as `script.py`

5. **First Run Process**
   - The script will:
     - Open a browser window
     - Ask you to sign in
     - Generate a token file: `token_script.json`

#### Step: CSV Format Requirements
Your CSV should contain:
- 1 column with Google Drive URLs
- 1 column with Issue name / project name

**Example:**
```
IssueID	DriveLinks
PROJ-1	https://drive.google.com/file/d/...
PROJ-2	https://drive.google.com/drive/folders/...
```

**Multiple links in one cell are allowed.**  
**Supported separators:**
- Comma (`,`)
- Semicolon (`;`)
- Newline

**Example:**
```
https://drive.google.com/file/d/ABC,
https://drive.google.com/file/d/XYZ;
https://drive.google.com/drive/folders/123
```

#### Step: How to Run the Script
1. **Prepare Files**
   - Place these files in the same directory:
     - `script.py`
     - `drive_links.csv`
     - `client_secret_xxxx.json`
2. **Run the Script**
   ```bash
   python script.py
   ```
3. **Authenticate**
   - A browser window will open automatically.
4. **Check Downloaded Files**
   - All output is stored here: `downloads/`

#### 📦 Output Structure
**Example output for mixed files:**
```
downloads/
    PROJ-1_ProjectCharter.docx
    PROJ-1_Budget.xlsx
    PROJ-2_Architecture.pptx
    PROJ-3_Diagrams/
    PROJ-3_Diagrams.zip
```
Each folder is zipped automatically after download.

#### 🪵 Logging
All actions are logged to: `download_log1.txt`

**Example log:**
```
2025-11-26 14:11:23 - INFO - Exported Google file → PROJ-1_Document.docx
2025-11-26 14:11:23 - INFO - Skipped (already exists)
2025-11-26 14:11:24 - INFO - Folder downloaded → PROJ-2/
```

#### 🛠 Troubleshooting
- **Browser does not open**
  ```bash
  python script.py --noauth_local_webserver
  ```
- **“invalid_grant”**
  ```bash
  rm token_*.json
  ```
  Run the script again.
- **Shortcut links not downloading**
  Replace Google Drive shortcut URLs with real file URLs.

#### 📄 License
MIT (or you may replace with your preferred license)