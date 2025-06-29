import json
import time
import signal
import requests
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

# Load accounts
ACCOUNTS_FILE = Path("accounts.json")
if not ACCOUNTS_FILE.exists():
    logger.error("❌ File accounts.json tidak ditemukan!")
    exit(1)

with open(ACCOUNTS_FILE) as f:
    ACCOUNTS = json.load(f)

# Global flag for graceful shutdown
stop_flag = False

def signal_handler(sig, frame):
    global stop_flag
    stop_flag = True
    logger.warning("⛔ Dihentikan manual oleh user.")

signal.signal(signal.SIGINT, signal_handler)

# Get username from token (for logging only)
def get_username(access_token):
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        res = requests.post("https://www.keycloudapi.com/User/_User_Search", headers=headers, data={})
        if res.status_code != 200 or not res.text.strip().startswith("{"):
            logger.warning("⚠️ Gagal ambil username, status {}: {}", res.status_code, res.text)
            return "Unknown"
        data = res.json()
        msg = data.get("Msg")
        if isinstance(msg, dict):
            return msg.get("NickName", "Unknown")
        elif isinstance(msg, str):
            try:
                msg_obj = json.loads(msg)
                return msg_obj.get("NickName", "Unknown")
            except:
                return "Unknown"
        return "Unknown"
    except Exception as e:
        logger.warning("⚠️ Tidak bisa ambil username: {}", e)
        return "Unknown"

# Perform mining request
def run_mining(access_token):
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        res = requests.post("https://www.keycloudapi.com/Go/_Start_VPoints", headers=headers, data={})
        if res.status_code != 200:
            logger.error("❌ Mining gagal (HTTP {}): {}", res.status_code, res.text)
            return None, None, None

        try:
            res_json = res.json()
        except Exception as e:
            logger.error("❌ Gagal parse response mining: {}", e)
            return None, None, None

        if res_json.get("State") != 200:
            logger.error("❌ Mining gagal: {}", res_json)
            return None, None, None

        ptime = res_json.get("PTime")
        power = res_json.get("Power")
        point = res_json.get("Integral")

        if ptime:
            end_time = datetime.fromtimestamp(int(ptime) / 1000)
            logger.success("✅ Mining berhasil! Selesai pada: {}", end_time.strftime('%Y-%m-%d %H:%M:%S'))
            logger.info("⚡ Power: {} | 🪙 Point: {}", power, point)
            return end_time, power, point
        else:
            logger.success("✅ Mining berhasil tanpa waktu selesai: {}", res_json)
            return None, power, point

    except Exception as e:
        logger.error("❌ Error saat mining: {}", e)
        return None, None, None

# Countdown timer
def countdown(seconds):
    logger.info("⏳ Menunggu {} detik sampai mining selanjutnya...", seconds)
    try:
        while seconds > 0 and not stop_flag:
            hrs, rem = divmod(seconds, 3600)
            mins, secs = divmod(rem, 60)
            print(f"\r⏱️  Countdown: {int(hrs):02}:{int(mins):02}:{int(secs):02}", end="", flush=True)
            time.sleep(1)
            seconds -= 1
        print("")
    except KeyboardInterrupt:
        logger.warning("⛔ Dihentikan manual oleh user.")

# Main mining loop
def main_loop():
    logger.info("🟢 Bot dimulai")
    while not stop_flag:
        next_times = []
        for account in ACCOUNTS:
            if stop_flag:
                break
            name = account.get("name", "Unknown")
            token = account.get("access_token")
            username = get_username(token)
            logger.info("🚀 Memulai proses mining untuk user: {}", username)
            end_time, power, point = run_mining(token)
            if end_time:
                wait_seconds = int((end_time - datetime.now()).total_seconds())
                next_times.append((username, wait_seconds))
            else:
                logger.warning("⚠️ Tidak dapat menentukan waktu mining selanjutnya. Menunggu 10 menit.")
                next_times.append((username, 600))
            if stop_flag:
                break
            logger.info("=======================================================")

        if next_times:
            for user, sec in next_times:
                hrs, rem = divmod(sec, 3600)
                mins, secs = divmod(rem, 60)
                logger.info("⛏️  {} harus menunggu selama: {:02}:{:02}:{:02}", user, int(hrs), int(mins), int(secs))
            max_wait = max(sec for _, sec in next_times)
            countdown(max_wait)

if __name__ == '__main__':
    main_loop()
