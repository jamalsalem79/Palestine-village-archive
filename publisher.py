"""
Instagram + Facebook Page Publisher - v7 AUTO IG ID
Posts to both IG and Facebook Page 61594819077642 - Palestine Archive
Auto-fetches IG ID from Page, no manual Graph Explorer needed
"""
import os
import time
import requests
import shutil
import subprocess

API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"

def upload_imgur(image_path):
    try:
        with open(image_path, 'rb') as f:
            r = requests.post(
                "https://api.imgur.com/3/image",
                headers={"Authorization": "Client-ID 546c25a59c58ad7", "User-Agent": "Mozilla/5.0"},
                files={"image": f},
                timeout=60
            )
        print(f"imgur status {r.status_code} {r.text[:500]}")
        j = r.json()
        if j.get("success") and j.get("data", {}).get("link"):
            return j["data"]["link"]
    except Exception as e:
        print(f"imgur failed: {e}")
    return None

def upload_transfer(image_path):
    try:
        filename = os.path.basename(image_path)
        with open(image_path, 'rb') as f:
            r = requests.put(
                f"https://transfer.sh/{filename}",
                data=f,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=60
            )
        url = r.text.strip()
        print(f"transfer.sh response: {url}")
        if url.startswith("https://") and "transfer.sh" in url:
            return url
    except Exception as e:
        print(f"transfer.sh failed: {e}")
    return None

def upload_github_raw(image_path):
    try:
        filename = os.path.basename(image_path)
        dest_dir = "output"
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, filename)
        if os.path.abspath(image_path) != os.path.abspath(dest):
            shutil.copy(image_path, dest)
            print(f"Copied {image_path} -> {dest}")
        subprocess.run(["git", "config", "--global", "user.email", "bot@palestine.archive"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Archive Bot"], check=True)
        subprocess.run(["git", "add", dest], check=True)
        subprocess.run(["git", "commit", "-m", f"publish image {filename} {int(time.time())} [skip ci]"], check=False)
        subprocess.run(["git", "push"], check=True)
        print("Pushed image to GitHub")
        repo = os.getenv("GITHUB_REPOSITORY", "jamalsalem79/Palestine-village-archive")
        url = f"https://raw.githubusercontent.com/{repo}/main/{dest}?t={int(time.time())}"
        print(f"GitHub raw URL: {url}")
        time.sleep(3)
        return url
    except Exception as e:
        print(f"github raw failed: {e}")
    return None

def get_public_url(image_path):
    for func in [upload_imgur, upload_transfer, upload_github_raw]:
        print(f"Trying {func.__name__}...")
        url = func(image_path)
        if url and url.startswith("http"):
            print(f"Public URL: {url}")
            try:
                h = requests.head(url, timeout=15, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
                print(f"HEAD check {h.status_code} content-type={h.headers.get('Content-Type')}")
                if h.status_code == 200:
                    return url
            except Exception as ex:
                print(f"HEAD check failed: {ex} - still trying URL anyway")
                return url
    raise Exception("All hosts failed - check GitHub Token permissions")

def get_ig_id_from_page(fb_page_id, token):
    """Auto-fetch IG Business ID from Page - tries multiple methods"""
    print(f"🔍 Trying to auto-detect IG ID from Page {fb_page_id}...")
    
    # Method 1: Direct page query
    try:
        url = f"{GRAPH_BASE}/{fb_page_id}"
        params = {"fields": "instagram_business_account", "access_token": token}
        r = requests.get(url, params=params, timeout=30)
        print(f"Method 1 - Page IG query: {r.status_code} {r.text[:800]}")
        data = r.json()
        if "instagram_business_account" in data and "id" in data["instagram_business_account"]:
            ig_id = data["instagram_business_account"]["id"]
            print(f"✅ Found IG ID via Page: {ig_id}")
            return ig_id
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2: me/accounts
    try:
        url = f"{GRAPH_BASE}/me/accounts"
        params = {"fields": "id,name,instagram_business_account", "access_token": token}
        r = requests.get(url, params=params, timeout=30)
        print(f"Method 2 - me/accounts: {r.status_code} {r.text[:1500]}")
        data = r.json()
        for page in data.get("data", []):
            if str(page.get("id")) == str(fb_page_id) and page.get("instagram_business_account"):
                ig_id = page["instagram_business_account"]["id"]
                print(f"✅ Found IG ID via me/accounts: {ig_id}")
                return ig_id
            # If only one page, take it
            if page.get("instagram_business_account") and len(data.get("data", [])) == 1:
                ig_id = page["instagram_business_account"]["id"]
                print(f"✅ Found IG ID (single page): {ig_id}")
                return ig_id
        # Try any page that has IG
        for page in data.get("data", []):
            if page.get("instagram_business_account"):
                ig_id = page["instagram_business_account"]["id"]
                print(f"✅ Found IG ID via any page {page['id']}: {ig_id}")
                return ig_id
    except Exception as e:
        print(f"Method 2 failed: {e}")
    
    print("❌ Could not auto-detect IG ID")
    return None

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

def publish_to_facebook_page(image_url, caption, fb_page_id, fb_token):
    if not fb_page_id or not fb_token:
        print("FB Page ID or Token missing - skipping FB Page post")
        return {"skipped": True}
    try:
        print(f"Publishing to Facebook Page {fb_page_id}...")
        url = f"{GRAPH_BASE}/{fb_page_id}/photos"
        data = {"url": image_url, "message": caption, "access_token": fb_token}
        r = requests.post(url, data=data, timeout=60)
        print(f"FB Page Publish: {r.status_code} {r.text[:1000]}")
        res = r.json()
        if "id" in res:
            print(f"✅ FB Page posted: {res['id']}")
            return {"success": True, "post_id": res["id"]}
        else:
            print(f"❌ FB Page failed: {res}")
            return {"error": res}
    except Exception as e:
        print(f"FB Page exception: {e}")
        return {"error": str(e)}

def publish_image(image_path_or_url, caption):
    ig_user_id = (os.getenv("IG_USER_ID") or os.getenv("INSTAGRAM_USER_ID") or "").strip().strip('"').strip("'")
    token = (os.getenv("ACCESS_TOKEN") or os.getenv("INSTAGRAM_ACCESS_TOKEN") or "").strip().strip('"').strip("'")
    fb_page_id = (os.getenv("FB_PAGE_ID") or "61594819077642").strip()
    fb_page_token = (os.getenv("FB_PAGE_TOKEN") or os.getenv("FACEBOOK_PAGE_TOKEN") or token).strip().strip('"').strip("'")
    
    print(f"DEBUG: IG_USER_ID length={len(ig_user_id)} value={ig_user_id[:20]}...")
    print(f"DEBUG: ACCESS_TOKEN length={len(token)} starts_with={token[:10]}...")
    print(f"DEBUG: FB_PAGE_ID={fb_page_id}")
    
    if not token:
        return {"dry_run": True}
    if len(token) < 50:
        print(f"ERROR: Token too short ({len(token)} chars), likely truncated!")
        return {"error": f"Token too short: {len(token)} chars"}

    # AUTO-FETCH IG ID if not provided
    if not ig_user_id or len(ig_user_id) < 10 or ig_user_id == "61594819077642":
        print(f"⚠️ IG_USER_ID missing or equals Page ID, trying auto-detect...")
        auto_ig_id = get_ig_id_from_page(fb_page_id, token)
        if auto_ig_id:
            ig_user_id = auto_ig_id
            print(f"✅ Using auto-detected IG ID: {ig_user_id}")
        else:
            # If auto fails but Page ID is provided, we can still try to publish to FB only
            print("⚠️ Could not get IG ID, will try FB Page only if IG fails")
    
    if os.path.exists(str(image_path_or_url)):
        image_url = get_public_url(image_path_or_url)
    else:
        image_url = str(image_path_or_url)
    
    print(f"Publishing with image_url={image_url}")
    
    result = {}
    
    # 1. Publish to Instagram (if we have IG ID)
    if ig_user_id and len(ig_user_id) > 10 and ig_user_id != fb_page_id:
        create_url = f"{GRAPH_BASE}/{ig_user_id}/media"
        r = requests.post(create_url, data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=60)
        print(f"Create IG container: {r.status_code} {r.text}")
        data = r.json()
        if "error" in data:
            result["instagram"] = {"error": data["error"], "step": "instagram_create"}
        else:
            creation_id = data.get("id")
            if not creation_id:
                result["instagram"] = {"error": "No creation_id", "raw": data}
            else:
                time.sleep(12)
                status_url = f"{GRAPH_BASE}/{creation_id}"
                for i in range(8):
                    sr = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=30)
                    print(f"Status {i}: {sr.text[:500]}")
                    sj = sr.json()
                    if sj.get("status_code") == "FINISHED":
                        break
                    if sj.get("status_code") in ["ERROR", "EXPIRED"]:
                        result["instagram"] = {"error": f"Container failed {sj}", "step": "instagram_status"}
                        break
                    time.sleep(4)
                else:
                    # only if not break with error
                    if "instagram" not in result:
                        pub_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
                        r2 = requests.post(pub_url, data={"creation_id": creation_id, "access_token": token}, timeout=60)
                        print(f"Publish IG: {r2.status_code} {r2.text}")
                        res = r2.json()
                        if "id" in res:
                            result["instagram"] = {"success": True, "media_id": res["id"]}
                            print(f"✅ Instagram success: {res['id']}")
                        else:
                            result["instagram"] = {"error": res}
    
    # 2. Publish to Facebook Page
    fb_result = publish_to_facebook_page(image_url, caption, fb_page_id, fb_page_token)
    result["facebook"] = fb_result
    
    if result.get("instagram", {}).get("success") or result.get("facebook", {}).get("success"):
        result["success"] = True
        return result
    else:
        return {"error": result}
