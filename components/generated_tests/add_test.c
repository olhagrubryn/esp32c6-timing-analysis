#include <stdint.h>
#include <stdio.h>
#include <inttypes.h>
#include "generated_tests.h"

uint32_t test_add(void) {
    uint32_t start, end;
    uint32_t a = 1, b = 2, c = 0;
    
    // Performance Counter lesen (Start)
    __asm__ __volatile__("fence.i");
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    // 1000x ADD Operationen
    for (int i = 0; i < 1000; i++) {
        __asm__ __volatile__("add %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
    }
    
    // Performance Counter lesen (Ende)
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    __asm__ __volatile__("fence.i");
    
    uint32_t total_cycles = end - start;
    printf("ADD: %" PRIu32 " cycles total, %.2f cycles/instruction\n", 
           total_cycles, total_cycles / 1000.0);
    
    return total_cycles;
}