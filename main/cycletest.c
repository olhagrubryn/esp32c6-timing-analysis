#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

// Performance Counter Initialisierung
static inline void init_performance_counters(void) {
    __asm__ __volatile__ ("li t0, 1\n csrw 0x7E0, t0\n csrw 0x7E1, t0\n" ::: "t0");
}

// ===== GRUNDLEGENDE MESSUNGEN =====

// 1. LATENZ-KETTE (abhängige ADDs)
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_latency_chain(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1; 
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n add %2, %2, %2\n .endr\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(a) :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// 2. DURCHSATZ-KETTE (unabhängige ADDs)
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_throughput_chain(void) {
    uint32_t start, end;
    register uint32_t t1 __asm__("t1") = 1, t2 __asm__("t2") = 2, t3 __asm__("t3") = 3;
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 3\n add %2, %2, %2\n add %3, %3, %3\n add %4, %4, %4\n .endr\n"
        "add %2, %2, %2\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(t1), "+r"(t2), "+r"(t3) :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// 3. SICHERE LOAD-LATENZ (ohne IRAM_ATTR)
FORCE_INLINE_ATTR uint32_t measure_load_latency_safe(void) {
    uint32_t start, end;
    // Verwende eine lokale, statische Variable die gut ausgerichtet ist
    static volatile uint32_t __attribute__((aligned(4))) test_value = 0xDEADBEEF;
    uint32_t val;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "la t4, test_value_label\n"
        ".rept 10\n lw %2, 0(t4)\n .endr\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "=&r"(val)
        : 
        : "t4", "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
    
    // Label für die Adresse
    __asm__ __volatile__ ("test_value_label: .word 0xDEADBEEF\n");
}

// Alternative: Stack-basierte Load-Latency (am sichersten)
FORCE_INLINE_ATTR uint32_t measure_load_latency_stack(void) {
    uint32_t start, end;
    // Verwende Stack-Variable
    volatile uint32_t stack_value __attribute__((aligned(4))) = 0xCAFEBABE;
    uint32_t val;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n lw %2, 0(sp)\n .endr\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "=&r"(val)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// ===== ERWEITERTE ANALYSE =====

// A. Komplexe Abhängigkeiten (keine Optimierung möglich)
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_complex_dependencies(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    register uint32_t b __asm__("t2") = 2;
    register uint32_t c __asm__("t3") = 3;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n"
        "add %1, %1, %2\n"   // a = a + b
        "add %2, %2, %3\n"   // b = b + c
        "add %3, %3, %1\n"   // c = c + a
        ".endr\n"
        "csrr %4, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "+r"(c), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// B. Gemischte ALU-Operationen
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_mixed_alu_ops(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 0x12345678;
    register uint32_t b __asm__("t2") = 0x87654321;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "add %1, %1, %2\n"   // ADD
        "sub %1, %1, %2\n"   // SUB
        "xor %1, %1, %2\n"   // XOR
        "or  %1, %1, %2\n"   // OR
        "and %1, %1, %2\n"   // AND
        "sll %1, %1, %2\n"   // SLL
        "srl %1, %1, %2\n"   // SRL
        "sra %1, %1, %2\n"   // SRA
        "slt %1, %1, %2\n"   // SLT
        "sltu %1, %1, %2\n"  // SLTU
        "csrr %3, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// C. Branch-Penalty Test
FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_branch_penalty(void) {
    uint32_t start, end;
    register uint32_t counter __asm__("t1") = 0;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n"
        "addi %1, %1, 1\n"      // Inkrement
        "beqz %1, 1f\n"         // Branch (wird nie genommen)
        "1:\n"
        ".endr\n"
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(counter), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// ===== SIMPLER TEST (nur ALU, keine Loads) =====

void run_simple_alu_test(void) {
    printf("\n=== ESP32-C6 ALU Performance Test ===\n");
    printf("Compiler: riscv32-esp-elf-gcc, Optimization: -Og\n\n");
    
    // Cache Warmup (nur ALU)
    printf("Performing ALU cache warmup...\n");
    for (int i = 0; i < 5; i++) {
        measure_latency_chain();
        measure_throughput_chain();
        measure_complex_dependencies();
    }
    
    // Mehrere Durchläufe für Statistik
    const int NUM_RUNS = 5;
    uint32_t latency_sum = 0, throughput_sum = 0;
    uint32_t complex_sum = 0, mixed_sum = 0, branch_sum = 0;
    
    for (int run = 0; run < NUM_RUNS; run++) {
        printf("\n--- Run %d/%d ---\n", run + 1, NUM_RUNS);
        
        uint32_t latency = measure_latency_chain();
        uint32_t throughput = measure_throughput_chain();
        uint32_t complex = measure_complex_dependencies();
        uint32_t mixed = measure_mixed_alu_ops();
        uint32_t branch = measure_branch_penalty();
        
        printf("Basic Measurements:\n");
        printf("  ADD Latency (10x):      %" PRIu32 " cycles\n", latency);
        printf("  ADD Throughput (10x):   %" PRIu32 " cycles\n", throughput);
        
        printf("Advanced Analysis:\n");
        printf("  Complex Dep. (30x):     %" PRIu32 " cycles\n", complex);
        printf("  Mixed ALU Ops (10x):    %" PRIu32 " cycles\n", mixed);
        printf("  Branch Penalty (10x):   %" PRIu32 " cycles\n", branch);
        
        // Summen für Durchschnitt
        latency_sum += latency;
        throughput_sum += throughput;
        complex_sum += complex;
        mixed_sum += mixed;
        branch_sum += branch;
        
        vTaskDelay(pdMS_TO_TICKS(200));
    }
    
    // Durchschnittliche Ergebnisse
    printf("\n=== AVERAGE RESULTS (over %d runs) ===\n", NUM_RUNS);
    
    float avg_latency = latency_sum / (float)NUM_RUNS;
    float avg_throughput = throughput_sum / (float)NUM_RUNS;
    float avg_complex = complex_sum / (float)NUM_RUNS;
    float avg_mixed = mixed_sum / (float)NUM_RUNS;
    float avg_branch = branch_sum / (float)NUM_RUNS;
    
    printf("\nPer Operation Analysis:\n");
    printf("  ADD Latency:          %.2f cycles/op\n", avg_latency / 10.0f);
    printf("  ADD Throughput:       %.2f cycles/op\n", avg_throughput / 10.0f);
    printf("  Complex Dep. ADD:     %.2f cycles/op\n", avg_complex / 30.0f);
    printf("  Mixed ALU Op:         %.2f cycles/op\n", avg_mixed / 10.0f);
    printf("  Branch Penalty:       %.2f cycles/op\n", avg_branch / 10.0f);
    
    printf("\nPerformance Ratios:\n");
    printf("  Latency/Throughput:   %.2f (ideal > 1.0)\n", avg_latency / avg_throughput);
    printf("  Complex/Simple ADD:   %.2f\n", (avg_complex / 30.0f) / (avg_latency / 10.0f));
    
    printf("\nIPC Calculation:\n");
    printf("  Theoretical IPC (ADD):  %.2f\n", 10.0f / avg_throughput);

}
// ===== SEPARATER LOAD-TEST (optional) =====

void run_load_test_separately(void) {
    printf("\n=== Optional: Load Latency Test ===\n");
    printf("Note: This test may fail due to memory access restrictions\n");
    
    // Versuche Load-Test mit Stack-Variable
    printf("Attempting stack-based load test...\n");
    
    // 1. CACHE WARMUP für Load-Test
    printf("Performing cache warmup for load test...\n");
    for (int i = 0; i < 5; i++) {
        // Verwende eine einfache Load-Operation für Warmup
        volatile uint32_t warmup_var __attribute__((aligned(4))) = 0x12345678;
        uint32_t dummy;
        
        // Mehrere Reads um Cache zu füllen
        for (int j = 0; j < 10; j++) {
            dummy = warmup_var;
        }
        
        // Auch die eigentliche Messfunktion aufwärmen
        measure_load_latency_stack();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    
    // 2. MEHRERE MESSUNGEN für bessere Statistik
    const int NUM_MEASUREMENTS = 5;
    uint32_t load_sum = 0;
    int successful_measurements = 0;
    
    for (int i = 0; i < NUM_MEASUREMENTS; i++) {
        printf("\nLoad test measurement %d/%d: ", i + 1, NUM_MEASUREMENTS);
        
        uint32_t load_result = measure_load_latency_stack();
        
        if (load_result > 0 && load_result < 10000) { // Plausibilitätscheck
            printf("%" PRIu32 " cycles\n", load_result);
            load_sum += load_result;
            successful_measurements++;
        } else {
            printf("failed/invalid\n");
        }
        
        // Kurze Pause zwischen Messungen
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    
    // 3. ERGEBNISSE
    if (successful_measurements > 0) {
        uint32_t avg_load = load_sum / successful_measurements;
        
        printf("\n=== LOAD TEST RESULTS ===\n");
        printf("Successful measurements: %d/%d\n", successful_measurements, NUM_MEASUREMENTS);
        printf("Average load latency (10x lw): %" PRIu32 " cycles\n", avg_load);
        printf("Average per load: %.2f cycles\n", avg_load / 10.0f);
        
        // Vergleich mit ALU (angenommen 1 Zyklus/ADD)
        printf("\nLoad/ALU ratio estimation:\n");
        printf("Assuming ~1 cycle/ADD, Load is ~%.1fx slower\n", avg_load / 10.0f);
    
        // Typische Werte für Vergleich
        printf("\nTypical values for comparison:\n");
        printf("- L1 Cache: 1-3 cycles\n");
        printf("- L2 Cache: 5-12 cycles\n");
        printf("- Main Memory: 50-200+ cycles\n");
    } else {
        printf("\n⚠️  WARNING: No valid load measurements obtained\n");
        printf("Possible reasons:\n");
        printf("1. Memory access protection\n");
        printf("2. Stack alignment issues\n");
        printf("3. Cache configuration differences\n");
        printf("\nFor BA thesis: Focus on ALU results which are reliable.\n");
    }
}
// ===== HAUPTPROGRAMM =====

void app_main(void) {
    printf("\nStarting ESP32-C6 Performance Analysis for Bachelor Thesis\n");
    printf("===========================================================\n");
    
    // Initialisierung
    vTaskDelay(pdMS_TO_TICKS(500));
    init_performance_counters();

    
    // Führe den sicheren ALU-Test durch
    run_simple_alu_test();
    
    // Optional: Versuche Load-Test separat
    run_load_test_separately();
    
    // Cache-Effekt Analyse
    printf("\n=== CACHE EFFECT DEMONSTRATION ===\n");
    printf("Running 10 consecutive ADD latency measurements:\n");
    
    for (int i = 0; i < 10; i++) {
        uint32_t cycles = measure_latency_chain();
        printf("  Measurement %2d: %" PRIu32 " cycles (%.1f/ADD)\n", 
               i + 1, cycles, cycles / 10.0f);
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    
    printf("\n=== ANALYSIS COMPLETE ===\n");
}