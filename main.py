import datetime
import time
import os
import pickle
from twilio.rest import Client
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# === CONFIG ===
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_PATH = 'credentials/client_secret.json'  # Dosya adını uygun şekilde değiştir
TOKEN_PATH = 'token.pickle'
# .env dosyasını yükle
load_dotenv()
# Ortam değişkenlerini al
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_FROM = os.getenv("WHATSAPP_FROM")
WHATSAPP_TO = os.getenv("WHATSAPP_TO")

# Sadece bir defa mesaj gönderilen etkinlikleri takip et
hatirlatici_gonderildi = set()

# Hedef takvimler
TAKVIMLER = [
    'primary',
    'buse.magden@masqot.co'
]

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    return service

def mesaj_gonder(etkinlik_adi):
    mesaj = f"🔔 Hatırlatma: '{etkinlik_adi}' toplantısına 30 dakika kaldı!"
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=WHATSAPP_FROM,
        to=WHATSAPP_TO,
        body=mesaj
    )
    print(f"📤 WhatsApp mesajı gönderildi: {message.sid}")

def kontrol_ve_hatirlat():
    global hatirlatici_gonderildi
    service = get_calendar_service()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.replace(microsecond=0).isoformat()

    for takvim_id in TAKVIMLER:
        try:
            events_result = service.events().list(
                calendarId=takvim_id,
                timeMin=now_iso,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        except Exception as e:
            print(f"❗ Takvim okunamadı ({takvim_id}):", e)
            continue

        events = events_result.get('items', [])
        if not events:
            print(f"Takvimde yaklaşan etkinlik yok: {takvim_id}")
            continue

        for event in events:
            summary = event.get('summary', 'Başlıksız Etkinlik')
            event_id = event.get('id')
            start_str = event['start'].get('dateTime', '')

            if not start_str:
                continue

            start_time = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            fark = (start_time - now).total_seconds() / 60

            # Sadece 30 dakika kala uyarı gönder
            if 25 <= fark <= 35 and (event_id + "_30") not in hatirlatici_gonderildi:
                mesaj_gonder(summary)
                hatirlatici_gonderildi.add(event_id + "_30")

if __name__ == "__main__":
    print("⏳ Takvim takip sistemi başlatıldı...")
    while True:
        try:
            kontrol_ve_hatirlat()
        except Exception as e:
            print("⚠️ Hata:", e)
        time.sleep(300)  # 5 dakikada bir kontrol
