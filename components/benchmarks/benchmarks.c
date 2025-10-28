#include "benchmarks.h"
#include "measurement_utils.h"
#include <stdio.h>

void print_main_menu(void) {
    printf("\n BENCHMARK MENU:\n");
    printf("1 - Micro Benchmarks (CPU Instructions)\n");
    printf("2 - Interrupt Latency Benchmarks\n");
    printf("3 - Power Mode Transition Benchmarks\n");
    printf("4 - Memory Access Benchmarks\n");
    printf("5 - Run ALL Benchmarks\n");
    printf("6 - Custom Experiment\n");
    printf("0 - System Info\n");
    printf("🎮 Choice: ");
}

void run_all_benchmarks(void) {
    printf("\n RUNNING COMPLETE BENCHMARK SUITE...\n");
    run_micro_benchmarks();
    run_interrupt_benchmarks();
    run_power_benchmarks();
    run_memory_benchmarks();
    printf(" ALL BENCHMARKS COMPLETED!\n");
}

