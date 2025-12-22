#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_cpu.h"
#include "freertos/portmacro.h"
#include "esp_attr.h"
#include "esp_private/esp_clk.h" // Für Frequenz-Check

// -----------------------------------------------------------------------------
//  Hardware-Zähler (CSR) Setup für ESP32-C6
//  Das ersetzt esp_cpu_get_cycle_count() für maximale Präzision
// -----------------------------------------------------------------------------

static inline void init_performance_counters(void) {
    // 0x7E0 (mpcer): Bit 0 = CYCLE (Takte zählen)
    // 0x7E1 (mpcmr): Bit 0 = COUNT_EN (Zähler aktivieren)
    __asm__ __volatile__ (
        "li t0, 0x01 \n"
        "csrw 0x7E0, t0 \n" 
        "csrw 0x7E1, t0 \n"
        "csrw 0x7E2, x0 \n" // Zähler auf 0 setzen
        ::: "t0"
    );
}

static inline uint32_t get_hardware_cycle_count(void) {
    uint32_t val;
    // Liest direkt aus dem Hardware-Register mpccr
    __asm__ __volatile__ ("csrr %0, 0x7E2" : "=r"(val));
    return val;
}

// -----------------------------------------------------------------------------
//  Kritischer Abschnitt (Behalten für Stabilität)
// -----------------------------------------------------------------------------
static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;
#define ENTER_CRITICAL()  portENTER_CRITICAL(&measureMux)
#define EXIT_CRITICAL()   portEXIT_CRITICAL(&measureMux)

// -----------------------------------------------------------------------------
//  Verbesserte Mess-Funktionen
// -----------------------------------------------------------------------------

// NEU: Differenzmessung im IRAM um Cache/Flash-Latenz zu eliminieren
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_pure_add_latency_iram(void) {
    uint32_t start, end32, end64;
    
    ENTER_CRITICAL();
    // Teil 1: 32 ADDs
    start = get_hardware_cycle_count();
    __asm__ __volatile__ (
        ".align 4 \n"
        ".rept 32 \n add t0, t0, t1 \n .endr \n" ::: "t0", "t1"
    );
    end32 = get_hardware_cycle_count() - start;

    // Teil 2: 64 ADDs
    start = get_hardware_cycle_count();
    __asm__ __volatile__ (
        ".align 4 \n"
        ".rept 64 \n add t0, t0, t1 \n .endr \n" ::: "t0", "t1"
    );
    end64 = get_hardware_cycle_count() - start;
    EXIT_CRITICAL();

    return end64 - end32; // Resultat für exakt 32 ADDs ohne Overhead
}

static inline void init_performance_counters_inst(void) {
    __asm__ __volatile__ (
        "li t0, 0x02 \n"      // Bit 1 = INST (Befehle zählen)
        "csrw 0x7E0, t0 \n" 
        "csrw 0x7E1, 0x01 \n" // COUNT_EN = 1
        "csrw 0x7E2, x0 \n"   // Reset auf 0
        ::: "t0"
    );
}


// -----------------------------------------------------------------------------
//  Hauptprogramm
// -----------------------------------------------------------------------------

void run_measurements(void) {
    // Zuerst: Messung der Ticks (wie bisher)
    init_performance_counters(); 
    uint32_t ticks = measure_pure_add_latency_iram();
    
    // NEU: Messung der echten Instruktionen
    init_performance_counters_inst();
    uint32_t insts = measure_pure_add_latency_iram();

    printf("\n--- ESP32-C6 ARCHITEKTUR-BEWEIS ---\n");
    // Korrektur: %d oder %u für int, bzw. expliziter Cast
    printf("CPU Frequenz: %u Hz\n", (unsigned int)esp_clk_cpu_freq());
    printf("Hardware-Ticks für 32 ADDs: %u\n", (unsigned int)ticks);
    printf("Echte Instruktionen für 32 ADDs: %u\n", (unsigned int)insts);
    
    if (insts == 32) {
        printf("BEWEIS ERBRACHT: 1 ADD = 1 Instruktion pro Arbeitsschritt.\n");
    } else {
        printf("Info: Instruktionen gezählt: %u\n", (unsigned int)insts);
    }
}

void app_main(void) {
    vTaskDelay(1000 / portTICK_PERIOD_MS);
    run_measurements();
}