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
        _csi_count,
        mac,
        data->rx_ctrl.rssi,
        data->rx_ctrl.rate,
        data->rx_ctrl.sig_len,
        data->len
    );
}

static void csi_init(char *ssid) {
    printf("CSI init starting...\n");
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(&_wifi_csi_cb, NULL));
    wifi_csi_config_t cfg = {};
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi(1));
    printf("CSI enabled!\n");
}
