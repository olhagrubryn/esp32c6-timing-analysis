#include <stdint.h>
#include "generated_tests.h"

uint32_t test_add(void) {
    uint32_t start, end, a = 1, b = 2, c;
    
    __asm__ __volatile__("fence.i");
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    for (int i = 0; i < 1000; i++) {
        __asm__ __volatile__("add %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
    }
    
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    __asm__ __volatile__("fence.i");
    
    return end - start;
}

uint32_t test_sub(void) {
    uint32_t start, end, a = 100, b = 1, c;
    
    __asm__ __volatile__("fence.i");
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    for (int i = 0; i < 1000; i++) {
        __asm__ __volatile__("sub %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
    }
    
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    __asm__ __volatile__("fence.i");
    
    return end - start;
}
