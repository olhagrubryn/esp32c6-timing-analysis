#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "main/generated_tests/generated_tests.h"

void run_all_generated_tests(void) {
    printf("\n=== Running Generated Instruction Tests ===\n");
    
    struct Test {
        const char* name;
        uint32_t (*function)(void);
    };
    
    struct Test tests[] = {
        {"ADD", test_add},
        {"SUB", test_sub},
        {"AND", test_and},
    };
    
    const int num_tests = sizeof(tests) / sizeof(tests[0]);
    
    printf("\nInstruction,Total Cycles,Cycles/Instruction\n");
    
    for (int i = 0; i < num_tests; i++) {
        printf("\n[%d/%d] %s...\n", i + 1, num_tests, tests[i].name);
        
        // Mehrere Durchläufe für Genauigkeit
        const int NUM_RUNS = 3;
        uint32_t total_cycles = 0;
        
        for (int run = 0; run < NUM_RUNS; run++) {
            uint32_t cycles = tests[i].function();
            total_cycles += cycles;
            
            printf("  Run %d: %" PRIu32 " cycles\n", run + 1, cycles);
            
            if (run < NUM_RUNS - 1) {
                vTaskDelay(pdMS_TO_TICKS(50));
            }
        }
        
        uint32_t avg_cycles = total_cycles / NUM_RUNS;
        printf("  Average: %" PRIu32 " cycles total, %.2f cycles/instruction\n",
               avg_cycles, avg_cycles / 1000.0);
        
        // CSV Format
        printf("CSV,%s,%" PRIu32 ",%.2f\n", 
               tests[i].name, avg_cycles, avg_cycles / 1000.0);
        
        vTaskDelay(pdMS_TO_TICKS(200));
    }
    
    printf("\n=== Generated Tests Complete ===\n");
}