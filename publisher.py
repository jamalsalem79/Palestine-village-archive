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
        # returns https://files.catbox.moe/xxxxxx.jpg
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
            # /dl/ is needed but still returns HTML for Instagram, keep as last fallback
            return url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/") if "/dl/" not in url else url
    except Exception as e:
        print(f"tmpfiles failed: {e}")
    return None

def get_public_url(image_path):
    # Try reliable hosts first
    for func in [upload_catbox, upload_0x0, upload_tmpfiles]:
        url = func(image_path)
        if url and url.startswith("http"):
            print(f"Public URL: {url}")
            # quick validation
            try:
                h = requests.head(url, timeout=15)
                print(f"HEAD check {h.status_code} content-type={h.headers.get('Content-Type')}")
            except:
                pass
            return url
    raise Exception("All hosts failed")