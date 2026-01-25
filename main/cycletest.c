#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "performance_counter.h"
/*
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
    uint32_t add_lat_sum = 0, move_elim_sum = 0, load_dep_sum = 0, bypass_sum = 0;
    
    for (int run = 0; run < NUM_RUNS; run++) {
        printf("\n--- Run %d/%d ---\n", run + 1, NUM_RUNS);
        
        // Bestehende Tests
        uint32_t latency = measure_latency_chain();
        uint32_t throughput = measure_throughput_chain();
        uint32_t complex = measure_complex_dependencies();
        uint32_t mixed = measure_mixed_alu_ops();
        uint32_t branch = measure_branch_penalty();
        
        // Neue Tests
        uint32_t add_lat = measure_add_latency();
        uint32_t move_elim = test_move_elimination();
        uint32_t load_dep = measure_load_latency_dependent();
        uint32_t bypass = test_bypass_delay();
        
        printf("Basic Measurements:\n");
        printf("  ADD Latency (10x):      %" PRIu32 " cycles\n", latency);
        printf("  ADD Throughput (10x):   %" PRIu32 " cycles\n", throughput);
        printf("  ADD Detailed Latency:   %.2f cycles/op\n", add_lat / 1.0f);
        
        printf("Advanced Analysis:\n");
        printf("  Complex Dep. (30x):     %" PRIu32 " cycles\n", complex);
        printf("  Mixed ALU Ops (10x):    %" PRIu32 " cycles\n", mixed);
        printf("  Branch Penalty (10x):   %" PRIu32 " cycles\n", branch);
        printf("  Move Elimination:       %.2f cycles/op\n", move_elim / 1.0f);
        printf("  Load Dep. Latency:      %.2f cycles/op\n", load_dep / 1.0f);
        printf("  Bypass Delay:           %.2f cycles/op\n", bypass / 1.0f);
        
        // Summen
        latency_sum += latency;
        throughput_sum += throughput;
        complex_sum += complex;
        mixed_sum += mixed;
        branch_sum += branch;
        add_lat_sum += add_lat;
        move_elim_sum += move_elim;
        load_dep_sum += load_dep;
        bypass_sum += bypass;
        
        vTaskDelay(pdMS_TO_TICKS(200));
    }
    
    // Durchschnittliche Ergebnisse
    printf("\n=== AVERAGE RESULTS (over %d runs) ===\n", NUM_RUNS);
    
    float avg_latency = latency_sum / (float)NUM_RUNS;
    float avg_throughput = throughput_sum / (float)NUM_RUNS;
    
    printf("\nPer Operation Analysis:\n");
    printf("  ADD Latency (10x):     %.2f cycles/op\n", avg_latency / 10.0f);
    printf("  ADD Throughput (10x):  %.2f cycles/op\n", avg_throughput / 10.0f);
    printf("  ADD Detailed:          %.2f cycles/op\n", add_lat_sum / (float)NUM_RUNS);
    printf("  Move Elimination:      %.2f cycles/op\n", move_elim_sum / (float)NUM_RUNS);
    printf("  Load Dependent:        %.2f cycles/op\n", load_dep_sum / (float)NUM_RUNS);
    printf("  Bypass Delay:          %.2f cycles/op\n", bypass_sum / (float)NUM_RUNS);
    printf("  Latency/Throughput:    %.2f (ideal > 1.0)\n", avg_latency / avg_throughput);
    
    // Zero Idioms Test (einmalig)
    test_zero_idioms();
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
*/
void app_main(void) {
    /*
    printf("\nStarting ESP32-C6 Performance Analysis\n");
    printf("======================================\n");
    
    vTaskDelay(pdMS_TO_TICKS(500));
    init_performance_counters();

    // Führe alle Tests durch
    run_simple_alu_test();
    
    // Optional: Load-Test
    run_load_test_separately();
    
    printf("\n=== ANALYSIS COMPLETE ===\n");
    */
    printf("Starting ESP32-C6 Latency Analysis...\n");
    
    // Initialize
    init_performance_counters();
    
    // Run complete analysis
    run_complete_latency_analysis();
    
    printf("\nDone!\n");
}