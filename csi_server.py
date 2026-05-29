import serial
import numpy as np
import asyncio
import websockets
import json
import time
from collections import deque

PORT = '/dev/ttyACM0'
BAUD = 115200
WINDOW = 50
CALIBRATION_TIME = 30
TARGET_MAC = 'B0:A6:04:04:E2:20'

rssi_history = deque(maxlen=WINDOW)
calibration_variances = []
state = "WARMING_UP"
threshold = None
calibration_start = None
clients = set()
last_presence = None

async def broadcast(msg):
    if clients:
        await asyncio.gather(*[c.send(json.dumps(msg)) for c in clients])

async def handler(ws):
    clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)

async def read_serial():
    global state, threshold, calibration_start, last_presence
    loop = asyncio.get_event_loop()
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"Reading from {PORT}...")
    while True:
        try:
            line = await loop.run_in_executor(None, ser.readline)
            line = line.decode('utf-8', errors='ignore').strip()
            if not line.startswith('CSI_DATA'):
                continue
            parts = line.split(',')
            if len(parts) < 4:
                continue
            mac = parts[2].upper()
            rssi = int(parts[3])
            if mac != TARGET_MAC:
                continue
            rssi_history.append(rssi)
            if len(rssi_history) < WINDOW:
                await broadcast({"type":"warmup","count":len(rssi_history),"total":WINDOW})
                continue
            if state == "WARMING_UP":
                state = "CALIBRATING"
                calibration_start = time.time()
                print("Calibrating — leave the room!")
            variance = float(np.var(list(rssi_history)))
            elapsed = time.time() - calibration_start
            remaining = max(0, CALIBRATION_TIME - elapsed)
            if state == "CALIBRATING":
                calibration_variances.append(variance)
                progress = (elapsed / CALIBRATION_TIME) * 100
                await broadcast({"type":"calibrating","progress":round(progress,1),"remaining":round(remaining),"variance":round(variance,2),"rssi":rssi})
                if elapsed >= CALIBRATION_TIME:
                    median_var = float(np.median(calibration_variances))
                    std_var = float(np.std(calibration_variances))
                    threshold = median_var + 2 * std_var + 0.5
                    threshold = max(threshold, 0.5)
                    state = "READY"
                    print(f"Threshold: {threshold:.2f}")
                    await broadcast({"type":"calibrated","threshold":round(threshold,2)})
            elif state == "READY":
                presence = variance > threshold
                changed = presence != last_presence
                last_presence = presence
                await broadcast({"type":"detection","rssi":rssi,"variance":round(variance,2),"threshold":round(threshold,2),"presence":presence,"changed":changed})
        except Exception as e:
            await asyncio.sleep(0.01)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server on ws://localhost:8765")
        await read_serial()

asyncio.run(main())
