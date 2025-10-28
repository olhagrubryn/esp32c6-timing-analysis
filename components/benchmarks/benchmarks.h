#ifndef BENCHMARKS_H
#define BENCHMARKS_H

#include <stdint.h>

// Benchmark Funktionen
void run_micro_benchmarks(void);
void run_interrupt_benchmarks(void);
void run_power_benchmarks(void);
void run_memory_benchmarks(void);
void run_all_benchmarks(void);

// Hilfsfunktionen
void print_main_menu(void);
int get_user_choice(void);
void execute_benchmark(int choice);

#endif