
#include <stdio.h>
#include <inttypes.h>

void measure_and(void) {
    uint32_t start, end;
    register uint32_t a = 0xF0F0, b = 0x0F0F, c;
    
    // Counter start
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    // Test-Block (100 Iterationen)
    for (int i = 0; i < 100; i++) {
        and t3, t1, t2
    }
    
    // Counter stop
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    
    printf("and: %" PRIu32 " cycles\n", end - start);
}

void app_main(void) {
    printf("\nESP32-C6 Benchmarks\n");
    measure_and();
}
