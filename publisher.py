"""
Instagram Publisher - FIXED v2
Fixes catbox/0x0.st ban by using tmpfiles.org + file.io + uguu.se
Works with App ID 1619660253287942, IG ID 17841400654154244
Env: IG_USER_ID, ACCESS_TOKEN
"""
import os
import time
import requests

API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"

def upload_tmpfiles(image_path):
    print(f"Trying tmpfiles.org for {image_path}...")
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=40
            )
        print(f"tmpfiles status {r.status_code}: {r.text[:500]}")
        j = r.json()
        if j.get("status") == "success":
            url = j["data"]["url"]  # https://tmpfiles.org/dl/abc
            # Ensure direct link
            if "/dl/" in url:
                direct = url
            else:
                direct = url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
            print(f"tmpfiles URL: {direct}")
            return direct
    except Exception as e:
        print(f"tmpfiles failed: {e}")
    return None

def upload_fileio(image_path):
    print(f"Trying file.io for {image_path}...")
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://file.io",
                files={"file": f},
                timeout=40
            )
        print(f"file.io status {r.status_code}: {r.text[:500]}")
        j = r.json()
        if j.get("success"):
            url = j.get("link")
            print(f"file.io URL: {url}")
            return url
    except Exception as e:
        print(f"file.io failed: {e}")
    return None

def upload_uguu(image_path):
    print(f"Trying uguu.se for {image_path}...")
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://uguu.se/upload.php",
                files={"files[]": f},
                timeout=40
            )
        print(f"uguu status {r.status_code}: {r.text[:500]}")
        j = r.json()
        if j.get("files"):
            url = j["files"][0].get("url")
            print(f"uguu URL: {url}")
            return url
    except Exception as e:
        print(f"uguu failed: {e}")
    return None

def upload_catbox(image_path):
    # Keep as last fallback - may work sometimes
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=30
            )
        if r.status_code == 200 and "http" in r.text:
            url = r.text.strip()
            print(f"catbox URL: {url}")
            return url
        print(f"catbox failed: {r.text[:200]}")
    except Exception as e:
        print(f"catbox exception: {e}")
    return None

def get_public_url(image_path):
    for func in [upload_tmpfiles, upload_fileio, upload_uguu, upload_catbox]:
        url = func(image_path)
        if url and url.startswith("http"):
            return url
    raise Exception("All image hosts failed - try again later")

def create_caption(village, index, total):
    caption = f"""{village['name_en']} - {village['name_ar']} | {village['district']} District

Population in 1948: {village['population_1948']}
Land area: {village['land_dunums']} dunums
Depopulated: {village['date_depopulated']}
Cause: {village['cause']}

Today on its lands: {village['current_localities']}

This is village {index} of {total}+ documented from the British Mandate (1917) to present. Every figure verified against credible sources.

Sources: {village['sources']}

This archive preserves the memory of destroyed villages so they are not erased.

#Palestine #Nakba #Nakba1948 #RightOfReturn #PalestinianHistory #FreePalestine #PalestineArchive #FromTheRiverToTheSea #Village_{village['id']} #BritishMandate #OngoingNakba #Gaza #WestBank #History #NeverForget
"""
    return caption[:2200]

def publish_image(image_path_or_url, caption):
    ig_user_id = os.getenv("IG_USER_ID") or os.getenv("INSTAGRAM_USER_ID")
    token = os.getenv("ACCESS_TOKEN") or os.getenv("INSTAGRAM_ACCESS_TOKEN")

    if not ig_user_id or not token:
        print("Missing env - dry run")
        return {"dry_run": True}

    if os.path.exists(str(image_path_or_url)):
        image_url = get_public_url(image_path_or_url)
    else:
        image_url = str(image_path_or_url)

    print(f"Publishing with image_url={image_url}")

    # Step 1: Create container
    create_url = f"{GRAPH_BASE}/{ig_user_id}/media"
    r = requests.post(create_url, data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=60)
    print(f"Create container: {r.status_code} {r.text}")
    data = r.json()
    if "error" in data:
        return {"error": data["error"]}

    creation_id = data.get("id")
    if not creation_id:
        return {"error": "No creation_id", "raw": data}

    print(f"Container {creation_id}, waiting 12s...")
    time.sleep(12)

    # Status check
    status_url = f"{GRAPH_BASE}/{creation_id}"
    for i in range(8):
        sr = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=30)
        sj = sr.json()
        print(f"Status check {i}: {sj}")
        if sj.get("status_code") == "FINISHED":
            break
        if sj.get("status_code") in ["ERROR", "EXPIRED"]:
            return {"error": f"Container failed {sj}"}
        time.sleep(4)

    # Publish
    pub_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
    r2 = requests.post(pub_url, data={"creation_id": creation_id, "access_token": token}, timeout=60)
    print(f"Publish: {r2.status_code} {r2.text}")
    res = r2.json()
    if "id" in res:
        print(f"SUCCESS {res['id']}")
        return {"success": True, "media_id": res["id"]}
    return {"error": res}