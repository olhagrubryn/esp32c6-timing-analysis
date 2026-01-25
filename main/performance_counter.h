#ifndef PERFORMANCE_COUNTER_H
#define PERFORMANCE_COUNTER_H

#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"
#include "esp_attr.h"

void init_performance_counters(void);

// Latenz-Funktionen (aus latency_measurements.c)
void run_complete_latency_analysis(void);
uint32_t measure_dependency_chain(void);
uint32_t measure_reg_to_reg_latency(void);
uint32_t measure_move_latency(void);
uint32_t measure_load_latency_l1(void);
uint32_t measure_load_use_chain(void);
uint32_t measure_branch_decision_latency(void);
uint32_t measure_store_forwarding_latency(void);
uint32_t measure_div_latency_fast(void);
uint32_t measure_div_latency_slow(void);

// Throughput-Funktionen (aus throughput_measurements.c)
IRAM_ATTR uint32_t measure_throughput_chain(void);
IRAM_ATTR uint32_t measure_mixed_alu_ops(void);
IRAM_ATTR uint32_t measure_branch_penalty(void);

#endif