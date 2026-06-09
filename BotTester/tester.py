import csv
import sqlite3
import asyncio
import os
from telethon import TelegramClient, events
from dotenv import load_dotenv
load_dotenv()

# Configuration - Requires Telegram User API credentials (not bot token)
# Get from https://my.telegram.org
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = 'tester_session'

DB_PATH = 'test_results.db'

def setup_db(db_path=DB_PATH):
    """Initialize SQLite DB for storing test results."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            bot_username TEXT,
            test_case_name TEXT,
            status TEXT,
            expected_output TEXT,
            actual_output TEXT,
            blob_data BLOB,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def insert_result(conn, roll_no, bot_username, test_name, status, expected, actual, blob=None):
    """Insert a test record into the DB."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO test_results (roll_no, bot_username, test_case_name, status, expected_output, actual_output, blob_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (roll_no, bot_username, test_name, status, expected, actual, blob))
    conn.commit()

async def run_tests(client, conn, roll_no, bot_username):
    """Run all test cases for a specific bot."""
    print(f"\n--- Testing {bot_username} (Roll No: {roll_no}) ---")
    
    # Helper to send message and wait for reply
    async def send_and_wait(message, file=None, timeout=15):
        try:
            async with client.conversation(bot_username, timeout=timeout) as conv:
                if file:
                    await conv.send_file(file, caption=message)
                else:
                    await conv.send_message(message)
                response = await conv.get_response()
                return response
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return str(e)

    # ---------------------------------------------------------
    # Test 1: Simple Text Q&A
    # ---------------------------------------------------------
    print("  [1/4] Running Test 1: Simple Q&A...")
    res1 = await send_and_wait("/start")
    if res1 and not isinstance(res1, str):
        insert_result(conn, roll_no, bot_username, "Test 1: Simple Q&A", "PASS", "Any greeting text", res1.text)
    else:
        insert_result(conn, roll_no, bot_username, "Test 1: Simple Q&A", "FAIL", "Any greeting text", str(res1) if res1 else "Timeout")

    # ---------------------------------------------------------
    # Test 2: Image Data Extraction
    # ---------------------------------------------------------
    print("  [2/4] Running Test 2: Image Extraction...")
    img_path = 'test_data/sample_image.png'
    if os.path.exists(img_path):
        res2 = await send_and_wait("Extract text from this image", file=img_path)
        if res2 and not isinstance(res2, str):
            res2_text = res2.text or ""
            # Expecting the bot to extract 'TEST1234' from the image
            status = "PASS" if "TEST1234" in res2_text.upper() else "FAIL"
            insert_result(conn, roll_no, bot_username, "Test 2: Image Extraction", status, "Contains 'TEST1234'", res2_text)
        else:
            insert_result(conn, roll_no, bot_username, "Test 2: Image Extraction", "FAIL", "Contains 'TEST1234'", str(res2) if res2 else "Timeout")
    else:
        print("        -> Skipping: sample_image.png not found.")

    # ---------------------------------------------------------
    # Test 3: Context Management
    # ---------------------------------------------------------
    print("  [3/4] Running Test 3: Context Management...")
    # Setup context
    await send_and_wait("My favorite color is emerald.")
    await asyncio.sleep(1) # brief pause
    # Test context recall
    res3 = await send_and_wait("What is my favorite color?")
    if res3 and not isinstance(res3, str):
        res3_text = res3.text or ""
        status = "PASS" if "emerald" in res3_text.lower() else "FAIL"
        insert_result(conn, roll_no, bot_username, "Test 3: Context Management", status, "Contains 'emerald'", res3_text)
    else:
        insert_result(conn, roll_no, bot_username, "Test 3: Context Management", "FAIL", "Contains 'emerald'", str(res3) if res3 else "Timeout")

    # ---------------------------------------------------------
    # Test 4: Bot Data Sending
    # ---------------------------------------------------------
    print("  [4/4] Running Test 4: Bot Data Send...")
    res4 = await send_and_wait("Send me a data file or image.")
    if res4 and not isinstance(res4, str):
        if res4.media:
            # Download the media to memory and store as BLOB
            blob = await client.download_media(res4.media, bytes)
            media_type = type(res4.media).__name__
            insert_result(conn, roll_no, bot_username, "Test 4: Bot Data Send", "PASS", "Receives Media", f"Received {media_type}", blob)
        else:
            insert_result(conn, roll_no, bot_username, "Test 4: Bot Data Send", "FAIL", "Receives Media", f"No media received: {res4.text}")
    else:
        insert_result(conn, roll_no, bot_username, "Test 4: Bot Data Send", "FAIL", "Receives Media", str(res4) if res4 else "Timeout")


async def main():
    print("Starting Automated Bot Evaluation...")
    if not API_ID or not API_HASH:
        print("\n[ERROR] TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables must be set.")
        print("  1. Go to https://my.telegram.org to get your User API credentials.")
        print("  2. Run: export TELEGRAM_API_ID='your_id' && export TELEGRAM_API_HASH='your_hash'")
        return

    conn = setup_db()
    
    # Initialize the User Client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    def get_phone():
        print("\n--- INSTRUCTOR LOGIN ---")
        print("To test the bots, the script needs to log into YOUR Telegram account.")
        print("The students will NEVER see this, and they will NOT receive an OTP.")
        phone = input("Please enter YOUR PHONE NUMBER with country code (e.g. +1234567890).\nDO NOT enter a bot token: ")
        if ':' in phone:
            print("\n[ERROR] You entered a Bot Token!")
            print("Telegram prevents Bots from talking to other Bots.")
            print("This evaluation script MUST be logged into your personal Telegram User account.")
            exit(1)
        return phone

    await client.start(phone=get_phone)
    print("User Client Started.")

    csv_file = 'students.csv'
    if not os.path.exists(csv_file):
        print(f"[ERROR] {csv_file} not found!")
        return

    with open(csv_file, 'r', encoding='utf-8') as f:
        # Assuming header: roll_no,bot_username,bot_token
        reader = csv.DictReader(f)
        for row in reader:
            roll_no = row.get('roll_no', '').strip()
            bot_username = row.get('bot_username', '').strip()
            
            if bot_username:
                if not bot_username.startswith('@'):
                    bot_username = '@' + bot_username
                
                await run_tests(client, conn, roll_no, bot_username)
            else:
                print(f"Skipping invalid row: {row}")

    await client.disconnect()
    conn.close()
    print("\n✅ Testing complete! Results safely stored in test_results.db.")

if __name__ == '__main__':
    asyncio.run(main())
