#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "performance_counter.h"

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

// Performance Counter Initialisierung
void init_performance_counters(void) {
    __asm__ __volatile__ ("li t0, 1\n csrw 0x7E0, t0\n csrw 0x7E1, t0\n" ::: "t0");
}

// 1. LATENZ-KETTE (abhängige ADDs)
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

// A. Komplexe Abhängigkeiten
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

// Load Latency Stack
uint32_t measure_load_latency_stack(void) {
    uint32_t start, end;
    volatile uint32_t stack_value __attribute__((aligned(4))) = 0xCAFEBABE;
    uint32_t val;
    
    (void)stack_value; // Warnung vermeiden
    
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

// Für Register → Register Latenz
IRAM_ATTR uint32_t measure_add_latency(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 100\n"
        "add %1, %1, %1\n"   // a ← a + a (echte Abhängigkeit)
        ".endr\n"
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) / 100;
}

// Move Elimination testen
IRAM_ATTR uint32_t test_move_elimination(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    register uint32_t b __asm__("t2") = 0;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 100\n"
        "add %2, %1, zero\n"  // MOV mit ADD (immer 1 Zyklus)
        ".endr\n"
        "csrr %3, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 100;
}

// Load/Store Latenz mit Abhängigkeiten
IRAM_ATTR uint32_t measure_load_latency_dependent(void) {
    uint32_t start, end;
    volatile uint32_t* ptr = (volatile uint32_t*)&ptr; // self-referential
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 50\n"
        "lw t4, 0(%2)\n"      // Load address from memory
        "mv %2, t4\n"         // Use loaded address for next load
        ".endr\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(ptr)
        : 
        : "t4", "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 50;
}

// Bypass-Delay testen
IRAM_ATTR uint32_t test_bypass_delay(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "addi %1, %1, 1\n"
        "addi %1, %1, 1\n"
        "addi %1, %1, 1\n"
        "addi %1, %1, 1\n"
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 4;
}

// Zero-Idioms analysieren
IRAM_ATTR uint32_t measure_xor_same_reg(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 100\n"
        "xor %1, %1, %1\n"   // XOR mit gleichem Register
        ".endr\n"
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) / 100;
}

IRAM_ATTR uint32_t measure_chain_latency_simple(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    register uint32_t b __asm__("t2") = 2;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 100\n"
        "add %1, %1, %2\n"   // ADD mit unterschiedlichen Registern
        ".endr\n"
        "csrr %3, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) / 100;
}

void test_zero_idioms(void) {
    printf("\n=== Zero Idioms Analysis ===\n");
    
    uint32_t xor_time = measure_xor_same_reg();
    uint32_t add_time = measure_chain_latency_simple();
    
    printf("XOR same reg: %.2f cycles/op\n", xor_time / 100.0f);
    printf("ADD diff reg: %.2f cycles/op (Baseline)\n", add_time / 100.0f);
    
    if (xor_time < add_time / 2) {
        printf("→ Zero-idiom optimization detected!\n");
    } else {
        printf("→ No zero-idiom optimization\n");
    }
}