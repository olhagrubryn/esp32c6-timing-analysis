#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"
#include <inttypes.h>
#include "esp_rom_sys.h"  // Für esp_rom_delay_us

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
// Definiere eine globale Variable für Load-Tests (außerhalb der Funktion)
static volatile uint32_t __attribute__((aligned(4))) load_test_data = 0xDEADBEEF;

FORCE_INLINE_ATTR IRAM_ATTR void cache_warmup(void) {
    // Cache aufwärmen durch mehrmaliges Ausführen der Messfunktionen
    for (int i = 0; i < 5; i++) {
        measure_latency_chain();
        measure_throughput_chain();
    }
}

FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_load_latency_safe(void) {
    uint32_t start, end;
    volatile uint32_t *ptr = &load_test_data;
    uint32_t val;
    
    // Stelle sicher, dass der Pointer gültig ist
    if ((uintptr_t)ptr == 0) {
        return 0;
    }

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
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_branch_penalty(void) {
    uint32_t start, end;
    uint32_t iterations = 10;
    uint32_t dummy = 0;

    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n" // Start-Zeit
        
        // Wir simulieren 10 Branches.
        // Um den Predictor zu "verwirren", nutzen wir ein Muster,
        // das schwer vorherzusehen ist, oder erzwingen durch die Kürze einen Flush.
        ".rept 10\n"
        "   addi %2, %2, 1\n"   // Inkrementiere dummy
        "   beqz %2, 1f\n"      // Branch if zero (wird nie wahr sein, aber CPU muss prüfen)
        "   1:\n"
        ".endr\n"
        
        "csrr %1, 0x7E2\n" // End-Zeit
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(dummy)
        :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}
FORCE_INLINE_ATTR IRAM_ATTR void alu_test_refined(void) {
    // In alu_test_refined() dann hinzufügen:
    uint32_t branch_cycles = measure_branch_penalty();
    printf("Branch penalty (10x beqz):       %" PRIu32 " cycles\n", branch_cycles);
    printf("- Latenz pro Branch: ~%.1f cycles\n", branch_cycles / 10.0f);
    // Cache aufwärmen für konsistente Ergebnisse (nur ALU-Tests)
    for (int i = 0; i < 10; i++) {
        measure_latency_chain();
        measure_throughput_chain();
    }
    
    // Performance-Counter initialisieren
    init_performance_counters();
    
    // ALU-Messungen durchführen
    uint32_t dep_cycles = measure_latency_chain();
    uint32_t indep_cycles = measure_throughput_chain();
    
    // Warte kurz, um sicherzustellen, dass alles initialisiert ist
    esp_rom_delay_us(100);  // Korrigiert von ets_delay_us zu esp_rom_delay_us
    
    // Load-Latency Messung
    uint32_t load_cycles = measure_load_latency_safe();
    
    // Ergebnisse ausgeben mit korrekten Format-Spezifizierern
    printf("\n=== ALU Performance Test ===\n");
    printf("Dependent ADD chain (latency):   %" PRIu32 " cycles\n", dep_cycles);
    printf("Independent ADD chain (throughput): %" PRIu32 " cycles\n", indep_cycles);
    printf("Load latency (10x lw):           %" PRIu32 " cycles\n", load_cycles);
    
    if (indep_cycles > 0) {
        printf("Ratio dependent/independent: %.2f\n", 
               (float)dep_cycles / indep_cycles);
    }
    
    // Interpretation der Ergebnisse
    printf("\nInterpretation:\n");
    printf("- IPC (Instructions per Cycle) ~ %.2f\n", 10.0f / indep_cycles);
    printf("- Latenz pro ADD: ~%.1f cycles\n", dep_cycles / 10.0f);
    printf("- Latenz pro Load: ~%.1f cycles\n", load_cycles / 10.0f);
}

void app_main(void) {
    /*
    init_performance_counters();
    printf("\n--- KALIBRIERTE MESSUNG ---\n");
    
    for (int i = 0; i < 5; i++) {
        printf("Latenz (10x ADD dep.): %lu\n", measure_latency_chain());
        printf("Durchsatz (10x ADD indep.): %lu\n", measure_throughput_chain());
        printf("Load-Latenz (10x LW): %lu\n", measure_load_latency());
        printf("count_alu_capacity: %lu\n", detect_alu_count());
        printf("----------------------------\n");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
    */
    printf("\nStarting ALU performance measurement...\n");
    
    // Sicherstellen, dass der Stack und Daten initialisiert sind
    vTaskDelay(pdMS_TO_TICKS(100));
    
    // Load-Test-Daten initialisieren
    load_test_data = 0xCAFEBABE;
    
    printf("Load test data address: 0x%" PRIxPTR "\n", (uintptr_t)&load_test_data);
    
    // Mehrere Durchläufe für statistische Validität
    for (int run = 0; run < 3; run++) {
        printf("\n--- Run %d ---\n", run + 1);
        alu_test_refined();
        vTaskDelay(pdMS_TO_TICKS(100)); // Kurze Pause zwischen Durchläufen
    }
}