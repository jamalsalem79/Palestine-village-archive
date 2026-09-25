"""
Instagram + Facebook Page Publisher - v8 FINAL FIX
Auto-gets Page Token from User Token + Auto-fetches IG ID
Fixes #200 This app is not allowed + Object does not exist
"""
import os
import time
import requests

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
        j = r.json()
        if j.get("success") and j.get("data", {}).get("link"):
            return j["data"]["link"]
    except Exception as e:
        print(f"imgur failed: {e}")
    return None

def get_page_token_and_ig_id(fb_page_id, user_token):
    print(f"🔍 Getting Page token for Page {fb_page_id} from User token...")
    try:
        url = f"{GRAPH_BASE}/me/accounts"
        params = {"fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": user_token}
        r = requests.get(url, params=params, timeout=30)
        print(f"me/accounts: {r.status_code} {r.text[:2000]}")
        data = r.json()
        pages = data.get("data", [])
        if not pages:
            print("❌ me/accounts empty - System User has no Pages assigned!")
            return None, None
        for page in pages:
            if str(page.get("id")) == str(fb_page_id):
                page_token = page.get("access_token")
                ig_account = page.get("instagram_business_account")
                ig_id = ig_account.get("id") if ig_account else None
                print(f"✅ Found Page {fb_page_id} token length={len(page_token) if page_token else 0}")
                if ig_id:
                    print(f"✅ Found IG ID: {ig_id}")
                return page_token, ig_id
        for page in pages:
            if page.get("instagram_business_account"):
                return page.get("access_token"), page["instagram_business_account"]["id"]
        if pages:
            return pages[0].get("access_token"), None
    except Exception as e:
        print(f"get_page_token failed: {e}")
    return None, None

def get_public_url(image_path):
    url = upload_imgur(image_path)
    if url:
        return url
    raise Exception("Imgur upload failed")

def create_caption(village, index, total):
    return f"""{village['name_en']} - {village['name_ar']} | {village['district']}

Population: {village['population_1948']} Land: {village['land_dunums']}
Depopulated: {village['date_depopulated']} Cause: {village['cause']}
Today: {village['current_localities']}
Sources: {village['sources']}
#Palestine #Nakba #Village_{village['id']}"""[:2200]

def publish_to_facebook_page(image_url, caption, fb_page_id, page_token):
    if not fb_page_id or not page_token:
        return {"skipped": True}
    try:
        print(f"Publishing to FB Page {fb_page_id} with Page Token len={len(page_token)}...")
        url = f"{GRAPH_BASE}/{fb_page_id}/photos"
        data = {"url": image_url, "message": caption, "access_token": page_token}
        r = requests.post(url, data=data, timeout=60)
        print(f"FB Publish: {r.status_code} {r.text[:1000]}")
        res = r.json()
        if "id" in res:
            print(f"✅ FB posted: {res['id']}")
            return {"success": True, "post_id": res["id"]}
        return {"error": res}
    except Exception as e:
        return {"error": str(e)}

def publish_image(image_path_or_url, caption):
    ig_user_id = (os.getenv("IG_USER_ID") or "").strip()
    user_token = (os.getenv("ACCESS_TOKEN") or "").strip()
    fb_page_id = (os.getenv("FB_PAGE_ID") or "61594819077642").strip()
    fb_page_token_input = (os.getenv("FB_PAGE_TOKEN") or "").strip()

    print(f"DEBUG: IG_USER_ID len={len(ig_user_id)}")
    print(f"DEBUG: ACCESS_TOKEN len={len(user_token)} starts={user_token[:15]}...")
    print(f"DEBUG: FB_PAGE_ID={fb_page_id} FB_PAGE_TOKEN len={len(fb_page_token_input)}")

    if not user_token:
        return {"dry_run": True}

    page_token, resolved_ig_id = get_page_token_and_ig_id(fb_page_id, fb_page_token_input or user_token)
    if not page_token and fb_page_token_input != user_token:
        page_token, resolved_ig_id = get_page_token_and_ig_id(fb_page_id, user_token)

    if not page_token:
        page_token = fb_page_token_input or user_token
        print("⚠️ Using provided token as Page Token fallback")

    if resolved_ig_id and not ig_user_id:
        ig_user_id = resolved_ig_id

    if not ig_user_id and page_token:
        try:
            url = f"{GRAPH_BASE}/{fb_page_id}"
            params = {"fields": "instagram_business_account", "access_token": page_token}
            r = requests.get(url, params=params, timeout=30)
            print(f"Page IG query: {r.status_code} {r.text[:800]}")
            data = r.json()
            if "instagram_business_account" in data:
                ig_user_id = data["instagram_business_account"]["id"]
        except Exception as e:
            print(f"Page query failed: {e}")

    if os.path.exists(str(image_path_or_url)):
        image_url = get_public_url(image_path_or_url)
    else:
        image_url = str(image_path_or_url)

    print(f"Publishing with {image_url}")
    result = {}

    if ig_user_id and len(ig_user_id) > 10:
        create_url = f"{GRAPH_BASE}/{ig_user_id}/media"
        r = requests.post(create_url, data={"image_url": image_url, "caption": caption, "access_token": user_token}, timeout=60)
        print(f"Create IG: {r.status_code} {r.text}")
        data = r.json()
        if "id" in data:
            creation_id = data["id"]
            time.sleep(12)
            for i in range(8):
                sr = requests.get(f"{GRAPH_BASE}/{creation_id}", params={"fields": "status_code", "access_token": user_token}, timeout=30)
                sj = sr.json()
                if sj.get("status_code") == "FINISHED":
                    break
                if sj.get("status_code") in ["ERROR", "EXPIRED"]:
                    result["instagram"] = {"error": sj}
                    break
                time.sleep(4)
            if "instagram" not in result:
                r2 = requests.post(f"{GRAPH_BASE}/{ig_user_id}/media_publish", data={"creation_id": creation_id, "access_token": user_token}, timeout=60)
                print(f"Publish IG: {r2.status_code} {r2.text}")
                res = r2.json()
                if "id" in res:
                    result["instagram"] = {"success": True, "media_id": res["id"]}
                else:
                    result["instagram"] = {"error": res}
        else:
            result["instagram"] = {"error": data}

    fb_result = publish_to_facebook_page(image_url, caption, fb_page_id, page_token)
    result["facebook"] = fb_result

    if result.get("instagram", {}).get("success") or result.get("facebook", {}).get("success"):
        result["success"] = True
        return result
    return {"error": result}
