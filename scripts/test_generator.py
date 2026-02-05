#!/usr/bin/env python3
# esp32c6_latency_test_generator_final.py - Korrigierte Version mit richtigem Assembler

import os
import shutil

# ============================================================================
# 1. GENERATOR-KLASSEN
# ============================================================================

class LatencyTestGenerator:
    """Basisklasse für Latency-Test-Generierung."""
    
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
# 2. KORRIGIERTE TEMPLATES MIT RICHTIGEM ASSEMBLER
# ============================================================================

# The key fix here is using C string literal concatenation: "line1\n" "line2\n"
# 1. Das korrigierte Template für die Test-Funktionen
TEST_FUNCTION_TEMPLATE = """uint32_t {test_name}(void) {{
    uint32_t start, end;
    uint32_t total_cycles = 0;
    
    // Sicherer Puffer im RAM (16 Words), damit wir keine Access Faults bekommen
    static uint32_t safe_buffer[16] __attribute__((aligned(16)));
    uint32_t *ptr = safe_buffer;
    
    // Initialwerte für Register-Tests
    uint32_t r3_val = 0x12345678;
    uint32_t r4_val = 0x87654321;
    uint32_t r5_val = 0xABCDEF01;
    uint32_t r6_val = 0xFEDCBA98;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"   // Lade die sichere RAM-Adresse in a3
            "mv a4, %[mem_ptr]\\n"   // Auch in a4 (für Offsets)
            "mv a5, %[mem_ptr]\\n"   // Auch in a5
            "fence\\n"               // Memory Barrier
            "csrr %[t_start], 0x7E2\\n" // Start-Zyklus lesen
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"   // End-Zyklus lesen
            "fence\\n"
            : [t_start] "=r"(start), [t_end] "=r"(end)
            : [mem_ptr] "r"(ptr), "r"(r3_val), "r"(r4_val), "r"(r5_val), "r"(r6_val)
            : "a2", "a3", "a4", "a5", "a6", "memory"
        );
        total_cycles += (end - start);
    }}
    
    portEXIT_CRITICAL(&test_mutex);
    return total_cycles / {iterations};
}}
"""

HEADER_TEMPLATE = """#ifndef ESP32C6_LATENCY_TESTS_H
#define ESP32C6_LATENCY_TESTS_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Initialisierung
void init_performance_counters(void);

// Test-Funktionen Deklarationen
{function_declarations}

// Test-Runner
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
// TEST DEFINITIONEN UND RUNNER
// ============================================================================

typedef struct {{
    const char* name;
    uint32_t (*function)(void);
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
        
        // Mehrere Durchläufe für statistische Genauigkeit
        uint32_t min_cycles = UINT32_MAX;
        for (int run = 0; run < 5; run++) {{
            uint32_t cycles = test->function();
            if (cycles < min_cycles) min_cycles = cycles;
            vTaskDelay(pdMS_TO_TICKS(20));
        }}
        
        float cpi = (float)min_cycles / test->instruction_count;
        float latency = (float)min_cycles / test->iterations;
        
        printf("%-25s %-12" PRIu32 " %-8.2f %-10.2f %s\\n",
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
        
        uint32_t cycles = test->function();
        float cpi = (float)cycles / test->instruction_count;
        float latency = (float)cycles / test->iterations;
        
        fprintf(csv_file, "%s,%s,%" PRIu32 ",%" PRIu32 ",%.2f,%.2f,%s\\n",
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
    
    // Gruppiere nach Kategorie
    const char* categories[] = {{"REG2REG", "MEM2REG", "FLAGS", "REG2MEM", "DIV"}};
    const char* cat_names[] = {{"Register-to-Register", "Memory-to-Register", 
                               "Status-Flags", "Register-to-Memory", "Division"}};
    
    for (int cat_idx = 0; cat_idx < 5; cat_idx++) {{
        printf("\\n=== %s Latency Tests ===\\n", cat_names[cat_idx]);
        
        for (int i = 0; i < NUM_TESTS; i++) {{
            if (strcmp(all_tests[i].category, categories[cat_idx]) == 0) {{
                uint32_t cycles = all_tests[i].function();
                float latency = (float)cycles / all_tests[i].iterations;
                
                printf("  %-20s: %6" PRIu32 " cycles, latency: %6.2f cycles/iter\\n",
                       all_tests[i].name, cycles, latency);
            }}
        }}
    }}
}}
"""

# ============================================================================
# 3. KORRIGIERTE GENERATOR-FUNKTION MIT RICHTIGEM ASSEMBLER-FORMAT
# ============================================================================

def generate_complete_latency_test_suite(output_dir="esp32c6_latency_fixed"):
    
    from __main__ import LatencyTestGenerator # Ensure access to your classes
    generator = LatencyTestGenerator()
    
    # Sammle alle Tests
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
    # GENERIERE HEADER DATEI
    # ============================================================================
    
    function_decls = []
    for test in all_tests:
        func_name = f"test_{test['name'].lower()}"
        function_decls.append(f"uint32_t {func_name}(void);")
    
    header_content = HEADER_TEMPLATE.format(
        function_declarations="\n".join(function_decls)
    )
    
    with open(f"main/esp32c6_latency_tests.h", "w") as f:
        f.write(header_content)
    
    # ============================================================================
    # GENERIERE TEST-FUNKTIONEN MIT KORREKTEM ASSEMBLER
    # ============================================================================
    
    test_functions = []
    test_definitions = []

    for idx, test in enumerate(all_tests):
        func_name = f"test_{test['name'].lower()}"
        
        # FIX: Build the instruction block correctly
        # We use C string concatenation: "line1\n" "line2\n"
        instruction_lines = []
        
        # If it's a memory test, add the setup pointer instruction
        if "LDR" in test['name'] or "STR" in test['name']:
            instruction_lines.append('            "addi a3, a3, 0\\n"')

        # Jede Instruktion einzeln formatieren
        for instr_name, operands in test["instructions"]:
            # Wir sorgen dafür, dass wir nur Register nutzen, die wir oben vorbereitet haben
            instruction_lines.append(f'            "{instr_name} {operands}\\n"')
        
        # Join lines with actual newlines for the C file readability
        instruction_block = "\n".join(instruction_lines)
        
        test_func = TEST_FUNCTION_TEMPLATE.format(
            test_name=func_name,
            iterations=test.get("iterations", 1000),
            instruction_block=instruction_block
        )
        test_functions.append(test_func)
        
        # Füge zur Test-Definition hinzu
        test_def = f'    {{"{test["name"]}", {func_name}, {test["iterations"]}, ' \
                   f'{test["instruction_count"]}, "{test["description"]}", "{test["category"]}"}}'
        if idx < len(all_tests) - 1:
            test_def += ","
        test_definitions.append(test_def)
    
    # ============================================================================
    # GENERIERE HAUPT-C-DATEI
    # ============================================================================
    
    main_content = MAIN_TEMPLATE.format(
        test_functions="\n".join(test_functions),
        test_definitions="\n".join(test_definitions)
    )
    
    with open(f"main/esp32c6_latency_tests.c", "w") as f:
        f.write(main_content)
    
    # ============================================================================
    # GENERIERE BEISPIEL MAIN.C
    # ============================================================================
    
    example_main = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

void app_main(void) {
    printf("\\nESP32-C6 Instruction Latency Measurement Suite\\n");
    printf("================================================\\n\\n");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // Option 1: Ausführliche Ausgabe
    run_all_latency_tests();
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Option 2: CSV Ausgabe (benötigt SD Card)
    // print_csv_results();
    
    // Option 3: Detaillierte Analyse
    print_detailed_results();
    
    printf("\\n=== All tests completed ===\\n");
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
"""
    
    with open(f"main/main.c", "w") as f:
        f.write(example_main)
    
    # ============================================================================
    # GENERIERE CMakeLists.txt DATEIEN
    # ============================================================================
    
    # main/CMakeLists.txt
    main_cmake = """idf_component_register(SRCS "main.c"
                              "esp32c6_latency_tests.c"
                       INCLUDE_DIRS "."
                       REQUIRES freertos)
"""
    
    with open(f"main/CMakeLists.txt", "w") as f:
        f.write(main_cmake)
    
    # ============================================================================
    # AUSGABE STATISTIKEN
    # ============================================================================
    
    print(f"✅ Komplette Latency-Test-Suite generiert in {output_dir}/")
    print(f"\n📊 Test-Statistiken:")
    print(f"   - Gesamtanzahl Tests: {len(all_tests)}")
    
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
    print(f"   - Total Instructions pro Testlauf: {total_instructions}")
    
    print(f"\n📁 Generierte Dateien:")
    print(f"   - main/esp32c6_latency_tests.h")
    print(f"   - main/esp32c6_latency_tests.c")
    print(f"   - main/main.c")
    print(f"   - main/CMakeLists.txt")
    print(f"   - CMakeLists.txt (Root)")
    
    print(f"\n🚀 Build-Anleitung:")
    print(f"   1. cd {output_dir}")
    print(f"   2. idf.py set-target esp32c6")
    print(f"   3. idf.py build")
    print(f"   4. idf.py flash monitor")
    
    return all_tests




# ============================================================================
# 6. MAIN EXECUTION
# ============================================================================

# ... (deine Klassen und Templates bleiben gleich bis zum Ende von generate_complete_latency_test_suite) ...

# ============================================================================
# 4. MAIN EXECUTION (Vollständig bereinigt)
# ============================================================================

if __name__ == "__main__":
    print("ESP32-C6 Latency Test Generator - Clean Version")
    print("=" * 60)
    
    # Generiere direkt die neue Suite ohne Nachfrage
    output_directory = "esp32c6_latency_fixed"
    tests = generate_complete_latency_test_suite(output_directory)
    
    print("\n" + "=" * 60)
    print(f"✅ Fertig! Die Test-Suite wurde in '{output_directory}' erstellt.")
    
    # Zeige eine kurze Zusammenfassung der generierten Tests
    print("\n📋 Übersicht der generierten Kategorien:")
    categories = {}
    for test in tests:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        print(f"   - {cat}: {count} Tests")

    print("\n🚀 Nächste Schritte:")
    print(f"   1. cd {output_directory}")
    print("   2. idf.py set-target esp32c6")
    print("   3. idf.py build flash monitor")