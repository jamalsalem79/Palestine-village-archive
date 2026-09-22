
"""
Instagram Publisher - uses Instagram Graph API
Requirements: 
- FB App with instagram_basic + instagram_content_publish
- IG Business account connected to FB Page
- Access token

Env vars: IG_USER_ID, ACCESS_TOKEN
"""
import requests, os, time

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
    return caption[:2200] # IG limit

def publish_image(image_path, caption):
    ig_user_id = os.getenv("IG_USER_ID")
    token = os.getenv("ACCESS_TOKEN")
    if not ig_user_id or not token:
        print("Missing IG_USER_ID or ACCESS_TOKEN env vars - running in dry-run mode")
        print(f"Would post: {image_path} with caption length {len(caption)}")
        return {"dry_run": True}

    # Step 1: Upload - for local files you need public URL, so upload to S3 or use container URL
    # For production, host image_path at https://yourdomain.com/...
    # Here we assume you have IMAGE_HOST_URL env
    print("Publishing requires publicly accessible image URL. Implement your image host.")
    return {"status": "needs_hosting"}

if __name__ == "__main__":
    import csv
    with open('villages_database.csv', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        for i, v in enumerate(reader[:3]):
            cap = create_caption(v, i+1, len(reader))
            publish_image(f"output/{v['id']}.jpg", cap)
