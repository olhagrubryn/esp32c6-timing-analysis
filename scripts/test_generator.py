#!/usr/bin/env python3
# esp32c6_latency_test_generator_final.py - Fixed version with correct assembler

import os
import shutil

# ============================================================================
# 1. GENERATOR CLASSES
# ============================================================================

class LatencyTestGenerator:
    """Base class for latency test generation."""
    
    @staticmethod
    def generate_register_to_register_tests():
        """Register-to-Register Latency Tests."""
        test_groups = [
            {
                "name": "MOV_same_reg",
                "instructions": [
                    ("add", "a2, a3, a4"),
                    ("sub", "a3, a4, a5"),
                    ("xor", "a4, a5, a6"),
                    ("or",  "a5, a6, a2"),
                ],
                "iterations": 1000,
                "description": "ALU operations between different registers"
            },
            {
                "name": "MOV_dependency_chain",
                "instructions": [
                    ("add", "a2, a3, a4"),
                    ("add", "a3, a2, a5"),
                    ("add", "a4, a3, a6"),
                    ("add", "a5, a4, a2"),
                ],
                "iterations": 1000,
                "description": "Dependency chain with ADD"
            },
            {
                "name": "ALU_reg_shuffle",
                "instructions": [
                    ("xor", "a2, a3, a4"),
                    ("or",  "a3, a2, a5"),
                    ("and", "a4, a3, a6"),
                    ("sub", "a5, a4, a2"),
                ],
                "iterations": 1000,
                "description": "ALU operations with register shuffling"
            }
        ]
        
        return test_groups
    
    @staticmethod
    def generate_memory_to_register_tests():
        """Memory-to-Register Latency Tests."""
        test_groups = [
            {
                "name": "LDR_simple",
                "instructions": [
                    ("lw",   "a2, 0(a3)"),
                    ("lw",   "a3, 4(a4)"),
                    ("addi", "a2, a2, 1"),
                    ("lw",   "a4, 8(a5)"),
                ],
                "iterations": 500,
                "description": "Simple load operations"
            },
            {
                "name": "LDR_dependency_chain",
                "instructions": [
                    ("lw",   "a2, 0(a3)"),
                    ("xor",  "a4, a2, a5"),
                    ("lw",   "a3, 4(a4)"),
                    ("add",  "a5, a3, a6"),
                ],
                "iterations": 500,
                "description": "Load with dependency chain"
            },
            {
                "name": "LDR_post_index",
                "instructions": [
                    ("lw",   "a2, 0(a3)"),
                    ("addi", "a3, a3, 4"),
                    ("lw",   "a4, 0(a3)"),
                    ("addi", "a3, a3, 4"),
                ],
                "iterations": 500,
                "description": "Load with post-index addressing"
            }
        ]
        
        return test_groups
    
    @staticmethod
    def generate_status_flags_tests():
        """Status-Flags-to-Register Latency Tests."""
        test_groups = [
            {
                "name": "CMP_branch",
                "instructions": [
                    ("sub",  "a2, a3, a4"),
                    ("addi", "a5, a5, 1"),
                    ("addi", "a6, a6, 1"),
                    ("addi", "a2, a2, 1"),
                ],
                "iterations": 1000,
                "description": "Compare operations"
            },
            {
                "name": "SLT_set",
                "instructions": [
                    ("slt",  "a2, a3, a4"),
                    ("add",  "a5, a2, a6"),
                    ("sltu", "a3, a5, a2"),
                    ("or",   "a4, a3, a5"),
                ],
                "iterations": 1000,
                "description": "Set-on-compare instructions"
            },
            {
                "name": "TEST_flags",
                "instructions": [
                    ("and",  "a2, a3, a4"),
                    ("or",   "a5, a5, a2"),
                    ("addi", "a6, a6, 1"),
                    ("xor",  "a2, a2, a3"),
                ],
                "iterations": 1000,
                "description": "Test operations affecting flags"
            }
        ]
        
        return test_groups
    
    @staticmethod
    def generate_register_to_memory_tests():
        """Register-to-Memory Latency Tests (Store + Load)."""
        test_groups = [
            {
                "name": "STR_LDR_pair",
                "instructions": [
                    ("sw",   "a2, 0(a3)"),
                    ("lw",   "a4, 0(a3)"),
                    ("addi", "a4, a4, 1"),
                    ("sw",   "a4, 4(a3)"),
                ],
                "iterations": 500,
                "description": "Store followed by dependent load"
            },
            {
                "name": "STR_chain",
                "instructions": [
                    ("sw",   "a2, 0(a3)"),
                    ("addi", "a3, a3, 4"),
                    ("sw",   "a4, 0(a3)"),
                    ("lw",   "a5, -4(a3)"),
                ],
                "iterations": 500,
                "description": "Store chain with address progression"
            },
            {
                "name": "MEM_fence",
                "instructions": [
                    ("sw",   "a2, 0(a3)"),
                    ("fence", "iorw, iorw"),
                    ("lw",   "a4, 0(a3)"),
                    ("add",  "a5, a4, a6"),
                ],
                "iterations": 500,
                "description": "Store with memory fence and load"
            }
        ]
        
        return test_groups
    
    @staticmethod
    def generate_division_tests():
        """Division Instruction Latency Tests."""
        test_groups = [
            {
                "name": "DIV_fast",
                "instructions": [
                    ("div",  "a2, a3, a4"),
                    ("addi", "a5, a2, 0"),
                    ("mul",  "a6, a5, a3"),
                    ("addi", "a3, a3, 1"),
                ],
                "iterations": 200,
                "description": "Division with simple values (fast path)"
            },
            {
                "name": "DIV_slow",
                "instructions": [
                    ("div",  "a2, a3, a4"),
                    ("rem",  "a5, a3, a4"),
                    ("add",  "a6, a2, a5"),
                    ("addi", "a4, a4, -1"),
                ],
                "iterations": 200,
                "description": "Division with complex values (slow path)"
            },
            {
                "name": "DIVU_unsigned",
                "instructions": [
                    ("divu", "a2, a3, a4"),
                    ("remu", "a5, a3, a4"),
                    ("mul",  "a6, a2, a4"),
                    ("add",  "a2, a6, a5"),
                ],
                "iterations": 200,
                "description": "Unsigned division and remainder"
            }
        ]
        
        return test_groups

# ============================================================================
# 2. TEMPLATES  ASSEMBLER
# ============================================================================

TEST_FUNCTION_TEMPLATE = """float {test_name}(void) {{
    float start, end;
    float total_cycles = 0;
    
    // Safe buffer in RAM (16 words) to avoid access faults
    static uint32_t safe_buffer[16] __attribute__((aligned(16)));
    uint32_t *ptr = safe_buffer;
    
    // Initial values for register tests
    uint32_t r3_val = 0x12345678;
    uint32_t r4_val = 0x87654321;
    uint32_t r5_val = 0xABCDEF01;
    uint32_t r6_val = 0xFEDCBA98;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"   // Load safe RAM address into a3
            "mv a4, %[mem_ptr]\\n"   // Also into a4 (for offsets)
            "mv a5, %[mem_ptr]\\n"   // Also into a5
            "fence\\n"               // Memory Barrier
            "csrr %[t_start], 0x7E2\\n" // Read start cycle
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"   // Read end cycle
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr), "r"(r3_val), "r"(r4_val), "r"(r5_val), "r"(r6_val)
            : "a2", "a3", "a4", "a5", "a6", "memory"
        );
        start = (float)t_start;
        end = (float)t_end;
        total_cycles += (end - start);
    }}
    
    portEXIT_CRITICAL(&test_mutex);
    return total_cycles;
}}
"""

HEADER_TEMPLATE = """#ifndef ESP32C6_LATENCY_TESTS_H
#define ESP32C6_LATENCY_TESTS_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Initialization
void init_performance_counters(void);

// Test function declarations
{function_declarations}

// Test runner
void run_all_latency_tests(void);
void print_csv_results(void);
void print_detailed_results(void);

#endif // ESP32C6_LATENCY_TESTS_H
"""

MAIN_TEMPLATE = """#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

void init_performance_counters(void) {{
    __asm__ __volatile__ (
        "li a2, 1\\n"
        "csrw 0x7E0, a2\\n"   // Enable cycle counter
        "csrw 0x7E1, a2\\n"   // Enable performance counters
        ::: "a2"
    );
}}

{test_functions}

// ============================================================================
// TEST DEFINITIONS AND RUNNER
// ============================================================================

typedef struct {{
    const char* name;
    float (*function)(void);
    uint32_t iterations;
    uint32_t instruction_count;
    const char* description;
    const char* category;
}} latency_test_t;

static const latency_test_t all_tests[] = {{
{test_definitions}
}};

#define NUM_TESTS (sizeof(all_tests) / sizeof(all_tests[0]))

void run_all_latency_tests(void) {{
    printf("\\n================================================\\n");
    printf("ESP32-C6 INSTRUCTION LATENCY TESTS\\n");
    printf("================================================\\n\\n");
    
    init_performance_counters();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    printf("%-25s %-12s %-8s %-10s %s\\n", 
           "Test", "Cycles", "CPI", "Latency", "Description");
    printf("%-25s %-12s %-8s %-10s %s\\n",
           "----", "------", "---", "-------", "-----------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const latency_test_t* test = &all_tests[i];
        
        // Multiple runs for statistical accuracy
        float min_cycles = 1000000.0f;
        for (int run = 0; run < 5; run++) {{
            float cycles = test->function();
            if (cycles < min_cycles) min_cycles = cycles;
            vTaskDelay(pdMS_TO_TICKS(20));
        }}
        
        float cpi = min_cycles / (float)test->instruction_count;
        float latency = cpi / (float)test->iterations;
        
        printf("%-25s %-12.2f %-8.2f %-10.2f %s\\n",
               test->name, min_cycles, cpi, latency, test->description);
        
        vTaskDelay(pdMS_TO_TICKS(50));
    }}
}}

void print_csv_results(void) {{
    FILE* csv_file = fopen("/sd/latency_results.csv", "w");
    if (csv_file == NULL) {{
        printf("Error opening CSV file!\\n");
        return;
    }}
    
    fprintf(csv_file, "Test Name,Category,Cycles,Iterations,CPI,Latency,Description\\n");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const latency_test_t* test = &all_tests[i];
        
        float cycles = test->function();
        float cpi = cycles / (float)test->instruction_count;
        float latency = cycles / (float)test->iterations;
        
        fprintf(csv_file, "%s,%s,%.2f,%" PRIu32 ",%.2f,%.2f,%s\\n",
                test->name, test->category, cycles, test->iterations, 
                cpi, latency, test->description);
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }}
    
    fclose(csv_file);
    printf("\\nCSV results saved to /sd/latency_results.csv\\n");
}}

void print_detailed_results(void) {{
    printf("\\n================================================\\n");
    printf("DETAILED LATENCY ANALYSIS\\n");
    printf("================================================\\n\\n");
    
    // Group by category
    const char* categories[] = {{"REG2REG", "MEM2REG", "FLAGS", "REG2MEM", "DIV"}};
    const char* cat_names[] = {{"Register-to-Register", "Memory-to-Register", 
                               "Status-Flags", "Register-to-Memory", "Division"}};
    
    for (int cat_idx = 0; cat_idx < 5; cat_idx++) {{
        printf("\\n=== %s Latency Tests ===\\n", cat_names[cat_idx]);
        
        for (int i = 0; i < NUM_TESTS; i++) {{
            if (strcmp(all_tests[i].category, categories[cat_idx]) == 0) {{
                float cycles = all_tests[i].function();
                float latency = cycles / (float)all_tests[i].iterations;
                
                printf("  %-20s: %8.2f cycles, latency: %8.2f cycles/iter\\n",
                       all_tests[i].name, cycles, latency);
            }}
        }}
    }}
}}
"""

def generate_complete_latency_test_suite(output_dir="esp32c6_latency_fixed"):
    
    from __main__ import LatencyTestGenerator
    generator = LatencyTestGenerator()
    
    # Collect all tests
    all_tests = []
    
    # Register-to-Register Tests
    reg_tests = generator.generate_register_to_register_tests()
    for test in reg_tests:
        test["category"] = "REG2REG"
        test["instruction_count"] = len(test["instructions"])
        all_tests.append(test)
    
    # Memory-to-Register Tests
    mem_tests = generator.generate_memory_to_register_tests()
    for test in mem_tests:
        test["category"] = "MEM2REG"
        test["instruction_count"] = len(test["instructions"])
        all_tests.append(test)
    
    # Status-Flags Tests
    flag_tests = generator.generate_status_flags_tests()
    for test in flag_tests:
        test["category"] = "FLAGS"
        test["instruction_count"] = len(test["instructions"])
        all_tests.append(test)
    
    # Register-to-Memory Tests
    store_tests = generator.generate_register_to_memory_tests()
    for test in store_tests:
        test["category"] = "REG2MEM"
        test["instruction_count"] = len(test["instructions"])
        all_tests.append(test)
    
    # Division Tests
    div_tests = generator.generate_division_tests()
    for test in div_tests:
        test["category"] = "DIV"
        test["instruction_count"] = len(test["instructions"])
        all_tests.append(test)
    
    # ============================================================================
    # GENERATE HEADER FILE
    # ============================================================================
    
    function_decls = []
    for test in all_tests:
        func_name = f"test_{test['name'].lower()}"
        function_decls.append(f"float {func_name}(void);")
    
    header_content = HEADER_TEMPLATE.format(
        function_declarations="\n".join(function_decls)
    )
    
    with open(f"main/esp32c6_latency_tests.h", "w") as f:
        f.write(header_content)
    
    # ============================================================================
    # GENERATE TEST FUNCTIONS
    # ============================================================================
    
    test_functions = []
    test_definitions = []

    for idx, test in enumerate(all_tests):
        func_name = f"test_{test['name'].lower()}"
        
        instruction_lines = []
        
        if "LDR" in test['name'] or "STR" in test['name']:
            instruction_lines.append('            "addi a3, a3, 0\\n"')

        for instr_name, operands in test["instructions"]:
            instruction_lines.append(f'            "{instr_name} {operands}\\n"')
        
        instruction_block = "\n".join(instruction_lines)
        
        test_func = TEST_FUNCTION_TEMPLATE.format(
            test_name=func_name,
            iterations=test.get("iterations", 1000),
            instruction_block=instruction_block
        )
        test_functions.append(test_func)
        
        test_def = f'    {{"{test["name"]}", {func_name}, {test["iterations"]}, ' \
                   f'{test["instruction_count"]}, "{test["description"]}", "{test["category"]}"}}'
        if idx < len(all_tests) - 1:
            test_def += ","
        test_definitions.append(test_def)
    
    # ============================================================================
    # GENERATE MAIN C FILE
    # ============================================================================
    
    main_content = MAIN_TEMPLATE.format(
        test_functions="\n".join(test_functions),
        test_definitions="\n".join(test_definitions)
    )
    
    with open(f"main/esp32c6_latency_tests.c", "w") as f:
        f.write(main_content)
    
    # ============================================================================
    # GENERATE MAIN.C
    # ============================================================================
    
    example_main = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

void app_main(void) {
    printf("\\nESP32-C6 Instruction Latency Measurement Suite\\n");
    printf("================================================\\n\\n");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // Option 1: Detailed output
    run_all_latency_tests();
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Option 2: CSV output (requires SD Card)
    // print_csv_results();
    
    // Option 3: Detailed analysis
    print_detailed_results();
    
    printf("\\n=== All tests completed ===\\n");
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
"""
    
    with open(f"main/main.c", "w") as f:
        f.write(example_main)
    
    main_cmake = """idf_component_register(SRCS "main.c"
                              "esp32c6_latency_tests.c"
                       INCLUDE_DIRS "."
                       REQUIRES freertos)
"""
    
    with open(f"main/CMakeLists.txt", "w") as f:
        f.write(main_cmake)
    
    print(f"  Complete latency test suite generated in {output_dir}/")
    print(f"\n Test Statistics:")
    print(f"   - Total number of tests: {len(all_tests)}")
    
    categories = {}
    for test in all_tests:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        cat_name = {
            "REG2REG": "Register-to-Register",
            "MEM2REG": "Memory-to-Register",
            "FLAGS": "Status-Flags",
            "REG2MEM": "Register-to-Memory",
            "DIV": "Division"
        }.get(cat, cat)
        print(f"   - {cat_name}: {count} Tests")
    
    total_instructions = sum(t["instruction_count"] * t["iterations"] for t in all_tests)
    print(f"   - Total Instructions per test run: {total_instructions}")
    
    print(f"\n Generated files:")
    print(f"   - main/esp32c6_latency_tests.h")
    print(f"   - main/esp32c6_latency_tests.c")
    print(f"   - main/main.c")
    print(f"   - main/CMakeLists.txt")
    
    print(f"\n Build instructions:")
    print(f"   1. cd {output_dir}")
    print(f"   2. idf.py set-target esp32c6")
    print(f"   3. idf.py build")
    print(f"   4. idf.py flash monitor")
    
    return all_tests

# ============================================================================
# 4. MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("ESP32-C6 Latency Test Generator - Clean Version")
    print("=" * 60)
    
    output_directory = "esp32c6_latency_fixed"
    tests = generate_complete_latency_test_suite(output_directory)
    
    print("\n" + "=" * 60)
    print(f" Done! Test suite created in '{output_directory}'.")
    
    print("\n Overview of generated categories:")
    categories = {}
    for test in tests:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        print(f"   - {cat}: {count} tests")
