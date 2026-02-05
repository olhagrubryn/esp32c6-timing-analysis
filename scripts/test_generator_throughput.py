#!/usr/bin/env python3
# esp32c6_port_usage_generator.py

import os

# ============================================================================
# 1. GENERATOR CLASSES
# ============================================================================

class PortUsageGenerator:
    """Base class for port usage test generation - Updated for ESP32-C6 (RISC-V)."""
    
    @staticmethod
    def generate_alu_instruction_pairs():
        """ALU Instruction Pairs for Port Usage Tests."""
        test_groups = [
            {
                "name": "ADD_ADD",
                "instructions": [
                    ("add", "t0, t1, t2"),
                    ("add", "t3, t4, t5"),
                ],
                "iterations": 2000,
                "description": "ADD + ADD"
            },
            {
                "name": "ADD_SUB",
                "instructions": [
                    ("add", "t0, t1, t2"),
                    ("sub", "t3, t4, t5"),
                ],
                "iterations": 2000,
                "description": "ADD + SUB"
            },
            {
                "name": "AND_OR",
                "instructions": [
                    ("and", "t0, t1, t2"),
                    ("or",  "t3, t4, t5"),
                ],
                "iterations": 2000,
                "description": "AND + OR"
            },
            {
                "name": "XOR_SLL",
                "instructions": [
                    ("xor", "t0, t1, t2"),
                    ("sll", "t3, t4, t5"),
                ],
                "iterations": 2000,
                "description": "XOR + Shift"
            },
        ]
        return test_groups
    
    @staticmethod
    def generate_memory_alu_pairs():
        """Memory + ALU Instruction Pairs."""
        test_groups = [
            {
                "name": "LW_ADD",
                "instructions": [
                    ("lw",  "t0, 0(t1)"),
                    ("add", "t3, t4, t5"),
                ],
                "iterations": 1500,
                "description": "Load + ADD "
            },
            {
                "name": "SW_SUB",
                "instructions": [
                    ("sw",  "t0, 0(t1)"),
                    ("sub", "t3, t4, t5"),
                ],
                "iterations": 1500,
                "description": "Store + SUB"
            },
            {
                "name": "LW_LW",
                "instructions": [
                    ("lw", "t0, 0(t1)"),
                    ("lw", "t3, 4(t4)"),
                ],
                "iterations": 1500,
                "description": "Load + Load "
            },
            {
                "name": "SW_SW",
                "instructions": [
                    ("sw", "t0, 0(t1)"),
                    ("sw", "t3, 4(t4)"),
                ],
                "iterations": 1500,
                "description": "Store + Store"
            },
        ]
        return test_groups
    
    @staticmethod
    def generate_mul_div_pairs():
        """Multiplication/Division Instruction Pairs."""
        test_groups = [
            {
                "name": "MUL_ADD",
                "instructions": [
                    ("mul", "t0, t1, t2"),
                    ("add", "t3, t4, t5"),
                ],
                "iterations": 1000,
                "description": "Multiply + ADD "
            },
            {
                "name": "DIV_SUB",
                "instructions": [
                    ("div", "t0, t1, t2"),
                    ("sub", "t3, t4, t5"),
                ],
                "iterations": 500,
                "description": "Divide + SUB "
            },
            {
                "name": "MUL_MUL",
                "instructions": [
                    ("mul", "t0, t1, t2"),
                    ("mul", "t3, t4, t5"),
                ],
                "iterations": 800,
                "description": "Multiply + Multiply "
            },
        ]
        return test_groups
    
    @staticmethod
    def generate_control_pairs():
        """Control/Flow Instruction Pairs."""
        test_groups = [
            {
                "name": "NOP_NOP",
                "instructions": [
                    ("nop", ""),
                    ("nop", ""),
                ],
                "iterations": 3000,
                "description": "NOP + NOP "
            },
            {
                "name": "ADDI_ADDI",
                "instructions": [
                    ("addi", "t0, t1, 1"),
                    ("addi", "t3, t4, 2"),
                ],
                "iterations": 2000,
                "description": "ADDI + ADDI "
            },
            {
                "name": "LI_LI",
                "instructions": [
                    ("li", "t0, 0x1234"),
                    ("li", "t3, 0x5678"),
                ],
                "iterations": 2000,
                "description": "Load Im + Load Im"
            },
        ]
        return test_groups
    
    @staticmethod
    def generate_mixed_pairs():
        """Mixed Instruction Type Pairs."""
        test_groups = [
            {
                "name": "LW_MUL",
                "instructions": [
                    ("lw",  "t0, 0(t1)"),
                    ("mul", "t3, t4, t5"),
                ],
                "iterations": 1200,
                "description": "Load + Multiply "
            },
            {
                "name": "SW_DIV",
                "instructions": [
                    ("sw",  "t0, 0(t1)"),
                    ("div", "t3, t4, t5"),
                ],
                "iterations": 800,
                "description": "Store + Divide "
            },
            {
                "name": "ADD_SW",
                "instructions": [
                    ("add", "t0, t1, t2"),
                    ("sw",  "t3, 0(t4)"),
                ],
                "iterations": 1500,
                "description": "ADD + Store "
            },
            {
                "name": "MUL_LW",
                "instructions": [
                    ("mul", "t0, t1, t2"),
                    ("lw",  "t3, 0(t4)"),
                ],
                "iterations": 1200,
                "description": "Multiply + Load "
            },
        ]
        return test_groups

# ============================================================================
# 2. TEMPLATES
# ============================================================================
TEST_FUNCTION_TEMPLATE = """float {test_name}(void) {{
    float total_cycles = 0;
    
    // Sicherer Puffer im RAM
    static uint32_t safe_buffer[32] __attribute__((aligned(32)));
    uint32_t *ptr = safe_buffer;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            "mv t1, %[mem_ptr]\\n"   // Lade Basisadresse in t1
            "mv t4, %[mem_ptr]\\n"   // Lade Basisadresse in t4
            "fence\\n"               
            "csrr %[t_start], 0x7E2\\n" // Read start cycle
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"   // Read end cycle
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr)
            : "t0", "t1", "t2", "t3", "t4", "t5", "memory" 
        );
        total_cycles += (float)(t_end - t_start);
    }}
    
    portEXIT_CRITICAL(&test_mutex);
    return total_cycles;
}}
"""

HEADER_TEMPLATE = """#ifndef ESP32C6_PORT_USAGE_TESTS_H
#define ESP32C6_PORT_USAGE_TESTS_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Initialization
void init_performance_counters(void);

// Test function declarations
{function_declarations}

// Test runner
void run_all_port_usage_tests(void);
void print_port_csv_results(void);
void print_port_analysis(void);

#endif // ESP32C6_PORT_USAGE_TESTS_H
"""

MAIN_TEMPLATE = """#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_port_usage_tests.h"

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
}} port_test_t;

static const port_test_t all_tests[] = {{
{test_definitions}
}};

#define NUM_TESTS (sizeof(all_tests) / sizeof(all_tests[0]))

void run_all_port_usage_tests(void) {{
    printf("\\n================================================\\n");
    printf("ESP32-C6 PORT USAGE TESTS\\n");
    printf("================================================\\n\\n");
    
    init_performance_counters();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    printf("%-15s %-25s %-12s %-8s %-10s\\n", 
           "Test", "Description", "Cycles", "CPI", "Throughput");
    printf("%-15s %-25s %-12s %-8s %-10s\\n",
           "----", "-----------", "------", "---", "---------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const port_test_t* test = &all_tests[i];
        
        // Multiple runs for accuracy
        float min_cycles = 1000000.0f;
        for (int run = 0; run < 5; run++) {{
            float cycles = test->function();
            if (cycles < min_cycles) min_cycles = cycles;
            vTaskDelay(pdMS_TO_TICKS(10));
        }}
        
        float cpi = min_cycles / (float)(test->instruction_count * test->iterations);
        float throughput = 1.0 / cpi;
        
        printf("%-15s %-25s %-12.2f %-8.3f %-10.3f\\n",
               test->name, test->description, min_cycles, cpi, throughput);
        
        vTaskDelay(pdMS_TO_TICKS(30));
    }}
}}

void print_port_csv_results(void) {{
    FILE* csv_file = fopen("/sd/port_usage_results.csv", "w");
    if (csv_file == NULL) {{
        printf("Error opening CSV file!\\n");
        return;
    }}
    
    fprintf(csv_file, "Test Name,Category,Cycles,Iterations,Instruction Count,CPI,Throughput,Description\\n");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const port_test_t* test = &all_tests[i];
        
        float cycles = test->function();
        float cpi = cycles / (float)(test->instruction_count * test->iterations);
        float throughput = 1.0 / cpi;
        
        fprintf(csv_file, "%s,%s,%.2f,%" PRIu32 ",%" PRIu32 ",%.3f,%.3f,%s\\n",
                test->name, test->category, cycles, test->iterations,
                test->instruction_count, cpi, throughput, test->description);
        
        vTaskDelay(pdMS_TO_TICKS(5));
    }}
    
    fclose(csv_file);
    printf("\\nCSV results saved to /sd/port_usage_results.csv\\n");
}}

void print_port_analysis(void) {{
    printf("\\n================================================\\n");
    printf("PORT USAGE ANALYSIS\\n");
    printf("================================================\\n\\n");
    
    // Group by category
    const char* categories[] = {{"ALU", "MEM_ALU", "MUL_DIV", "CONTROL", "MIXED"}};
    const char* cat_names[] = {{"ALU Pairs", "Memory+ALU Pairs", 
                               "Mul/Div Pairs", "Control Pairs", "Mixed Pairs"}};
    
    for (int cat_idx = 0; cat_idx < 5; cat_idx++) {{
        printf("\\n=== %s ===\\n", cat_names[cat_idx]);
        
        float total_throughput = 0;
        int count = 0;
        
        for (int i = 0; i < NUM_TESTS; i++) {{
            if (strcmp(all_tests[i].category, categories[cat_idx]) == 0) {{
                float cycles = all_tests[i].function();
                float cpi = cycles / (float)(all_tests[i].instruction_count * all_tests[i].iterations);
                float throughput = 1.0 / cpi;
                
                printf("  %-15s: Throughput = %.3f IPC", all_tests[i].name, throughput);
                
                // Port conflict detection
                if (throughput > 1.8) {{
                    printf(" (likely different ports)\\n");
                }} else if (throughput > 1.3) {{
                    printf(" (partial port sharing)\\n");
                }} else {{
                    printf(" (port conflict)\\n");
                }}
                
                total_throughput += throughput;
                count++;
            }}
        }}
        
        if (count > 0) {{
            printf("  Average throughput: %.3f IPC\\n", total_throughput / count);
        }}
    }}
}}
"""

def generate_complete_port_usage_test_suite(output_dir="."):
    
    generator = PortUsageGenerator()
    
    # Collect all tests
    all_tests = []
    
    # ALU Pairs
    alu_tests = generator.generate_alu_instruction_pairs()
    for test in alu_tests:
        test["category"] = "ALU"
        test["instruction_count"] = 2  # Two instructions per pair
        all_tests.append(test)
    
    # Memory+ALU Pairs
    mem_tests = generator.generate_memory_alu_pairs()
    for test in mem_tests:
        test["category"] = "MEM_ALU"
        test["instruction_count"] = 2
        all_tests.append(test)
    
    # Mul/Div Pairs
    mul_tests = generator.generate_mul_div_pairs()
    for test in mul_tests:
        test["category"] = "MUL_DIV"
        test["instruction_count"] = 2
        all_tests.append(test)
    
    # Control Pairs
    ctrl_tests = generator.generate_control_pairs()
    for test in ctrl_tests:
        test["category"] = "CONTROL"
        test["instruction_count"] = 2
        all_tests.append(test)
    
    # Mixed Pairs
    mixed_tests = generator.generate_mixed_pairs()
    for test in mixed_tests:
        test["category"] = "MIXED"
        test["instruction_count"] = 2
        all_tests.append(test)
    
    # ============================================================================
    # CREATE OUTPUT DIRECTORY - MODIFIED
    # ============================================================================
    
    # Nur main-Verzeichnis erstellen (kein esp32c6_port_usage)
    os.makedirs("main", exist_ok=True)
    
    # ============================================================================
    # GENERATE HEADER FILE
    # ============================================================================
    
    function_decls = []
    for test in all_tests:
        func_name = f"port_test_{test['name'].lower()}"
        function_decls.append(f"float {func_name}(void);")
    
    header_content = HEADER_TEMPLATE.format(
        function_declarations="\n".join(function_decls)
    )
    
    with open("main/esp32c6_port_usage_tests.h", "w") as f:
        f.write(header_content)
    
    # ============================================================================
    # GENERATE TEST FUNCTIONS
    # ============================================================================
    
    test_functions = []
    test_definitions = []

    for idx, test in enumerate(all_tests):
        func_name = f"port_test_{test['name'].lower()}"
        
        instruction_lines = []
        
        # Create instruction block with register rotation
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
    
    with open("main/esp32c6_port_usage_tests.c", "w") as f:
        f.write(main_content)
    
    # ============================================================================
    # GENERATE MAIN.C
    # ============================================================================
    
    example_main = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_port_usage_tests.h"

void app_main(void) {
    printf("\\nESP32-C6 Port Usage Measurement Suite\\n");
    printf("=======================================\\n\\n");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // Run all tests with analysis
    run_all_port_usage_tests();
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Print detailed analysis
    print_port_analysis();
    
    // Uncomment to save CSV (requires SD card)
    // print_port_csv_results();
    
    printf("\\n=== All port usage tests completed ===\\n");
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
"""
    
    with open("main/main.c", "w") as f:
        f.write(example_main)
    
    # ============================================================================
    # GENERATE CMakeLists.txt
    # ============================================================================
    
    main_cmake = """idf_component_register(SRCS "main.c"
                              "esp32c6_port_usage_tests.c"
                       INCLUDE_DIRS "."
                       REQUIRES freertos)
"""
    
    with open("main/CMakeLists.txt", "w") as f:
        f.write(main_cmake)
    
    # KEIN SDKCONFIG MEHR ERSTELLEN
    # print(f"  Complete port usage test suite generated in {output_dir}/")
    print(f"  Complete port usage test suite generated in current directory")
    
    print(f"\n Test Statistics:")
    print(f"   - Total number of tests: {len(all_tests)}")
    
    categories = {}
    for test in all_tests:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        cat_name = {
            "ALU": "ALU Pairs",
            "MEM_ALU": "Memory+ALU Pairs",
            "MUL_DIV": "Mul/Div Pairs",
            "CONTROL": "Control Pairs",
            "MIXED": "Mixed Pairs"
        }.get(cat, cat)
        print(f"   - {cat_name}: {count} Tests")
    
    total_instructions = sum(t["instruction_count"] * t["iterations"] for t in all_tests)
    print(f"   - Total instruction pairs per test run: {total_instructions}")
    
    print(f"\n Generated files:")
    print(f"   - main/esp32c6_port_usage_tests.h")
    print(f"   - main/esp32c6_port_usage_tests.c")
    print(f"   - main/main.c")
    print(f"   - main/CMakeLists.txt")
    
    # SDKCONFIG ENTFERNEN AUS DER LISTE
    print(f"\n Build instructions:")
    print(f"   1. cd .  # (current directory)")
    print(f"   2. idf.py set-target esp32c6")
    print(f"   3. idf.py build")
    print(f"   4. idf.py flash monitor")
    
    return all_tests

# ============================================================================
# 4. MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("ESP32-C6 Port Usage Test Generator")
    print("=" * 60)
    
    output_directory = "."  # Auf aktuelles Verzeichnis ändern
    tests = generate_complete_port_usage_test_suite(output_directory)
    
    print("\n" + "=" * 60)
    print(f" Done! Test suite created in current directory.")
    
    print("\n Overview of generated categories:")
    categories = {}
    for test in tests:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        print(f"   - {cat}: {count} tests")