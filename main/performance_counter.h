/**
 * @file performance_counter.h
 * @brief Performance counter measurements for ESP32-C6
 */

#ifndef PERFORMANCE_COUNTER_H
#define PERFORMANCE_COUNTER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Performance counter initialization
void init_performance_counters(void);

// =========== LATENCY MEASUREMENTS (FLOAT) ===========
// Dependency Chains
float measure_dependency_chain(void);

// Register to Register
float measure_reg_to_reg_latency(void);
float measure_move_latency(void);

// Memory to Register
float measure_load_latency_l1(void);
float measure_load_use_chain(void);

// Conditional Branches
float measure_branch_decision_latency(void);

// Register to Memory
float measure_store_forwarding_latency(void);

// Divisions
float measure_div_latency_fast(void);
float measure_div_latency_slow(void);

// Memory Hierarchy
void measure_memory_hierarchy(void);

// =========== THROUGHPUT MEASUREMENTS (UINT32_T) ===========
// These functions are in throughput_measurements.c
// Note: Keep as uint32_t for compatibility
uint32_t measure_throughput_chain(void);
uint32_t measure_mixed_alu_ops(void);
uint32_t measure_branch_penalty(void);

// =========== MAIN ANALYSIS FUNCTION ===========
void run_complete_latency_analysis(void);

#ifdef __cplusplus
}
#endif

#endif // PERFORMANCE_COUNTER_H