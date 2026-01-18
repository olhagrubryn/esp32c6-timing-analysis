#include <stdio.h>
#include "esp_cpu.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void measure_precise_add(void) {
    uint32_t start, end, empty_start, empty_end;
    uint32_t overhead, total_time;
    
    // Register vorbereiten
    register uint32_t a = 5;
    register uint32_t b = 3;
    register uint32_t res;

    // 1. OVERHEAD MESSEN (Was kostet der Aufruf von esp_cpu_get_cycle_count selbst?)
    empty_start = esp_cpu_get_cycle_count();
    empty_end = esp_cpu_get_cycle_count();
    overhead = empty_end - empty_start;

    // 2. TATSÄCHLICHE MESSUNG
    start = esp_cpu_get_cycle_count();
    
    __asm__ __volatile__ (
        "add %0, %1, %2" 
        : "=r" (res) 
        : "r" (a), "r" (b)
    );

    end = esp_cpu_get_cycle_count();

    // 3. BERECHNUNG
    total_time = end - start;
    // Netto-Zyklen = (Ende - Start) - Overhead
    // Wir nutzen int32_t für das Ergebnis, falls der Overhead 
    // durch Pipeline-Effekte minimal schwankt.
    int32_t net_cycles = (int32_t)total_time - (int32_t)overhead;

    printf("Brutto: %lu | Overhead: %lu | Netto ADD: %ld Zyklus\n", 
            total_time, overhead, net_cycles);
}

void app_main(void) {
    // Kurze Pause für stabile Taktfrequenz
    vTaskDelay(pdMS_TO_TICKS(100));

    printf("Präzise Messung (160 MHz):\n");
    for(int i = 0; i < 5; i++) {
        measure_precise_add();
    }
}