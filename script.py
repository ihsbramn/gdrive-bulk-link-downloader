import os
import re
import pandas as pd
import requests
import shutil
from urllib.parse import urlparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import logging

# ------------------------------------------------------------
# LOGGING SETUP
# ------------------------------------------------------------
LOG_FILE = "download.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(msg):
    print(msg)
    logging.info(msg)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

EXPORT_MIME_MAP = {
    "application/vnd.google-apps.document":  ("docx",  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "application/vnd.google-apps.spreadsheet": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "application/vnd.google-apps.presentation": ("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    "application/vnd.google-apps.drawing": ("png", "image/png"),
}

FOLDER_MIME = "application/vnd.google-apps.folder"

# ------------------------------------------------------------
# CHECK IF FILE ALREADY EXISTS
# ------------------------------------------------------------
def already_downloaded(path):
    return os.path.exists(path)

# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
def authenticate_google():
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    token_file = f"token_{script_name}.json"

    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log("🔄 Refreshing Google token…")
            creds.refresh(Request())
        else:
            log("🌐 Opening browser for Google authentication…")

            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret_40751985182-fma5msb7toe8e67h1h9ld5e0ng138f4b.apps.googleusercontent.com.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    log(f"✔ Google authentication successful (token: {token_file})")
    return creds


# ------------------------------------------------------------
# ID EXTRACTION
# ------------------------------------------------------------
def extract_drive_id(url):
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)

    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)

    m = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)

    return None


def sanitize_filename(text):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(text))


# ------------------------------------------------------------
# GOOGLE DRIVE API FUNCTIONS
# ------------------------------------------------------------
def gdrive_list_children(creds, folder_id):
    headers = {"Authorization": f"Bearer {creds.token}"}
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{folder_id}' in parents",
        "fields": "files(id,name,mimeType)",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true"
    }

    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        log(f"❌ Folder listing failed: {r.text}")
        return []

    return r.json().get("files", [])


def download_binary(creds, file_id, local_path):
    if already_downloaded(local_path):
        log(f"⏩ Skipped (already exists): {local_path}")
        return True

    headers = {"Authorization": f"Bearer {creds.token}"}
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"

    with requests.get(url, headers=headers, stream=True) as r:
        if r.status_code != 200:
            log(f"❌ Binary download failed: {r.text}")
            return False

        with open(local_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

    log(f"⬇ Downloaded binary → {local_path}")
    return True


def export_google_file(creds, file_id, local_path, mime_type):
    if already_downloaded(local_path):
        log(f"⏩ Skipped export (already exists): {local_path}")
        return True

    url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
        f"?mimeType={mime_type}&supportsAllDrives=true"
    )
    headers = {"Authorization": f"Bearer {creds.token}"}

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        log(f"❌ Export failed: {r.text}")
        return False

    with open(local_path, "wb") as f:
        f.write(r.content)

    log(f"📄 Exported Google file → {local_path}")
    return True


def download_folder_recursive(creds, folder_id, base_path):
    os.makedirs(base_path, exist_ok=True)
    children = gdrive_list_children(creds, folder_id)

    for item in children:
        file_id = item["id"]
        name = sanitize_filename(item["name"])
        mime = item.get("mimeType")
        full_path = os.path.join(base_path, name)

        if mime == FOLDER_MIME:
            log(f"📁 Entering subfolder: {name}")
            download_folder_recursive(creds, file_id, full_path)
            continue

        if mime in EXPORT_MIME_MAP:
            ext, export_mime = EXPORT_MIME_MAP[mime]
            final_path = full_path + f".{ext}"
            log(f"📄 Exporting Google file: {final_path}")
            export_google_file(creds, file_id, final_path, export_mime)
            continue

        log(f"⬇ Downloading file: {full_path}")
        download_binary(creds, file_id, full_path)


# ------------------------------------------------------------
# PROCESS ANY DRIVE LINK
# ------------------------------------------------------------
def process_drive_link(creds, issue, url):
    file_id = extract_drive_id(url)
    if not file_id:
        log(f"[{issue}] ❌ Invalid link: {url}")
        return

    meta_url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}"
        f"?fields=id,name,mimeType"
        f"&supportsAllDrives=true"
    )
    headers = {"Authorization": f"Bearer {creds.token}"}
    meta_res = requests.get(meta_url, headers=headers)

    if meta_res.status_code != 200:
        log(f"[{issue}] ❌ Metadata fetch failed: {meta_res.text}")
        return

    meta = meta_res.json()
    name = sanitize_filename(meta.get("name", file_id))
    mime = meta.get("mimeType")

    log(f"[{issue}] 🔍 Detected MIME: {mime}")

    # -----------------------------------------
    # FOLDER
    # -----------------------------------------
    if mime == FOLDER_MIME:
        folder_root = os.path.join("downloads", f"{issue}_{name}")
        zip_path = folder_root + ".zip"

        if already_downloaded(zip_path):
            log(f"[{issue}] ⏩ Skipped folder (ZIP already exists): {zip_path}")
            return

        log(f"[{issue}] 📁 Folder detected → recursive download")
        download_folder_recursive(creds, file_id, folder_root)

        shutil.make_archive(folder_root, "zip", folder_root)
        log(f"[{issue}] 🗜 ZIP created: {zip_path}")
        return

    # -----------------------------------------
    # GOOGLE DOC EXPORTS
    # -----------------------------------------
    if mime in EXPORT_MIME_MAP:
        ext, export_mime = EXPORT_MIME_MAP[mime]
        filename = sanitize_filename(f"{issue}_{name}.{ext}")
        save_path = os.path.join("downloads", filename)

        if already_downloaded(save_path):
            log(f"[{issue}] ⏩ Skipped (already exists): {save_path}")
            return

        log(f"[{issue}] 📄 Exporting Google Doc → {filename}")
        export_google_file(creds, file_id, save_path, export_mime)
        log(f"[{issue}] ✔ Saved: {save_path}")
        return

    # -----------------------------------------
    # BINARY FILES
    # -----------------------------------------
    filename = sanitize_filename(f"{issue}_{name}")
    save_path = os.path.join("downloads", filename)

    if already_downloaded(save_path):
        log(f"[{issue}] ⏩ Skipped (already exists): {save_path}")
        return

    log(f"[{issue}] ⬇ Binary file detected → {filename}")
    download_binary(creds, file_id, save_path)
    log(f"[{issue}] ✔ Saved: {save_path}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    df = pd.read_csv("drive_links.csv")
    df.columns = df.columns.str.replace("\ufeff", "").str.strip()

    link_cols = []
    for c in df.columns:
        if df[c].astype(str).str.contains("drive.google.com", case=False).any():
            link_cols.append(c)

    if not link_cols:
        raise Exception("❌ No Google Drive link column found in CSV.")

    name_candidates = [c for c in df.columns if c not in link_cols]

    if not name_candidates:
        log("⚠️ All columns contain Google Drive links → using the first as name.")
        issue_col = df.columns[0]
    else:
        issue_col = name_candidates[0]

    link_col = link_cols[0]

    log(f"✔ Using '{issue_col}' as issue/name column")
    log(f"✔ Using '{link_col}' as link column")

    creds = authenticate_google()
    os.makedirs("downloads", exist_ok=True)

    for _, row in df.iterrows():
        issue = sanitize_filename(str(row[issue_col]))
        links = str(row[link_col]).strip()

        if not links or links.lower() == "nan":
            continue

        for url in re.split(r"[,\n;]+", links):
            url = url.strip()
            if url.startswith("http"):
                process_drive_link(creds, issue, url)


if __name__ == "__main__":
    log("🚀 Script started")
    main()
    log("✅ ALL DONE!")