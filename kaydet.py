import os
import time
import random
import threading
import subprocess
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from playwright.sync_api import sync_playwright

AUDIO_FILENAME = "gecici_ses.wav"
SAMPLE_RATE = 44100
audio_frames = []
recording = True

def record_system_audio():
    """Sistem sesini (hoparlörden çıkan oyun müziği ve efektlerini) arka planda kaydeder."""
    global recording, audio_frames
    
    # Windows'ta hoparlör/loopback çıkışını bulma
    wasapi_device = None
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and ('loopback' in dev['name'].lower() or 'stereo mix' in dev['name'].lower() or 'hoparlör' in dev['name'].lower() or 'speaker' in dev['name'].lower()):
            wasapi_device = idx
            break
            
    def callback(indata, frames, time_info, status):
        if recording:
            audio_frames.append(indata.copy())

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=2, callback=callback, device=wasapi_device):
            while recording:
                time.sleep(0.1)
    except Exception as e:
        # Standart mikrofon/giriş cihazı yedeği
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=2, callback=callback):
            while recording:
                time.sleep(0.1)

print("1. Ses kayıt motoru başlatılıyor...")
audio_thread = threading.Thread(target=record_system_audio)
audio_thread.start()

with sync_playwright() as p:
    # Chromium'u otomatik ses çalma izni ile açıyoruz
    browser = p.chromium.launch(
        headless=False,
        args=["--autoplay-policy=no-user-gesture-required"]
    )
    
    # YOUTUBE SHORTS FORMATI (1080x1920 Dikey ve 2x Retina Netliği)
    context = browser.new_context(
        record_video_dir="videolar/",
        viewport={"width": 450, "height": 800},
        screen={"width": 1080, "height": 1920},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()

    print("2. Web sitesi dikey Shorts formatında açılıyor...")
    page.goto("https://elifhazarr19-lab.github.io/challenge1/")
    time.sleep(2)

    # Müziği başlat
    try:
        page.click("#musicToggleBtn")
        print("-> Ambiyans müzik açıldı.")
        time.sleep(1)
    except:
        pass

    # 3 oyun modunu bul
    start_buttons = page.locator("button:has-text('Başla')").all()
    print(f"-> Toplam {len(start_buttons)} oyun modu sırayla oynanacak...")

    # Sırayla her oyunu oyna
    for i, btn in enumerate(start_buttons):
        print(f"-> Oyun {i+1} başlatılıyor...")
        btn.click()
        time.sleep(2)

        start_time = time.time()
        while time.time() - start_time < 7:
            stage_buttons = page.query_selector_all("#gameStage button")
            if stage_buttons:
                random.choice(stage_buttons).click()
            time.sleep(0.9)

        print(f"-> Oyun {i+1} bitti, lobiye dönülüyor...")
        try:
            page.click("button:has-text('Menüye Dön')")
        except:
            try:
                page.click("button:has-text('Çıkış')")
            except:
                pass
        time.sleep(1.2)

    time.sleep(1)
    context.close()
    browser.close()

# Ses kaydını durdur ve WAV olarak kaydet
recording = False
audio_thread.join()

if audio_frames:
    audio_data = np.concatenate(audio_frames, axis=0)
    write(AUDIO_FILENAME, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
    print("3. Ses dosyası hazırlandı.")

# Playwright tarafından üretilen en son video dosyasını bulma
video_files = [os.path.join("videolar", f) for f in os.listdir("videolar") if f.endswith(".webm")]
if video_files:
    latest_video = max(video_files, key=os.path.getctime)
    final_output = os.path.join("videolar", "Shorts_Sesli_Oynanis.mp4")
    
    print("4. Görüntü ve ses birleştiriliyor...")
    # ffmpeg varsa birleştirir, yoksa dosyaları klasörde ayrı bırakır
    try:
        cmd = f'ffmpeg -y -i "{latest_video}" -i "{AUDIO_FILENAME}" -c:v copy -c:a aac -shortest "{final_output}"'
        subprocess.run(cmd, shell=True, check=True)
        print(f"\nTEBRİKLER! Sesli Shorts videon hazır: {final_output}")
        if os.path.exists(AUDIO_FILENAME):
            os.remove(AUDIO_FILENAME)
    except Exception:
        print(f"\nVideo dikey olarak kaydedildi: {latest_video}")
        print(f"Ses dosyası kaydedildi: {AUDIO_FILENAME}")