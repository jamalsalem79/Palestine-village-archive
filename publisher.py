"""
Instagram Publisher - FIXED v4
Fixes token parse error + fixes Unknown Image Format by using Catbox direct URLs
"""
import os
import time
import requests

API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"

def upload_catbox(image_path):
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=60
            )
        url = r.text.strip()
        print(f"catbox response: {url}")
        if url.startswith("https://") and "catbox.moe" in url:
            return url
    except Exception as e:
        print(f"catbox failed: {e}")
    return None

def upload_0x0(image_path):
    try:
        with open(image_path, 'rb') as f:
            r = requests.post("https://0x0.st", files={"file": f}, timeout=60)
        url = r.text.strip()
        print(f"0x0 response: {url}")
        if url.startswith("https://"):
            return url
    except Exception as e:
        print(f"0x0 failed: {e}")
    return None

def upload_tmpfiles(image_path):
    try:
        with open(image_path, 'rb') as f:
            r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=40)
        j = r.json()
        if j.get("status") == "success":
            url = j["data"]["url"]
            return url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/") if "/dl/" not in url else url
    except Exception as e:
        print(f"tmpfiles failed: {e}")
    return None

def get_public_url(image_path):
    # Try reliable hosts first - Catbox gives direct image/jpeg which IG accepts
    for func in [upload_catbox, upload_0x0, upload_tmpfiles]:
        url = func(image_path)
        if url and url.startswith("http"):
            print(f"Public URL: {url}")
            try:
                h = requests.head(url, timeout=15)
                print(f"HEAD check {h.status_code} content-type={h.headers.get('Content-Type')}")
            except Exception as ex:
                print(f"HEAD check failed: {ex}")
            return url
    raise Exception("All hosts failed")

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
    # CRITICAL: strip whitespace/newlines that cause code 190 Cannot parse
    ig_user_id = (os.getenv("IG_USER_ID") or os.getenv("INSTAGRAM_USER_ID") or "").strip().strip('"').strip("'")
    token = (os.getenv("ACCESS_TOKEN") or os.getenv("INSTAGRAM_ACCESS_TOKEN") or "").strip().strip('"').strip("'")
    
    print(f"DEBUG: IG_USER_ID length={len(ig_user_id)} value={ig_user_id[:10]}...")
    print(f"DEBUG: ACCESS_TOKEN length={len(token)} starts_with={token[:10]}...")
    
    if not ig_user_id or not token:
        return {"dry_run": True}
    if len(token) < 50:
        print(f"ERROR: Token too short ({len(token)} chars), likely truncated in Secrets!")
        return {"error": f"Token too short: {len(token)} chars"}

    if os.path.exists(str(image_path_or_url)):
        image_url = get_public_url(image_path_or_url)
    else:
        image_url = str(image_path_or_url)

    print(f"Publishing with image_url={image_url}")
    create_url = f"{GRAPH_BASE}/{ig_user_id}/media"
    r = requests.post(create_url, data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=60)
    print(f"Create container: {r.status_code} {r.text}")
    data = r.json()
    if "error" in data:
        return {"error": data["error"]}
    creation_id = data.get("id")
    if not creation_id:
        return {"error": "No creation_id", "raw": data}
    time.sleep(12)
    status_url = f"{GRAPH_BASE}/{creation_id}"
    for i in range(8):
        sr = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=30)
        print(f"Status {i}: {sr.text[:500]}")
        sj = sr.json()
        if sj.get("status_code") == "FINISHED":
            break
        if sj.get("status_code") in ["ERROR", "EXPIRED"]:
            return {"error": f"Container failed {sj}"}
        time.sleep(4)
    pub_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
    r2 = requests.post(pub_url, data={"creation_id": creation_id, "access_token": token}, timeout=60)
    print(f"Publish: {r2.status_code} {r2.text}")
    res = r2.json()
    if "id" in res:
        return {"success": True, "media_id": res["id"]}
    return {"error": res}
