#!/usr/bin/env python3
# scripts/generate_latency_tests.py - ESP32-C6 Instruction Latency Test Generator

import os
import sys
import random
import shutil

# ============================================================================
# Pfad-Konfiguration
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

# ============================================================================
# 1. RISCV INSTRUKTIONEN DATENBANK
# ============================================================================

class RISCVInstructions:
    """Zentrale Datenbank aller RISC-V Instruktionen für ESP32-C6."""
    
    @staticmethod
    def get_all_instructions():
        """Alle verfügbaren Instruktionen mit korrekter Syntax."""
        return {
            # === ALU Register-zu-Register ===
            "add":  "add {dst}, {src1}, {src2}",
            "sub":  "sub {dst}, {src1}, {src2}",
            "xor":  "xor {dst}, {src1}, {src2}",
            "or":   "or {dst}, {src1}, {src2}",
            "and":  "and {dst}, {src1}, {src2}",
            "sll":  "sll {dst}, {src1}, {src2}",
            "srl":  "srl {dst}, {src1}, {src2}",
            "sra":  "sra {dst}, {src1}, {src2}",
            "slt":  "slt {dst}, {src1}, {src2}",
            "sltu": "sltu {dst}, {src1}, {src2}",
            
            # === ALU Immediate ===
            "addi":  "addi {dst}, {src1}, {imm}",
            "xori":  "xori {dst}, {src1}, {imm}",
            "ori":   "ori {dst}, {src1}, {imm}",
            "andi":  "andi {dst}, {src1}, {imm}",
            "slli":  "slli {dst}, {src1}, {imm}",
            "srli":  "srli {dst}, {src1}, {imm}",
            "srai":  "srai {dst}, {src1}, {imm}",
            "slti":  "slti {dst}, {src1}, {imm}",
            "sltiu": "sltiu {dst}, {src1}, {imm}",
            
            # === Load Instruktionen ===
            "lb":   "lb {dst}, 0({base})",
            "lh":   "lh {dst}, 0({base})",
            "lw":   "lw {dst}, 0({base})",
            "lbu":  "lbu {dst}, 0({base})",
            "lhu":  "lhu {dst}, 0({base})",
            
            # === Store Instruktionen ===
            "sb":   "sb {src}, 0({base})",
            "sh":   "sh {src}, 0({base})",
            "sw":   "sw {src}, 0({base})",
            
            # === Multiplikation/Division ===
            "mul":   "mul {dst}, {src1}, {src2}",
            "mulh":  "mulh {dst}, {src1}, {src2}",
            "mulhu": "mulhu {dst}, {src1}, {src2}",
            "div":   "div {dst}, {src1}, {src2}",
            "divu":  "divu {dst}, {src1}, {src2}",
            "rem":   "rem {dst}, {src1}, {src2}",
            "remu":  "remu {dst}, {src1}, {src2}",
        }
    
    @staticmethod
    def get_instructions_by_category():
        """Instruktionen gruppiert nach Kategorien."""
        return {
            "REG2REG": {
                "add", "sub", "xor", "or", "and", "sll", "srl", "sra", "slt", "sltu"
            },
            "IMMEDIATE": {
                "addi", "xori", "ori", "andi", "slli", "srli", "srai", "slti", "sltiu"
            },
            "LOAD": {
                "lb", "lh", "lw", "lbu", "lhu"
            },
            "STORE": {
                "sb", "sh", "sw"
            },
            "DIV_MUL": {
                "mul", "mulh", "mulhu", "div", "divu", "rem", "remu"
            }
        }

# ============================================================================
# 2. SINGLE-INSTRUKTION TEST GENERATOR
# ============================================================================

class SingleInstructionTestGenerator:
    """Generiert für JEDE Instruktion einen SEPARATEN Test."""
    
    @staticmethod
    def generate_test_for_instruction(insn_name, insn_template, category):
        """Erstellt einen einzelnen Test für EINE bestimmte Instruktion."""
        
        if category in ["LOAD", "STORE"]:
            iterations = 500
            description_prefix = "Memory"
        elif category == "DIV_MUL":
            iterations = 200
            description_prefix = "Arithmetic"
        else:
            iterations = 1000
            description_prefix = "ALU"
        
        if category == "LOAD":
            concrete_instr = insn_template.format(
                dst="a2",
                base="a3"
            )
            instructions = [(insn_name, concrete_instr)]
            
        elif category == "STORE":
            concrete_instr = insn_template.format(
                src="a2",
                base="a3"
            )
            instructions = [(insn_name, concrete_instr)]
            
        elif category == "IMMEDIATE":
            concrete_instr = insn_template.format(
                dst="a2",
                src1="a3",
                imm=random.choice([1, 2, 4, 8, 16])
            )
            instructions = [(insn_name, concrete_instr)]
            
        else:  # REG2REG oder DIV_MUL
            concrete_instr = insn_template.format(
                dst="a2",
                src1="a3",
                src2="a4"
            )
            instructions = [(insn_name, concrete_instr)]
        
        test = {
            "name": f"{insn_name}",
            "instructions": instructions,
            "iterations": iterations,
            "description": f"{description_prefix} latency test for {insn_name}",
            "category": category,
            "instruction_count": 1,
            "insn_name": insn_name
        }
        
        return test
    
    @staticmethod
    def generate_all_single_instruction_tests():
        """Generiert für JEDE Instruktion einen separaten Test."""
        all_tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        
        for category, insn_set in categories.items():
            for insn_name in sorted(insn_set):
                if insn_name in all_insn:
                    test = SingleInstructionTestGenerator.generate_test_for_instruction(
                        insn_name, 
                        all_insn[insn_name],
                        category
                    )
                    all_tests.append(test)
        
        return all_tests

# ============================================================================
# 3. SEQUENZ TEST GENERATOR - FIXED: KEIN ÜBERSCHREIBEN VON BASIS-REGISTERN
# ============================================================================

class SequenceTestGenerator:
    """Generiert Tests mit kurzen Sequenzen verschiedener Instruktionen."""
    
    @staticmethod
    def generate_sequence_test(insn_list, category, name_suffix):
        """Erstellt einen Test mit einer Sequenz von Instruktionen."""
        instructions = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        for i, insn_name in enumerate(insn_list):
            if insn_name in all_insn:
                template = all_insn[insn_name]
                
                if category == "LOAD":
                    # WICHTIG: NIEMALS a3 als Destination verwenden!
                    # a3 ist der Basis-Register und muss erhalten bleiben
                    dst_options = ["a2", "a4", "a5", "a6"]
                    dst = dst_options[i % len(dst_options)]
                    instr = template.format(dst=dst, base="a3")
                    instructions.append((insn_name, instr))
                    
                elif category == "STORE":
                    # STORE: Source Register, Basis a3 bleibt erhalten
                    src_options = ["a2", "a4", "a5", "a6"]
                    src = src_options[i % len(src_options)]
                    instr = template.format(src=src, base="a3")
                    instructions.append((insn_name, instr))
                    
                elif category == "IMMEDIATE":
                    dst = f"a{2 + (i % 4)}"
                    src1 = f"a{3 + ((i) % 3)}"
                    instr = template.format(dst=dst, src1=src1, imm=4)
                    instructions.append((insn_name, instr))
                    
                else:  # REG2REG oder DIV_MUL
                    dst = f"a{2 + (i % 4)}"
                    src1 = f"a{3 + ((i) % 3)}"
                    src2 = f"a{4 + ((i+1) % 3)}"
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                    instructions.append((insn_name, instr))
        
        if not instructions:
            return None
            
        if category in ["LOAD", "STORE"]:
            iterations = 300
        elif category == "DIV_MUL":
            iterations = 100
        else:
            iterations = 500
        
        test = {
            "name": f"SEQ_{name_suffix}",
            "instructions": instructions,
            "iterations": iterations,
            "description": f"Sequence of {len(instructions)} {category} instructions",
            "category": category,
            "instruction_count": len(instructions),
            "insn_name": "sequence"
        }
        
        return test
    
    @staticmethod
    def generate_all_sequence_tests():
        """Generiert verschiedene Sequenz-Tests pro Kategorie."""
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        for category, insn_set in categories.items():
            insn_list = sorted(list(insn_set))
            
            if len(insn_list) < 2:
                continue
            
            # Für ALLE Kategorien: 2er und 3er Sequenzen
            test = SequenceTestGenerator.generate_sequence_test(
                insn_list[:2], category, f"{category}_2mix"
            )
            if test: tests.append(test)
            
            if len(insn_list) >= 3:
                test = SequenceTestGenerator.generate_sequence_test(
                    insn_list[:3], category, f"{category}_3mix"
                )
                if test: tests.append(test)
            
            # Random Sequenzen NUR für nicht-memory Kategorien
            if category not in ["LOAD", "STORE"]:
                random_sample = random.sample(insn_list, min(4, len(insn_list)))
                test = SequenceTestGenerator.generate_sequence_test(
                    random_sample, category, f"{category}_random"
                )
                if test: tests.append(test)
        
        return tests

# ============================================================================
# 4. C CODE GENERATOR - KEIN addi a3, a3, 0 MEHR!
# ============================================================================

def generate_test_function(test):
    """Generiert C-Code für EINEN Test."""
    
    func_name = f"test_{test['name'].replace('-', '_').replace('.', '_')}"
    
    instruction_lines = []
    
    # KEIN "addi a3, a3, 0" mehr - das ist überflüssig!
    # Der Compiler macht "mv a3, %[mem_ptr]" bereits in der Inline-Assembly
    
    # Instruktionen mit korrekter Syntax
    for insn_name, operands in test["instructions"]:
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    # C-Funktion Template mit Speicher-Initialisierung
    func_template = f"""float {func_name}(void) {{
    float total_cycles = 0;
    
    // Safe buffer in RAM - mit initialisierten Werten!
    static uint32_t safe_buffer[16] __attribute__((aligned(16))) = {{
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678
    }};
    
    uint32_t *ptr = safe_buffer;
    
    // Initial values for registers
    uint32_t r3_val = 0x12345678;
    uint32_t r4_val = 0x87654321;
    uint32_t r5_val = 0xABCDEF01;
    uint32_t r6_val = 0xFEDCBA98;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {test["iterations"]}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"      // a3 = safe_buffer (BLEIBT ERHALTEN!)
            "mv a4, %[mem_ptr]\\n"
            "mv a5, %[mem_ptr]\\n"
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n" // Start cycle count
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"   // End cycle count
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr), "r"(r3_val), "r"(r4_val), "r"(r5_val), "r"(r6_val)
            : "a2", "a3", "a4", "a5", "a6", "memory"
        );
        total_cycles += (float)(t_end - t_start);
    }}
    
    portEXIT_CRITICAL(&test_mutex);
    return total_cycles;
}}
"""
    return func_template

# ============================================================================
# 5. FILE GENERATOR
# ============================================================================

def ensure_directories():
    """Stellt sicher, dass alle benötigten Verzeichnisse existieren."""
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    print(f"  ✓ Using main dir: {MAIN_DIR}")
    print(f"  ✓ Using tests dir: {TESTS_DIR}")

def generate_all_test_files(all_tests):
    """Generiert alle Test-Files."""
    
    ensure_directories()
    
    # ========================================================================
    # 1. Generiere Test-Files im tests/ Verzeichnis
    # ========================================================================
    
    test_files = []
    
    for i, test in enumerate(all_tests):
        safe_name = test['name'].replace('-', '_').replace('.', '_')
        c_filename = f"{safe_name}_latency.c"
        h_filename = f"{safe_name}_latency.h"
        
        # Header
        header_guard = f"TEST_{safe_name.upper()}_LATENCY_H"
        header_content = f"""#ifndef {header_guard}
#define {header_guard}

float test_{safe_name}(void);

#endif /* {header_guard} */
"""
        
        # C-File
        func_name = f"test_{safe_name}"
        test_func = generate_test_function(test)
        
        c_content = f"""#include <stdio.h>
#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../main/esp32c6_latency_tests.h"

extern portMUX_TYPE test_mutex;

{test_func}
"""
        
        with open(os.path.join(TESTS_DIR, c_filename), "w") as f:
            f.write(c_content)
        
        with open(os.path.join(TESTS_DIR, h_filename), "w") as f:
            f.write(header_content)
        
        test_files.append((safe_name, test, c_filename, h_filename))
        print(f"  ✓ Generated: tests/{c_filename}")
    
    # ========================================================================
    # 2. Generiere zentrale Header-Datei
    # ========================================================================
    
    central_header = """#ifndef ESP32C6_LATENCY_TESTS_H
#define ESP32C6_LATENCY_TESTS_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Test-Funktionen - generiert
"""
    
    for safe_name, test, _, h_file in test_files:
        central_header += f'#include "../tests/{h_file}"\n'
    
    central_header += """
// Initialization
void init_performance_counters(void);

// Test runners
void run_all_latency_tests(void);
void run_category_tests(const char* category);
void print_csv_results(void);
void print_detailed_results(void);

// Externer Zugriff auf Test-Anzahl
extern const int LATENCY_TEST_COUNT;

#endif /* ESP32C6_LATENCY_TESTS_H */
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_latency_tests.h"), "w") as f:
        f.write(central_header)
    
    # ========================================================================
    # 3. Generiere MAIN Test-Runner
    # ========================================================================
    
    test_definitions = []
    for safe_name, test, c_file, h_file in test_files:
        test_definitions.append(f'    {{"{test["name"]}", test_{safe_name}, {test["iterations"]}, {test["instruction_count"]}, "{test["description"]}", "{test["category"]}"}}')
    
    test_definitions_str = ",\n".join(test_definitions)
    
    main_content = f"""#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

// Anzahl der Tests
const int LATENCY_TEST_COUNT = {len(test_files)};

void init_performance_counters(void) {{
    __asm__ __volatile__ (
        "li a2, 1\\n"
        "csrw 0x7E0, a2\\n"
        "csrw 0x7E1, a2\\n"
        ::: "a2"
    );
}}

// ============================================================================
// TEST DEFINITIONS
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
{test_definitions_str}
}};

#define NUM_TESTS (sizeof(all_tests) / sizeof(all_tests[0]))

// ============================================================================
// TEST RUNNERS
// ============================================================================

void run_all_latency_tests(void) {{
    printf("\\n========================================================\\n");
    printf("ESP32-C6 INSTRUCTION LATENCY TESTS\\n");
    printf("========================================================\\n\\n");
    printf("Total tests: %d\\n\\n", NUM_TESTS);
    
    init_performance_counters();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    printf("%-20s %-12s %-8s %-12s %s\\n", 
           "Instruction", "Cycles", "CPI", "Latency(cycles)", "Category");
    printf("%-20s %-12s %-8s %-12s %s\\n",
           "-----------", "------", "---", "--------------", "--------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const latency_test_t* test = &all_tests[i];
        
        float cycles = test->function();
        float cpi = cycles / (float)test->instruction_count;
        float latency = cycles / (float)test->iterations;
        
        printf("%-20s %-12.2f %-8.2f %-12.2f %s\\n",
               test->name, cycles, cpi, latency, test->category);
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }}
}}

void run_category_tests(const char* category) {{
    printf("\\n=== Category: %s ===\\n", category);
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].category, category) == 0) {{
            float cycles = all_tests[i].function();
            float latency = cycles / (float)all_tests[i].iterations;
            printf("  %-20s: %8.2f cycles, latency: %8.2f cycles/iter\\n",
                   all_tests[i].name, cycles, latency);
        }}
    }}
}}

void print_detailed_results(void) {{
    printf("\\n========================================================\\n");
    printf("DETAILED INSTRUCTION LATENCY ANALYSIS\\n");
    printf("========================================================\\n");
    
    const char* categories[] = {{"REG2REG", "IMMEDIATE", "LOAD", "STORE", "DIV_MUL"}};
    const char* cat_names[] = {{"Register-to-Register", "Immediate", 
                               "Load", "Store", "Multiply/Divide"}};
    
    for (int cat_idx = 0; cat_idx < 5; cat_idx++) {{
        printf("\\n=== %s ===\\n", cat_names[cat_idx]);
        int count = 0;
        
        for (int i = 0; i < NUM_TESTS; i++) {{
            if (strcmp(all_tests[i].category, categories[cat_idx]) == 0) {{
                float cycles = all_tests[i].function();
                float latency = cycles / (float)all_tests[i].iterations;
                printf("  %-20s: %6.2f cycles/iter\\n",
                       all_tests[i].name, latency);
                count++;
            }}
        }}
        
        if (count == 0) printf("  (no tests)\\n");
    }}
}}

void print_csv_results(void) {{
    FILE* csv_file = fopen("/sd/latency_results.csv", "w");
    if (csv_file == NULL) {{
        printf("Warning: Cannot open CSV file\\n");
        return;
    }}
    
    fprintf(csv_file, "Instruction,Category,Cycles,Iterations,CPI,Latency\\n");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        float cycles = all_tests[i].function();
        float cpi = cycles / (float)all_tests[i].instruction_count;
        float latency = cycles / (float)all_tests[i].iterations;
        
        fprintf(csv_file, "%s,%s,%.2f,%" PRIu32 ",%.2f,%.2f\\n",
                all_tests[i].name, all_tests[i].category,
                cycles, all_tests[i].iterations, cpi, latency);
    }}
    
    fclose(csv_file);
    printf("\\nCSV results saved\\n");
}}
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_latency_tests.c"), "w") as f:
        f.write(main_content)
    
    # ========================================================================
    # 4. Generiere main.c
    # ========================================================================
    
    main_c = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

void app_main(void) {
    printf("\\n========================================\\n");
    printf("ESP32-C6 INSTRUCTION LATENCY MEASUREMENT\\n");
    printf("========================================\\n");
    printf("Testing %d instructions...\\n\\n", LATENCY_TEST_COUNT);
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Run all tests
    run_all_latency_tests();
    
    // Detailed analysis
    vTaskDelay(pdMS_TO_TICKS(500));
    print_detailed_results();
    
    printf("\\n=== All tests completed ===\\n");
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
"""
    
    with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
        f.write(main_c)
    
    # ========================================================================
    # 5. Generiere CMakeLists.txt
    # ========================================================================
    
    cmake_sources = "main.c\n    esp32c6_latency_tests.c\n"
    for safe_name, test, c_file, h_file in test_files:
        cmake_sources += f"    ../tests/{c_file}\n"
    
    cmake = f"""idf_component_register(SRCS {cmake_sources}
                       INCLUDE_DIRS "."
                       REQUIRES freertos)
"""
    
    with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
        f.write(cmake)
    
    return test_files

# ============================================================================
# 6. MAIN GENERATOR
# ============================================================================

def generate_complete_test_suite():
    """Hauptfunktion: Generiert ALLE Tests."""
    
    print("\n" + "=" * 70)
    print("ESP32-C6 INSTRUCTION LATENCY TEST GENERATOR")
    print("=" * 70)
    print(f"\nProject root: {PROJECT_ROOT}")
    
    # 1. Generiere Single-Instruction Tests
    print("\n[1/3] Generating SINGLE instruction tests...")
    single_tests = SingleInstructionTestGenerator.generate_all_single_instruction_tests()
    print(f"      → {len(single_tests)} individual instruction tests")
    
    # 2. Generiere Sequenz-Tests (FIXED: Kein Überschreiben von a3!)
    print("\n[2/3] Generating SEQUENCE tests...")
    sequence_tests = SequenceTestGenerator.generate_all_sequence_tests()
    print(f"      → {len(sequence_tests)} sequence tests")
    
    # 3. Kombiniere alle Tests
    all_tests = single_tests + sequence_tests
    
    print(f"\n[3/3] Generating {len(all_tests)} test files...")
    test_files = generate_all_test_files(all_tests)
    
    # ========================================================================
    # STATISTIK
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("GENERATION COMPLETE!")
    print("=" * 70)
    
    print(f"\n📊 TEST STATISTICS:")
    print(f"   • Total tests: {len(all_tests)}")
    
    categories = {}
    for test in all_tests:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n   By category:")
    for cat, count in sorted(categories.items()):
        name_map = {
            "REG2REG": "Register-to-Register",
            "IMMEDIATE": "Immediate Operations",
            "LOAD": "Load Instructions",
            "STORE": "Store Instructions", 
            "DIV_MUL": "Multiply/Divide"
        }
        cat_name = name_map.get(cat, cat)
        print(f"     • {cat_name:25}: {count:3} tests")
    
    single_count = len(single_tests)
    seq_count = len(sequence_tests)
    print(f"\n   • Single instruction tests: {single_count}")
    print(f"   • Sequence tests: {seq_count}")
    
    print(f"\n📁 GENERATED DIRECTORY STRUCTURE:")
    print(f"   {PROJECT_ROOT}/")
    print(f"   ├── main/")
    print(f"   │   ├── CMakeLists.txt")
    print(f"   │   ├── esp32c6_latency_tests.c")
    print(f"   │   ├── esp32c6_latency_tests.h")
    print(f"   │   └── main.c")
    print(f"   └── tests/")
    
    for i, (safe_name, test, c_file, h_file) in enumerate(test_files[:8]):
        print(f"       ├── {c_file}")
    if len(test_files) > 8:
        print(f"       ├── ... ({len(test_files)-8} more files)")
    
    print(f"\n🚀 BUILD & RUN:")
    print(f"   $ cd {PROJECT_ROOT}")
    print(f"   $ idf.py set-target esp32c6")
    print(f"   $ idf.py build")
    print(f"   $ idf.py flash monitor")
    
    print("\n✅ DONE!\n")
    
    return all_tests

# ============================================================================
# 7. MAIN
# ============================================================================

if __name__ == "__main__":
    random.seed(42)
    
    print(f"Script location: {SCRIPT_DIR}")
    print(f"Project root: {PROJECT_ROOT}")
    
    # Generiere alles
    tests = generate_complete_test_suite()