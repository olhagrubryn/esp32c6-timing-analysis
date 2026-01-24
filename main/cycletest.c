#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "performance_counter.h"

// Function declarations from both files
uint32_t measure_complex_dependencies(void);
uint32_t measure_load_latency_stack(void);
uint32_t measure_mixed_alu_ops(void);
uint32_t measure_branch_penalty(void);

void run_simple_alu_test(void) {
    printf("\n=== ESP32-C6 ALU Performance Test ===\n");
    
    // Cache Warmup
    printf("Performing ALU cache warmup...\n");
    for (int i = 0; i < 5; i++) {
        measure_latency_chain();
        measure_throughput_chain();
        measure_complex_dependencies();
    }
    
    // Mehrere Durchläufe
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
    
    printf("\nPer Operation Analysis:\n");
    printf("  ADD Latency:          %.2f cycles/op\n", avg_latency / 10.0f);
    printf("  ADD Throughput:       %.2f cycles/op\n", avg_throughput / 10.0f);
    printf("  Latency/Throughput:   %.2f (ideal > 1.0)\n", avg_latency / avg_throughput);
}

void run_load_test_separately(void) {
    printf("\n=== Optional: Load Latency Test ===\n");
    
    const int NUM_MEASUREMENTS = 5;
    uint32_t load_sum = 0;
    int successful_measurements = 0;
    
    for (int i = 0; i < NUM_MEASUREMENTS; i++) {
        printf("\nLoad test measurement %d/%d: ", i + 1, NUM_MEASUREMENTS);
        
        uint32_t load_result = measure_load_latency_stack();
        
        if (load_result > 0 && load_result < 10000) {
            printf("%" PRIu32 " cycles\n", load_result);
            load_sum += load_result;
            successful_measurements++;
        } else {
            printf("failed/invalid\n");
        }
        
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    
    if (successful_measurements > 0) {
        uint32_t avg_load = load_sum / successful_measurements;
        printf("\nAverage load latency: %.2f cycles/load\n", avg_load / 10.0f);
    }
}

void app_main(void) {
    printf("\nStarting ESP32-C6 Performance Analysis\n");
    printf("======================================\n");
    
    vTaskDelay(pdMS_TO_TICKS(500));
    init_performance_counters();

    // Führe den ALU-Test durch
    run_simple_alu_test();
    
    // Optional: Load-Test
    run_load_test_separately();
    
    printf("\n=== ANALYSIS COMPLETE ===\n");
}