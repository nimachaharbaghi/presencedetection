import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time

PORT = '/dev/ttyACM0'
BAUD = 115200
WINDOW = 50
CALIBRATION_TIME = 30
TARGET_MAC = 'B0:A6:04:04:E2:20'

rssi_history = deque(maxlen=WINDOW)  # starts empty, no zeros!
variance_history = deque([0] * 200, maxlen=200)
presence_history = deque([0] * 200, maxlen=200)
calibration_variances = []

state = "WARMING_UP"  # wait for window to fill before calibrating
threshold = None
calibration_start = None

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
fig.suptitle(f'ESP32-C6 Presence Detection — C3: {TARGET_MAC}', fontsize=13)

ser = serial.Serial(PORT, BAUD, timeout=1)

def update(frame):
    global state, threshold, calibration_start

    try:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line.startswith('CSI_DATA'):
            return
        parts = line.split(',')
        if len(parts) < 4:
            return
        mac = parts[2].upper()
        rssi = int(parts[3])
        if mac != TARGET_MAC:
            return

        rssi_history.append(rssi)

        # Wait until window is full before doing anything
        if len(rssi_history) < WINDOW:
            ax1.clear()
            ax1.set_title(f'Warming up... {len(rssi_history)}/{WINDOW} samples')
            fig.patch.set_facecolor('#eeeeee')
            return

        # Start calibration once window is full
        if state == "WARMING_UP":
            state = "CALIBRATING"
            calibration_start = time.time()
            print("Window full — starting calibration. PLEASE LEAVE THE ROOM!")

        variance = float(np.var(list(rssi_history)))
        elapsed = time.time() - calibration_start
        remaining = max(0, CALIBRATION_TIME - elapsed)

        if state == "CALIBRATING":
            calibration_variances.append(variance)
            progress = (elapsed / CALIBRATION_TIME) * 100

            ax1.clear()
            ax1.plot(list(rssi_history), color='cyan', linewidth=1.5)
            ax1.set_title(f'RSSI — {rssi} dBm | variance: {variance:.2f}')
            ax1.set_ylabel('RSSI (dBm)')
            ax1.set_ylim(-110, -30)
            ax1.grid(True, alpha=0.3)

            ax2.clear()
            ax2.text(0.5, 0.5,
                    f'⚠ PLEASE LEAVE THE ROOM ⚠\n\n{remaining:.0f} seconds remaining\n\nvariance: {variance:.2f}',
                    transform=ax2.transAxes, ha='center', va='center',
                    fontsize=16, color='darkblue',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
            ax2.axis('off')

            ax3.clear()
            ax3.barh([''], [progress], color='royalblue', alpha=0.7)
            ax3.set_xlim(0, 100)
            ax3.set_title(f'Calibration: {progress:.0f}%')
            fig.patch.set_facecolor('#cce5ff')

            if elapsed >= CALIBRATION_TIME:
                median_var = np.median(calibration_variances)
                std_var = np.std(calibration_variances)
                threshold = median_var + 2 * std_var + 0.5
                threshold = max(threshold, 0.5)
                state = "READY"
                variance_history.clear()
                presence_history.clear()
                print(f"\nCalibration done!")
                print(f"Empty room: median={median_var:.2f}, std={std_var:.2f}")
                print(f"Threshold: {threshold:.2f}")

        elif state == "READY":
            variance_history.append(variance)
            presence = 1 if variance > threshold else 0
            presence_history.append(presence)
            status = "PERSON DETECTED 🔴" if presence else "ROOM EMPTY 🟢"

            ax1.clear()
            ax1.plot(list(rssi_history), color='cyan', linewidth=1.5)
            ax1.set_title(f'RSSI — {rssi} dBm | variance: {variance:.2f} | threshold: {threshold:.2f}')
            ax1.set_ylabel('RSSI (dBm)')
            ax1.set_ylim(-110, -30)
            ax1.grid(True, alpha=0.3)

            ax2.clear()
            ax2.plot(list(variance_history), color='orange', linewidth=1.5)
            ax2.axhline(y=threshold, color='red', linestyle='--',
                       linewidth=2, label=f'Threshold: {threshold:.1f}')
            ax2.set_title('Variance')
            ax2.set_ylabel('Variance')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            ax3.clear()
            ax3.fill_between(range(len(presence_history)),
                            list(presence_history), color='red', alpha=0.6)
            ax3.set_title(f'Status: {status}', fontsize=13,
                         color='red' if presence else 'green',
                         fontweight='bold')
            ax3.set_ylim(-0.1, 1.5)
            ax3.set_yticks([0, 1])
            ax3.set_yticklabels(['Empty', 'Person'])
            ax3.grid(True, alpha=0.3)
            fig.patch.set_facecolor('#ffcccc' if presence else '#ccffcc')

    except Exception:
        pass

print("=================================")
print("Warming up — collecting first samples...")
print("=================================")

ani = animation.FuncAnimation(fig, update, interval=50, cache_frame_data=False)
plt.tight_layout()
plt.show()
ser.close()
