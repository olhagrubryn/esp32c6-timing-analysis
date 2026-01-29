#include <stdint.h>
#include <stdio.h>
#include <inttypes.h>
#include "generated_tests.h"

uint32_t test_and(void) {
    uint32_t start, end;
    uint32_t a = 0xF0F0F0F0, b = 0x0F0F0F0F, c = 0;
    
    __asm__ __volatile__("fence.i");
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    for (int i = 0; i < 1000; i++) {
        __asm__ __volatile__("and %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
    }
    
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    __asm__ __volatile__("fence.i");
    
    uint32_t total_cycles = end - start;
    printf("AND: %" PRIu32 " cycles total, %.2f cycles/instruction\n", 
           total_cycles, total_cycles / 1000.0);
    
    return total_cycles;
}