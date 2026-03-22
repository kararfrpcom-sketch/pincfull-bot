import requests
import random
import string
import datetime

DB_URL = "https://pincfull-default-rtdb.firebaseio.com"

def generate_code(name, duration_days=30):
    # Random 8 character suffix
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    code = f"PINC-{suffix}"
    
    data = {
        "name": name,
        "duration_days": duration_days,
        "status": "unused",
        "created_at": str(datetime.datetime.now())
    }
    
    # Save to /codes/
    response = requests.put(f"{DB_URL}/codes/{code}.json", json=data)
    if response.status_code == 200:
        print(f"✅ Code Generated Successfully!")
        print(f"👤 User: {name}")
        print(f"🔑 Code: {code}")
        print(f"📅 Validity: {duration_days} Days")
    else:
        print("❌ Error generating code.")

if __name__ == "__main__":
    print("--- PincFull Pro Admin Tool ---")
    user_name = input("Enter Customer Name: ")
    generate_code(user_name)
