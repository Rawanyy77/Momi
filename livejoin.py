from telethon import TelegramClient, events

API_ID = 29136563
API_HASH = "a6162f3dd14be892cd5fbc056f279693"
CHANNEL =  "@trade_withtwt"

client = TelegramClient("livejoin_session", API_ID, API_HASH)

@client.on(events.Raw())
async def handler(event):
    print(event)

client.start()
print("Userbot started...")
client.run_until_disconnected()
