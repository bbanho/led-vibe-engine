#!/usr/bin/env python3
import asyncio
import numpy as np
import sounddevice as sd
import colorsys
import time
import random
import socket
import os
import signal
from bleak import BleakScanner, BleakClient

# --- Configurações ---
DEVICE_ADDRESS = "C5:50:EB:E3:E5:D0" 
SOCKET_PATH = "/tmp/silverblue_led.sock"
SAMPLE_RATE = 44100 
BLOCK_SIZE = 2048

# Configuração de Brilho e Cor
MIN_BRIGHTNESS = 0.2       
MAX_AUDIO_BRIGHTNESS = 0.7 
PING_BRIGHTNESS = 1.0      
SILENCE_THRESHOLD = 0.01   
READING_HUE = 0.13         
READING_SAT = 0.8          

# --- Paletas Dinâmicas ---
PALETTES = {
    "CHILL": [[0.5, 0.55, 0.6], [0.1, 0.15, 0.9], [0.08, 0.6, 1.0]],
    "PARTY": [[0.8, 0.9, 0.0], [0.4, 0.5, 0.6], [0.1, 0.5, 0.9]],
    "RAGE":  [[0.0, 0.02, 0.98], [0.0, 0.0, 0.0]],
    "WARM_COLD": [0.0, 0.12, 0.66],
    "VAPORWAVE": [0.85, 0.75, 0.5],
    "ROCK": [0.6, 0.15, 0.0],
    "JAZZ": [0.08, 0.1, 0.05],
    "TECHNO": [0.5, 0.33, 0.85],
    "LOFI": [0.75, 0.1, 0.08]
}

class VibeEngine:
    def __init__(self):
        self.onsets = []
        self.current_vibe = "JAZZ"
        self.last_switch = 0
    
    def analyze(self, energy_ratio):
        now = time.time()
        if energy_ratio > 1.5:
            self.onsets = [t for t in self.onsets if now - t < 5.0]
            if not self.onsets or (now - self.onsets[-1] > 0.1): self.onsets.append(now)
        density = len(self.onsets) / 5.0
        if now - self.last_switch > 10.0:
            if density > 4.0: self.current_vibe = "RAGE"
            elif density > 1.0: self.current_vibe = "PARTY"
            else: self.current_vibe = "JAZZ"
            self.last_switch = now
        return self.current_vibe

class LEDBLE:
    def __init__(self, device):
        self.device = device
        self.client = BleakClient(device)

    async def connect(self):
        if not self.client.is_connected: await self.client.connect()

    async def set_rgb(self, rgb):
        try:
            if not self.client.is_connected: await self.connect()
            packet = [0x56, rgb[0], rgb[1], rgb[2], 0x00, 0xF0, 0xAA]
            await self.client.write_gatt_char("0000ffe9-0000-1000-8000-00805f9b34fb", bytearray(packet), response=False)
        except: pass

class AudioReactive:
    def __init__(self):
        self.led = None
        self.running = True
        self.vibe = VibeEngine()
        self.ping_lock = asyncio.Lock()
        self.static_mode = False
        self.override_mode = False
        
        self.target_brightness = MIN_BRIGHTNESS
        self.target_hue = READING_HUE
        self.target_sat = READING_SAT
        self.current_brightness = MIN_BRIGHTNESS
        self.current_hue = READING_HUE
        self.current_sat = READING_SAT
        
        self.avg_bass = 10.0
        self.peak_hold = 0.0
        self.weather_accumulator = 0.0

    def process_audio(self, indata):
        if self.override_mode or self.static_mode: return

        fft_data = np.abs(np.fft.rfft(indata[:, 0]))
        freqs = np.fft.rfftfreq(len(indata), 1/SAMPLE_RATE)
        
        e_bass = np.sum(fft_data[(freqs > 40) & (freqs < 150)])
        rms = np.sqrt(np.mean(indata**2))
        
        if rms < SILENCE_THRESHOLD:
            self.target_brightness, self.target_hue, self.target_sat = MIN_BRIGHTNESS, READING_HUE, READING_SAT
            return

        self.avg_bass = (self.avg_bass * 0.99) + (e_bass * 0.01)
        bass_ratio = e_bass / max(self.avg_bass, 0.1)
        
        mode = self.vibe.current_vibe
        if mode in ["JAZZ", "PARTY", "RAGE", "DYNAMIC"]: mode = self.vibe.analyze(bass_ratio)

        if mode == "KCD2":
            e_rain = np.sum(fft_data[(freqs > 2000) & (freqs < 8000)])
            detected_wet = e_rain > (self.avg_bass * 1.5) and e_rain > 0.5
            if detected_wet: self.weather_accumulator = min(1.0, self.weather_accumulator + 0.05)
            else: self.weather_accumulator = max(0.0, self.weather_accumulator - 0.02)
            is_wet = self.weather_accumulator > 0.5
            e_steel = np.sum(fft_data[freqs > 4000])
            e_hooves = np.sum(fft_data[(freqs >= 60) & (freqs < 200)])
            e_thunder = np.sum(fft_data[freqs < 60])
            if e_steel > (self.avg_bass * 6.0) and e_steel > 0.6:
                self.target_hue, self.target_sat, self.target_brightness = 0.6, 0.1, 1.0
                return
            elif e_hooves > (self.avg_bass * 1.5):
                self.target_hue, self.target_sat, self.target_brightness = 0.05, 0.8, MIN_BRIGHTNESS + 0.3
                return
            else:
                self.target_hue, self.target_sat = (0.55, 0.3) if is_wet else (0.08, 0.9)
                thunder_mod = (np.sin(time.time() * 15) * 0.1) if e_thunder > (self.avg_bass * 2.0) else 0
                self.target_brightness = np.clip(MIN_BRIGHTNESS + thunder_mod + (random.uniform(-0.03, 0.03) if is_wet else 0), 0, 1.0)
            return

        SCAPES = {
            "WAR_ZONE": {
                "ambient": (0.33, 1.0), "events": [(2000, 20000, 3.0, 0.0, 0.0, 1.0), (0, 200, 3.0, 0.03, 1.0, 0.8)]
            }
        }
        if mode in SCAPES:
            s = SCAPES[mode]
            self.target_hue, self.target_sat = s["ambient"]
            self.target_brightness = MIN_BRIGHTNESS + (bass_ratio * 0.2)
            for fmin, fmax, thr, h, sat, bri in s["events"]:
                e_val = np.sum(fft_data[(freqs > fmin) & (freqs < fmax)])
                if e_val > (self.avg_bass * thr):
                    self.target_hue, self.target_sat, self.target_brightness = h, sat, bri
                    break
            return

        self.target_brightness = MIN_BRIGHTNESS + (np.clip((bass_ratio - 0.5) / 2.0, 0, 1) * (MAX_AUDIO_BRIGHTNESS - MIN_BRIGHTNESS))
        if mode in ["WARM_COLD", "VAPORWAVE", "ROCK", "JAZZ", "TECHNO", "LOFI"]:
            p = PALETTES[mode]
            idx = int(np.clip(bass_ratio * 0.5 * 2.99, 0, 2)) if mode != "WARM_COLD" else int(np.clip(bass_ratio, 0, 2))
            self.target_hue = p[idx % len(p)]
            self.target_sat = 1.0 if mode != "LOFI" else 0.5
        else:
            if np.any((freqs > 250) & (freqs < 4000)):
                mid_fft = fft_data[(freqs > 250) & (freqs < 4000)]
                centroid = np.sum(freqs[(freqs > 250) & (freqs < 4000)] * mid_fft) / (np.sum(mid_fft) + 1e-6)
                self.target_hue = np.clip((np.log10(max(centroid, 250)) - np.log10(250)) / (np.log10(4000) - np.log10(250)), 0, 1)

    async def led_control_loop(self):
        while self.running:
            if self.override_mode: await asyncio.sleep(0.05); continue
            if self.led:
                if self.static_mode: self.target_brightness, self.target_hue, self.target_sat = MIN_BRIGHTNESS, READING_HUE, READING_SAT
                if self.current_brightness <= (MIN_BRIGHTNESS + 0.01) and self.target_brightness > (MIN_BRIGHTNESS + 0.05):
                    self.current_hue = self.target_hue
                self.current_brightness = (self.current_brightness * 0.8) + (self.target_brightness * 0.2)
                diff = self.target_hue - self.current_hue
                if diff > 0.5: diff -= 1.0
                elif diff < -0.5: diff += 1.0
                speed = 0.05 if self.vibe.current_vibe in ["WAR_ZONE", "KCD2", "ROCK"] else 0.02
                self.current_hue = (self.current_hue + (diff * speed)) % 1.0
                self.current_sat = (self.current_sat * 0.8) + (self.target_sat * 0.2)
                r, g, b = colorsys.hsv_to_rgb(self.current_hue, self.current_sat, self.current_brightness)
                await self.led.set_rgb((int(r*255), int(g*255), int(b*255)))
            await asyncio.sleep(0.05)

    async def handle_ping(self, color_name):
        async with self.ping_lock:
            self.override_mode = True
            COLORS = { "green": (0, 255, 0), "red": (255, 0, 0), "blue": (0, 0, 255), "cyan": (0, 255, 255), "magenta": (255, 0, 255), "yellow": (255, 200, 0), "white": (255, 255, 255), "wine": (100, 0, 20) }
            rgb = COLORS.get(color_name.lower(), (0, 255, 0))
            if self.led:
                for _ in range(2): 
                    await self.led.set_rgb((255,255,255)); await asyncio.sleep(0.05); await self.led.set_rgb((0,0,0)); await asyncio.sleep(0.1)
                for i in range(0, 101, 20): 
                    f = i/100.0; await self.led.set_rgb((int(rgb[0]*f), int(rgb[1]*f), int(rgb[2]*f))); await asyncio.sleep(0.03)
                await asyncio.sleep(2.0)
                await self.led.set_rgb((0,0,0)); await asyncio.sleep(0.5)
            self.override_mode = False

    async def server_loop(self):
        if os.path.exists(SOCKET_PATH): os.remove(SOCKET_PATH)
        server = await asyncio.start_unix_server(self.handle_client, SOCKET_PATH)
        async with server: await server.serve_forever()

    async def handle_client(self, reader, writer):
        global READING_HUE, READING_SAT, MIN_BRIGHTNESS
        data = await reader.read(100); msg = data.decode().strip()
        if msg.startswith("PING"):
            p = msg.split(" "); color = p[1] if len(p) > 1 else "green"; asyncio.create_task(self.handle_ping(color))
        elif msg.startswith("MODE"):
            p = msg.split(" "); m = p[1].upper() if len(p) > 1 else "JAZZ"
            if m == "STATIC": self.static_mode = True
            else: self.static_mode = False; self.vibe.current_vibe = m
        elif msg.startswith("SET"):
            p = msg.split(" ")
            if len(p) >= 4:
                try: READING_HUE, READING_SAT, MIN_BRIGHTNESS = float(p[1]), float(p[2]), float(p[3])
                except: pass
        writer.close()

    async def main(self):
        asyncio.create_task(self.server_loop()) 
        while self.running:
            try:
                device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=5.0)
                if device:
                    self.led = LEDBLE(device); await self.led.connect()
                    target_id = None; devices = sd.query_devices()
                    for i, d in enumerate(devices):
                        name = d['name'].lower()
                        # Procura por Monitor de Hardware (ex: Analog Stereo Monitor), ignorando EasyEffects
                        if "monitor" in name and "easyeffects" not in name: 
                            target_id = i; break
                    
                    if target_id is None: target_id = sd.default.device[0]
                    with sd.InputStream(callback=lambda d,f,t,s: self.process_audio(d), device=target_id, channels=1, samplerate=SAMPLE_RATE):
                        await self.led_control_loop()
            except: pass
            await asyncio.sleep(5)

    async def shutdown(self):
        self.running = False
        if self.led: await self.led.set_rgb((0,0,0))
        if os.path.exists(SOCKET_PATH): os.remove(SOCKET_PATH)
        os._exit(0)

if __name__ == "__main__":
    asyncio.run(AudioReactive().main())
