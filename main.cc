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
#define WIFI_CHANNEL 11
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
