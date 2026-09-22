
import schedule, time, csv, os, random
from generator import generate_infographic, verify_village
from publisher import create_caption, publish_image

STATE_FILE = "last_posted.txt"

def get_next_village():
    with open('villages_database.csv', encoding='utf-8') as f:
        villages = list(csv.DictReader(f))
    # track last posted
    last_id = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as sf:
            last_id = sf.read().strip()
    # chronological order: 1947-49 first, then 1967, then ongoing
    # simple: next after last_id
    if not last_id:
        return villages[0], 1
    for idx, v in enumerate(villages):
        if v['id'] == last_id:
            next_idx = (idx+1) % len(villages)
            return villages[next_idx], next_idx+1
    return villages[0], 1

def daily_job():
    village, idx = get_next_village()
    ok, msg = verify_village(village)
    if not ok:
        print(f"Verification failed for {village['id']}: {msg}")
        return
    with open('villages_database.csv', encoding='utf-8') as f:
        total = sum(1 for _ in f) -1
    path = generate_infographic(village, "output")
    caption = create_caption(village, idx, total)
    result = publish_image(path, caption)
    if result.get('dry_run') or result.get('status')!='error':
        with open(STATE_FILE,'w') as sf:
            sf.write(village['id'])
        print(f"Posted {village['id']}")

schedule.every().day.at("19:00").do(daily_job) # 19:00 Amman time

if __name__ == "__main__":
    print("Bot running - will post daily at 19:00 Asia/Amman")
    daily_job() # run once now
    while True:
        schedule.run_pending()
        time.sleep(60)
