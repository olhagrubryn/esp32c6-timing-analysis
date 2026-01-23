#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"
#include <inttypes.h>

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

static inline void init_performance_counters(void) {
    __asm__ __volatile__ ("li t0, 1\n csrw 0x7E0, t0\n csrw 0x7E1, t0\n" ::: "t0");
}

// 1. LATENZ-KETTE (Abhängig: Jedes ADD wartet auf das vorherige)
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_latency_chain(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1; 
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n add %2, %2, %2\n .endr\n" // Wiederholt ADD 10x (a = a + a)
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(a) :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) -1;
}

// 2. DURCHSATZ-KETTE (Unabhängig: Befehle können theoretisch parallel/überlappend)
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_throughput_chain(void) {
    uint32_t start, end;
    register uint32_t t1 __asm__("t1") = 1, t2 __asm__("t2") = 2, t3 __asm__("t3") = 3;
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 3\n add %2, %2, %2\n add %3, %3, %3\n add %4, %4, %4\n .endr\n"
        "add %2, %2, %2\n" // Insgesamt 10 Befehle
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(t1), "+r"(t2), "+r"(t3) :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1 ;
}

FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_load_latency(void) {
    uint32_t start, end;
    // Verwende "aligned" Attribute um Ausrichtung sicherzustellen
    static volatile uint32_t __attribute__((aligned(4))) data = 42;
    volatile uint32_t *ptr = &data;
    uint32_t val;

    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n lw %2, 0(%3)\n .endr\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "=&r"(val)  // "=&r" = early-clobber
        : "r"(ptr)
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}
void app_main(void) {
    init_performance_counters();
    printf("\n--- KALIBRIERTE MESSUNG ---\n");
    
    for (int i = 0; i < 5; i++) {
        printf("Latenz (10x ADD dep.): %lu\n", measure_latency_chain());
        printf("Durchsatz (10x ADD indep.): %lu\n", measure_throughput_chain());
        printf("Load-Latenz (10x LW): %lu\n", measure_load_latency());
        printf("----------------------------\n");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}