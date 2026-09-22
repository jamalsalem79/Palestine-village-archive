"""
Instagram Publisher - FIXED for new App ID 1619660253287942 + IG ID 17841400654154244
Env vars: IG_USER_ID, ACCESS_TOKEN (mapped from secrets INSTAGRAM_USER_ID / INSTAGRAM_ACCESS_TOKEN)
"""
import os
import time
import requests

API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"

def upload_to_catbox(image_path):
    """Upload local JPG to catbox.moe to get public URL for Instagram API"""
    print(f"Uploading {image_path} to catbox.moe...")
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=40
            )
        if r.status_code == 200 and r.text.strip().startswith("http"):
            url = r.text.strip()
            print(f"Public URL: {url}")
            return url
        print(f"Catbox failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"Catbox exception: {e}")

    # Fallback 0x0.st
    print("Trying fallback 0x0.st...")
    with open(image_path, 'rb') as f:
        r = requests.post("https://0x0.st", files={"file": f}, timeout=40)
    if r.status_code == 200:
        url = r.text.strip()
        print(f"Fallback URL: {url}")
        return url
    raise Exception(f"Both hosts failed: {r.text}")

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
    token = os.getenv("ACCESS_TOKEN") or os.getenv("INSTAGRAM_ACCESS_TOKEN") or os.getenv("INSTAGRAM_TOKEN")

    if not ig_user_id or not token:
        print("Missing IG_USER_ID or ACCESS_TOKEN env vars - dry-run mode")
        print(f"Would post: {image_path_or_url} caption len {len(caption)}")
        return {"dry_run": True, "error": "missing_env"}

    # Local file? Upload first
    if os.path.exists(str(image_path_or_url)):
        image_url = upload_to_catbox(image_path_or_url)
    else:
        image_url = str(image_path_or_url)

    # Step 1: Create container
    print(f"Step 1: Creating media container for IG user {ig_user_id}")
    create_url = f"{GRAPH_BASE}/{ig_user_id}/media"
    payload = {"image_url": image_url, "caption": caption, "access_token": token}
    r = requests.post(create_url, data=payload, timeout=60)
    print(f"Create: {r.status_code} {r.text}")
    data = r.json()
    if "error" in data:
        print(f"ERROR: {data['error']}")
        return {"error": data['error']}

    creation_id = data.get("id")
    if not creation_id:
        return {"error": "No creation_id", "raw": data}

    print(f"Container {creation_id} created, waiting...")
    time.sleep(10)

    # Status check loop
    status_url = f"{GRAPH_BASE}/{creation_id}"
    for i in range(6):
        sr = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=30)
        sj = sr.json()
        print(f"Status {i}: {sj}")
        if sj.get("status_code") == "FINISHED":
            break
        if sj.get("status_code") in ["ERROR", "EXPIRED"]:
            return {"error": f"Container failed {sj}"}
        time.sleep(5)

    # Step 2: Publish
    publish_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
    r2 = requests.post(publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=60)
    print(f"Publish: {r2.status_code} {r2.text}")
    result = r2.json()
    if "id" in result:
        print(f"SUCCESS Published {result['id']}")
        return {"success": True, "media_id": result["id"]}
    return {"error": result}

