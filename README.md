# ESP32 CSI Presence Detection

Detect room occupancy using WiFi Channel State Information — no cameras, no PIR sensors, just two cheap ESP32 boards and a browser dashboard.

**Team:** Nima Chaharbaghi · Saif Meftah · Florian Milbradt

---

## How It Works

The ESP32-C3 connects to your phone hotspot and fires regular WiFi packets at 10/sec. The ESP32-C6 passively sniffs those packets on the same channel and measures how the signal changes. A person walking through the signal path absorbs and reflects WiFi at 2.4 GHz, causing measurable variance in the received signal strength. A Python script detects that variance and streams the result live to a browser dashboard.

```
Phone Hotspot (ch. 6)
       |
       | WiFi
       |
ESP32-C3 ──── packets ────► ESP32-C6 ──── serial ────► csi_server.py ────► presence_dashboard.html
(powerbank)                 (laptop USB)                WebSocket :8765      Browser
```

---

## Hardware

| Board | Role | Price |
|-------|------|-------|
| Seeed Studio XIAO ESP32-C6 | CSI receiver — passive sniffer | ~$5 |
| ESP32-C3 devkit (any) | CSI transmitter — sends packets | ~$4 |

Total hardware cost: ~$9. No soldering. Plug-and-play USB.

**Placement:** Put the two boards on opposite sides of the room or either side of a doorway. Detection improves when a person physically crosses the signal path.

---

## Repo Contents

| File | Description |
|------|-------------|
| `csi_component.h` | C6-compatible CSI callback — replaces the version in ESP32-CSI-Tool |
| `main.cc` | C6 receiver main file — replaces the version in ESP32-CSI-Tool |
| `csi_server.py` | Python WebSocket server — reads serial, detects presence, broadcasts |
| `csi_presence.py` | Optional matplotlib visualizer (debug use) |
| `presence_dashboard.html` | Browser dashboard — open locally, connects to WebSocket |
| `CSI_Presence_Detection.pptx` | Project presentation |

---

## External Repositories

| Repo | Purpose | URL |
|------|---------|-----|
| ESP-IDF v5.3 | Firmware SDK for both C3 and C6 | https://github.com/espressif/esp-idf |
| ESP32-CSI-Tool | Base firmware (modified) | https://github.com/StevenMHernandez/ESP32-CSI-Tool |

> This project uses **ESP-IDF v5.3 only** — one version handles both boards.

---

## One-Time Setup

### 1. System dependencies

```bash
sudo apt-get update
sudo apt-get install -y git wget flex bison gperf python3 python3-pip \
  python3-venv cmake ninja-build ccache libffi-dev libssl-dev \
  dfu-util libusb-1.0-0 python3-virtualenv
```

### 2. Install ESP-IDF v5.3

```bash
mkdir -p ~/esp && cd ~/esp
git clone -b v5.3 --recursive https://github.com/espressif/esp-idf.git esp-idf-v5
cd esp-idf-v5
./install.sh esp32c3 esp32c6
```

Source it each session (or add to `~/.bashrc`):

```bash
. ~/esp/esp-idf-v5/export.sh
```

### 3. Clone the CSI tool and this repo

```bash
git clone https://github.com/StevenMHernandez/esp32-csi-tool ~/esp32-csi-tool
git clone https://github.com/nimachaharbaghi/presencedetection ~/presencedetection
```

### 4. Set up the C6 receiver project

```bash
cp -r ~/esp32-csi-tool/passive ~/passive-c6
cp -r ~/esp32-csi-tool/_components ~/_components
```

Now replace the two modified files from this repo:

```bash
cp ~/presencedetection/csi_component.h ~/_components/csi_component.h
cp ~/presencedetection/main.cc ~/passive-c6/main/main.cc
```

### 5. Python dependencies

```bash
pip install numpy websockets pyserial matplotlib --break-system-packages
```

### 6. USB permissions

```bash
sudo usermod -aG dialout $USER
```

Log out and back in, then verify: `groups | grep dialout`

---

## Flash the ESP32-C3 (Transmitter)

Do this once. After flashing the C3 runs automatically on any power source.

### Step 1 — Source the environment

```bash
. ~/esp/esp-idf-v5/export.sh
```

### Step 2 — Set target and build

```bash
cd ~/esp32-csi-tool/active_sta
rm -rf build sdkconfig sdkconfig.old
idf.py set-target esp32c3
idf.py build
```

### Step 3 — Fix deprecated header (v5.x compatibility)

```bash
sed -i 's/#include "esp_spi_flash.h"/#include "spi_flash_mmap.h"/' main/main.cc
```

### Step 4 — Set WiFi credentials

Your hotspot must be on **channel 6**. Replace the values below with your hotspot name and password:

```bash
sed -i 's/CONFIG_ESP_WIFI_SSID=.*/CONFIG_ESP_WIFI_SSID="YOUR_HOTSPOT_SSID"/' sdkconfig
sed -i 's/CONFIG_ESP_WIFI_PASSWORD=.*/CONFIG_ESP_WIFI_PASSWORD="YOUR_HOTSPOT_PASSWORD"/' sdkconfig
sed -i 's/# CONFIG_SHOULD_COLLECT_CSI is not set/CONFIG_SHOULD_COLLECT_CSI=y/' sdkconfig
sed -i 's/# CONFIG_ESP_WIFI_CSI_ENABLED is not set/CONFIG_ESP_WIFI_CSI_ENABLED=y/' sdkconfig
```

### Step 5 — Build and flash

```bash
idf.py build
idf.py -p /dev/ttyACM1 flash monitor
```

### Step 6 — Note the MAC address

Look for this in the monitor output:

```
wifi:connected with YOUR_HOTSPOT_SSID
sending frames.
CSI_DATA,STA,B0:A6:04:04:E2:20,...
```

**Copy the MAC address** — you need it in `csi_server.py`. Press **Ctrl+]** to exit.

### Step 7 — Deploy on powerbank

Unplug the C3 from the laptop and plug into a powerbank. It starts transmitting on every boot — no laptop needed.

---

## Flash the ESP32-C6 (Receiver)

### Step 1 — Source the environment

```bash
. ~/esp/esp-idf-v5/export.sh
```

### Step 2 — Set target and configure

```bash
cd ~/passive-c6
rm -rf build sdkconfig sdkconfig.old
idf.py set-target esp32c6
echo "CONFIG_ESP_WIFI_CSI_ENABLED=y" >> sdkconfig
sed -i 's/CONFIG_WIFI_CHANNEL=.*/CONFIG_WIFI_CHANNEL=6/' sdkconfig
```

Check your hotspot channel and match it:

```bash
nmcli dev wifi list | grep YOUR_HOTSPOT_SSID
```

### Step 3 — Build and flash

```bash
idf.py build
idf.py -p /dev/ttyACM0 flash
```

### Step 4 — Verify

```bash
idf.py -p /dev/ttyACM0 monitor
```

You should see `CSI_DATA` lines including the C3 MAC at a steady rate. Press **Ctrl+]** to exit — the C6 keeps running.

---

## Running the System

### Step 1 — Set the C3 MAC

Open `~/presencedetection/csi_server.py` and update `TARGET_MAC`:

```python
TARGET_MAC = 'B0:A6:04:04:E2:20'   # replace with your C3 MAC
```

### Step 2 — Start the WebSocket server

```bash
python ~/presencedetection/csi_server.py
```

Expected output:

```
WebSocket server on ws://localhost:8765
Reading from /dev/ttyACM0...
```

### Step 3 — Open the dashboard

Open `presence_dashboard.html` in Chrome or Firefox (drag into browser or double-click). It connects automatically to `ws://localhost:8765`.

---

## Calibration

| Phase | Duration | What to do |
|-------|----------|-----------|
| Warming up | ~5s | Wait — collecting first samples |
| Calibrating | 30s | **Leave the room and close the door** |
| Detection | Continuous | System is live |

If you were in the room during calibration restart `csi_server.py` and try again — the baseline will be wrong otherwise.

---

## Dashboard

| State | Indicator | Sound |
|-------|-----------|-------|
| Warming up | Grey circle | None |
| Calibrating | Blue pulsing | None |
| Room empty | Green pulsing | None |
| Person detected | Red pulsing | Double ascending beep |
| Person left | Green pulsing | Double descending beep |

---

## Troubleshooting

**C3 packets not appearing in C6 output**
- Verify the C3 is connected to your hotspot (check phone for connected devices)
- Verify both boards are on the same channel: `nmcli dev wifi list`
- Make sure `TARGET_MAC` in `csi_server.py` matches exactly (uppercase, colons)

**Dashboard shows "Disconnected"**
- Make sure `csi_server.py` is running
- Check port is free: `lsof -i :8765`
- Refresh the browser

**Wrong port for C3 or C6**
```bash
ls /dev/ttyACM*
```
Try swapping ACM0 and ACM1.

**Build fails with deprecated header error**
```bash
sed -i 's/#include "esp_spi_flash.h"/#include "spi_flash_mmap.h"/' main/main.cc
```

**Detection too sensitive (false positives)** — edit `csi_server.py`:
```python
threshold = median_var + 3 * std_var + 0.5
```

**Detection misses people** — edit `csi_server.py`:
```python
threshold = median_var + 1.5 * std_var + 0.5
```

---

## Why these two files are modified

### `csi_component.h`

The original file from ESP32-CSI-Tool uses struct fields (`sig_mode`, `mcs`, `cwb`, etc.) that only exist on older ESP32 variants and are absent from the ESP32-C6 hardware. This replacement outputs the fields available on C6 — `rssi`, `rate`, `sig_len`, `len` — and keeps the same CSV column layout so the Python script works without changes.

### `main.cc`

The original `main.cc` from the passive project is missing `esp_event_loop_create_default()`, which causes a crash loop on the C6 under ESP-IDF v5.x. It also includes headers removed in v5.x. This replacement adds the event loop call before WiFi init and fixes the includes.

---

## Credits

- **ESP32-CSI-Tool** by Steven M. Hernandez (MIT License)
  https://github.com/StevenMHernandez/ESP32-CSI-Tool

- **ESP-IDF** by Espressif Systems (Apache 2.0 License)
  https://github.com/espressif/esp-idf
