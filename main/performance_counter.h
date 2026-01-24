#ifndef PERFORMANCE_COUNTER_H
#define PERFORMANCE_COUNTER_H

#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"
#include "esp_attr.h"

void init_performance_counters(void);

// Latenz-Funktionen (aus latency_measurements.c)
IRAM_ATTR uint32_t measure_latency_chain(void);
IRAM_ATTR uint32_t measure_complex_dependencies(void);
uint32_t measure_load_latency_stack(void);
IRAM_ATTR uint32_t measure_add_latency(void);
IRAM_ATTR uint32_t test_move_elimination(void);
IRAM_ATTR uint32_t measure_load_latency_dependent(void);
IRAM_ATTR uint32_t test_bypass_delay(void);
IRAM_ATTR uint32_t measure_xor_same_reg(void);
IRAM_ATTR uint32_t measure_chain_latency_simple(void);
void test_zero_idioms(void);

// Throughput-Funktionen (aus throughput_measurements.c)
IRAM_ATTR uint32_t measure_throughput_chain(void);
IRAM_ATTR uint32_t measure_mixed_alu_ops(void);
IRAM_ATTR uint32_t measure_branch_penalty(void);

#endif