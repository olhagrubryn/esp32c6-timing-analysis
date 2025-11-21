#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_cpu.h"

void app_main(void)
{
    esp_cpu_cycle_count_t start = esp_cpu_get_cycle_count();
    
    // Kritischer Code
    asm volatile (
        "li t0, 100\n"
        "1:\n"
        "addi t0, t0, -1\n"
        "bnez t0, 1b\n"
        ::: "t0"
    );
    
    esp_cpu_cycle_count_t end = esp_cpu_get_cycle_count();
    esp_cpu_cycle_count_t cycles = end - start;
    
    printf("Verbrauchte Zyklen: %lu\n", cycles);
}