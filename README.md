# ESP32 CSI Presence Detection

A WiFi Channel State Information (CSI) based room presence detection system using two ESP32 boards, a Python WebSocket server, and a live web dashboard.

---

## How It Works

The ESP32-C3 connects to your phone hotspot and sends regular WiFi ping packets. The ESP32-C6 passively sniffs those packets and measures how the signal changes. When a person walks through the signal path, their body absorbs and reflects WiFi waves — causing measurable changes in the CSI data. A Python script detects this variance and streams the result to a browser dashboard in real time.

```
Phone Hotspot
     |
     |  WiFi ch.6
     |
ESP32-C3 (powerbank) ----packets----> ESP32-C6 (laptop USB)
  Transmitter                           Receiver
  active_sta firmware                   passive-c6 firmware
                                              |
                                        csi_server.py
                                              |
                                     presence_dashboard.html
```

---

## Hardware Required

| Component | Role |
|-----------|------|
| Seeed Studio XIAO ESP32-C6 | CSI receiver — passive sniffer |
| ESP32-C3 devkit (any) | CSI transmitter — sends packets |
| USB cable × 2 | Flashing both boards |
| Powerbank | Power the C3 wirelessly after flashing |
| Phone hotspot or WiFi router | Access point on channel 6 |
| Linux laptop/PC | Runs Python server + browser dashboard |

**Placement tip:** Put the C3 and C6 on opposite sides of the room or either side of a doorway. Detection improves when a person physically crosses the signal path between the two boards.

---

## Repositories Used

| Repo | Purpose | URL |
|------|---------|-----|
| ESP-IDF v5.3 | Build firmware for both C3 and C6 | https://github.com/espressif/esp-idf |
| ESP32-CSI-Tool | Base firmware for active_sta (C3) and passive (C6) | https://github.com/StevenMHernandez/ESP32-CSI-Tool |

> **Note:** This project uses ESP-IDF v5.3 for both boards — one version handles everything.

---

## Project File Structure

```
~/
├── esp/
│   └── esp-idf-v5/                   # ESP-IDF v5.3 (cloned from repo)
├── Desktop/espcir/
│   ├── esp32-csi-tool/               # Cloned from ESP32-CSI-Tool repo
│   │   └── active_sta/               # C3 transmitter firmware (minor edits)
│   ├── passive-c6/                   # Copied from esp32-csi-tool/passive/
│   │   └── main/
│   │       └── main.cc               # ← replaced with version from this repo
│   └── _components/                  # Copied from esp32-csi-tool/_components/
│       └── csi_component.h           # ← replaced with version from this repo
├── csi_server.py                     # From this repo
└── presence_dashboard.html           # From this repo
```

---

## One-Time Installation

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

Source it (add to `~/.bashrc` to make permanent):

```bash
. ~/esp/esp-idf-v5/export.sh
```

### 3. Clone the CSI tool

```bash
git clone https://github.com/StevenMHernandez/esp32-csi-tool \
  ~/Desktop/espcir/esp32-csi-tool
```

### 4. Set up the C6 receiver project

```bash
cp -r ~/Desktop/espcir/esp32-csi-tool/passive ~/Desktop/espcir/passive-c6
cp -r ~/Desktop/espcir/esp32-csi-tool/_components ~/Desktop/espcir/
```

Now replace the two files with the versions from **this repo**:

```bash
cp csi_component.h ~/Desktop/espcir/_components/csi_component.h
cp main.cc ~/Desktop/espcir/passive-c6/main/main.cc
```

### 5. Python dependencies

```bash
pip install numpy websockets pyserial matplotlib --break-system-packages
```

### 6. USB permissions

```bash
sudo usermod -aG dialout $USER
```

Log out and back in, then verify:

```bash
groups | grep dialout
```

---

## Flash the ESP32-C3 (Transmitter)

Do this once. After flashing the C3 runs automatically on any power source.

### Step 1 — Source the environment

```bash
. ~/esp/esp-idf-v5/export.sh
```

### Step 2 — Navigate and set target

```bash
cd ~/Desktop/espcir/esp32-csi-tool/active_sta
rm -rf build sdkconfig sdkconfig.old
idf.py set-target esp32c3
idf.py build
```

### Step 3 — Fix deprecated header (v5.x compatibility)

```bash
sed -i 's/#include "esp_spi_flash.h"/#include "spi_flash_mmap.h"/' main/main.cc
```

### Step 4 — Set WiFi credentials

Replace `YOUR_HOTSPOT_SSID` and `YOUR_HOTSPOT_PASSWORD` with your phone hotspot or router. Make sure it is broadcasting on **channel 6**.

```bash
sed -i 's/CONFIG_ESP_WIFI_SSID=.*/CONFIG_ESP_WIFI_SSID="YOUR_HOTSPOT_SSID"/' sdkconfig
sed -i 's/CONFIG_ESP_WIFI_PASSWORD=.*/CONFIG_ESP_WIFI_PASSWORD="YOUR_HOTSPOT_PASSWORD"/' sdkconfig
sed -i 's/# CONFIG_SHOULD_COLLECT_CSI is not set/CONFIG_SHOULD_COLLECT_CSI=y/' sdkconfig
sed -i 's/# CONFIG_ESP_WIFI_CSI_ENABLED is not set/CONFIG_ESP_WIFI_CSI_ENABLED=y/' sdkconfig
```

### Step 5 — Build and flash

Check which port the C3 is on:

```bash
ls /dev/ttyACM*
```

Plug in the C3 (usually `/dev/ttyACM1` if the C6 is also plugged in):

```bash
idf.py build
idf.py -p /dev/ttyACM1 flash monitor
```

### Step 6 — Note the MAC address

In the monitor output look for:

```
wifi:connected with YOUR_HOTSPOT_SSID
Got ip: 172.x.x.x
sending frames.
CSI_DATA,STA,B0:A6:04:04:E2:20,...
```

**Write down the MAC address** — you need it in `csi_server.py`. Press **Ctrl+]** to exit.

### Step 7 — Deploy on powerbank

Unplug the C3 from the laptop and plug it into a powerbank. It starts transmitting automatically on every boot.

---

## Flash the ESP32-C6 (Receiver)

### Step 1 — Source the environment

```bash
. ~/esp/esp-idf-v5/export.sh
```

### Step 2 — Set target and configure

```bash
cd ~/Desktop/espcir/passive-c6
rm -rf build sdkconfig sdkconfig.old
idf.py set-target esp32c6
echo "CONFIG_ESP_WIFI_CSI_ENABLED=y" >> sdkconfig
sed -i 's/CONFIG_WIFI_CHANNEL=.*/CONFIG_WIFI_CHANNEL=6/' sdkconfig
```

Check your hotspot channel first and match it:

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

You should see `CSI_DATA` lines including the C3 MAC. Press **Ctrl+]** to exit — the C6 keeps running.

---

## Running the System

### Step 1 — Set the C3 MAC in the server

Open `csi_server.py` and update `TARGET_MAC` with the MAC you noted:

```python
TARGET_MAC = 'B0:A6:04:04:E2:20'   # replace with your C3 MAC
```

### Step 2 — Start the WebSocket server

```bash
python ~/csi_server.py
```

You should see:

```
WebSocket server on ws://localhost:8765
Reading from /dev/ttyACM0...
```

### Step 3 — Open the dashboard

Open `presence_dashboard.html` in Chrome or Firefox (drag into browser or double-click). It connects automatically to `ws://localhost:8765`.

---

## Calibration Procedure

| Phase | Duration | What to do |
|-------|----------|-----------|
| Warming up | ~5s | Wait — collecting initial samples |
| Calibrating | 30s | **Leave the room and close the door** |
| Detection | Continuous | System is live |

If you were in the room during calibration the threshold will be wrong — restart `csi_server.py` and try again.

---

## Dashboard Guide

| State | Indicator | Sound |
|-------|-----------|-------|
| Warming up | Grey circle | None |
| Calibrating | Blue pulsing | None |
| Room empty | Green pulsing | None |
| Person detected | Red pulsing | Double ascending beep |
| Person left | Green pulsing | Double descending beep |

---

## Troubleshooting

**No CSI data from C3 MAC**
- Verify the C3 is connected to your hotspot (check phone for connected devices)
- Verify both boards are on the same channel: `nmcli dev wifi list`
- Make sure `TARGET_MAC` in `csi_server.py` matches exactly (uppercase, colons)

**Dashboard shows "Disconnected"**
- Make sure `csi_server.py` is running
- Check port is free: `lsof -i :8765`
- Refresh the browser

**Port not found**
```bash
ls /dev/ttyACM*
```
Try swapping ACM0 and ACM1.

**Build fails with deprecated API errors**
```bash
sed -i 's/#include "esp_spi_flash.h"/#include "spi_flash_mmap.h"/' main/main.cc
sed -i 's/#include "tcpip_adapter.h"/#include "esp_netif.h"/' main/main.cc
```

**Detection too sensitive (false positives)** — increase multiplier in `csi_server.py`:
```python
threshold = median_var + 3 * std_var + 0.5
```

**Detection misses people** — decrease it:
```python
threshold = median_var + 1.5 * std_var + 0.5
```

---

## Repo File Reference

### `csi_component.h`

This replaces `~/Desktop/espcir/_components/csi_component.h` after copying from the CSI tool repo. The original file uses ESP32-specific struct fields (`sig_mode`, `mcs`, `cwb`, etc.) that do not exist on the ESP32-C6. This version outputs the fields available on C6 and zeros for the rest, keeping the same CSV column layout.

```cpp
#pragma once
#include <cstdio>
#include <cstring>
#include "esp_wifi.h"

static int _csi_count = 0;

static void _wifi_csi_cb(void *ctx, wifi_csi_info_t *data) {
    _csi_count++;
    char mac[20] = {0};
    sprintf(mac, "%02X:%02X:%02X:%02X:%02X:%02X",
            data->mac[0], data->mac[1], data->mac[2],
            data->mac[3], data->mac[4], data->mac[5]);
    printf("CSI_DATA,%d,%s,%d,%d,%d,%d\n",
        _csi_count, mac,
        data->rx_ctrl.rssi,
        data->rx_ctrl.rate,
        data->rx_ctrl.sig_len,
        data->len);
}

static void csi_init(char *ssid) {
    printf("CSI init starting...\n");
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(&_wifi_csi_cb, NULL));
    wifi_csi_config_t cfg = {};
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi(1));
    printf("CSI enabled!\n");
}
```

---

### `main.cc`

This replaces `~/Desktop/espcir/passive-c6/main/main.cc` after copying the passive project from the CSI tool repo. The original `main.cc` is missing `esp_event_loop_create_default()` which causes a crash loop on the C6, and includes headers not available in ESP-IDF v5.x.

```cpp
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "../../_components/nvs_component.h"
#include "../../_components/csi_component.h"

#ifdef CONFIG_WIFI_CHANNEL
#define WIFI_CHANNEL CONFIG_WIFI_CHANNEL
#else
#define WIFI_CHANNEL 6
#endif

static int pkt_count = 0;

void promiscuous_cb(void *buf, wifi_promiscuous_pkt_type_t type) {
    pkt_count++;
    if (pkt_count % 100 == 0) {
        printf("Packets received: %d\n", pkt_count);
    }
}

void passive_init() {
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_NULL));
    ESP_ERROR_CHECK(esp_wifi_start());
    esp_wifi_set_promiscuous_rx_cb(promiscuous_cb);
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
    printf("Sniffer started on channel %d\n", WIFI_CHANNEL);
}

extern "C" void app_main(void) {
    nvs_init();
    passive_init();
    csi_init((char *) "PASSIVE");
    printf("Waiting for packets...\n");
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        printf("Alive, packets so far: %d\n", pkt_count);
    }
}
```

---

## Credits

- **ESP32-CSI-Tool** by Steven M. Hernandez (MIT License)
  https://github.com/StevenMHernandez/ESP32-CSI-Tool

- **ESP-IDF** by Espressif Systems (Apache 2.0 License)
  https://github.com/espressif/esp-idf
