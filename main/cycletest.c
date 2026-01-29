// main/cycletest.c - Korrigierte Version
#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "performance_counter.h"

// Include für generierte Tests
#include "generated_tests.h"

// Performance Counter Initialisierung
void init_performance_counters(void) {
    // ESP32-C6 Performance Counter aktivieren
    __asm__ __volatile__ ("li t0, 1\n csrw 0x7E0, t0\n csrw 0x7E1, t0\n" ::: "t0");
}

void app_main(void) {
    printf("\n=== ESP32-C6 Performance Analysis ===\n");
    
    // Initialize
    init_performance_counters();
    
    // Kurze Pause
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    printf("\n1. Running complete latency analysis...\n");
    // Komplette Analyse (falls vorhanden)
    // run_complete_latency_analysis();
    
    vTaskDelay(pdMS_TO_TICKS(500));
    
    printf("\n2. Running generated instruction tests...\n");
    // Generierte Tests
    run_all_generated_tests();
    
    vTaskDelay(pdMS_TO_TICKS(500));
    
    printf("\n=== All tests completed ===\n");
    
    // Optional: Neustart nach einer Weile
    vTaskDelay(pdMS_TO_TICKS(3000));
    printf("Restarting...\n");
    // esp_restart();
}