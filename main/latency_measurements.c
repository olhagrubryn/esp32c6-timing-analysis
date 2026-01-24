#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "performance_counter.h"

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

// Performance Counter Initialisierung
void init_performance_counters(void) {
    __asm__ __volatile__ ("li t0, 1\n csrw 0x7E0, t0\n csrw 0x7E1, t0\n" ::: "t0");
}

// 1. LATENZ-KETTE (abhängige ADDs) - DAS IST LATENCY!
IRAM_ATTR uint32_t measure_latency_chain(void) {
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

// A. Komplexe Abhängigkeiten (keine Optimierung möglich) - AUCH LATENCY!
IRAM_ATTR uint32_t measure_complex_dependencies(void) {
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

// Load Latency Stack - AUCH LATENCY!
uint32_t measure_load_latency_stack(void) {
    uint32_t start, end;
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