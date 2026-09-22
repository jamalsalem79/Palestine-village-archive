"""
daily_bot.py - Picks one village per day and publishes
Fixed to work with publisher.py and new secrets
"""
import csv
import os
from datetime import datetime
from generator import generate_infographic, verify_village
from publisher import publish_image, create_caption

def pick_village_of_the_day():
    csv_path = "villages_database.csv"
    with open(csv_path, encoding='utf-8') as f:
        villages = list(csv.DictReader(f))
    
    verified = []
    for v in villages:
        ok, _ = verify_village(v)
        if ok:
            verified.append(v)
    
    if not verified:
        raise Exception("No verified villages")

    day_of_year = datetime.utcnow().timetuple().tm_yday
    index = day_of_year % len(verified)
    total = len(verified)
    village = verified[index]
    print(f"Day {day_of_year}: {index+1}/{total} - {village['name_en']} ({village['id']})")
    return village, index+1, total

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    village, idx, total = pick_village_of_the_day()
    image_path = generate_infographic(village, "output")
    print(f"Generated {image_path}")
    caption = create_caption(village, idx, total)
    result = publish_image(image_path, caption)
    print(f"Result: {result}")
    if result.get("success"):
        print("✅ Published!")
    elif result.get("dry_run"):
        print("Dry run - add secrets in GitHub to publish for real")
    else:
        print(f"❌ Failed {result}")
        exit(1)


