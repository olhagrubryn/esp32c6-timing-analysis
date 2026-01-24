#ifndef PERFORMANCE_COUNTER_H
#define PERFORMANCE_COUNTER_H

#include <inttypes.h>
#include "freertos/FreeRTOS.h"

void init_performance_counters(void);
uint32_t measure_latency_chain(void);
uint32_t measure_throughput_chain(void);

#endif