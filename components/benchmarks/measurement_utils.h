#ifndef MEASUREMENT_UTILS_H
#define MEASUREMENT_UTILS_H

#include <stdint.h>

// Zeitmessung
uint64_t get_time_us(void);
uint32_t get_cycle_count(void);
void precise_delay_cycles(uint32_t cycles);

// GPIO Utilities
void setup_gpio_output(int gpio_num);
void toggle_gpio_fast(int gpio_num);

// Datenausgabe
void print_results(const char* test_name, uint64_t time_us, int iterations);
void print_statistics(uint64_t min, uint64_t max, uint64_t avg, uint64_t total);

// Interrupt Utilities
void setup_gpio_interrupt(int gpio_num, void* handler);

#endif