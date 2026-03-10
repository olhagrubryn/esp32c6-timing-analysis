#!/usr/bin/env python3
# scripts/generate_throughput_tests.py - ESP32-C6 Instruction Throughput Test Generator
# FIXED: Funktionsnamen-Konsistenz!

import os
import sys
import random
from collections import defaultdict

# ============================================================================
# PFAD-KONFIGURATION
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

# ============================================================================
# TEST VALUE REGISTRY - DIESELBEN WERTE WIE LATENCY-TESTS!
# ============================================================================

class TestValueRegistry:
    """Zentrale Registry für Testwerte."""
    
    HIGH_THROUGHPUT_VALUES = [2, 4, 8, 16, 32, 64]
    LOW_THROUGHPUT_VALUES = [3, 7, 13, 17, 19, 23]
    EDGE_CASE_VALUES = [0, 1, 0xFFFFFFFF, 0x7FFFFFFF]
    
    @classmethod
    def get_divider_test_values(cls):
        return {
            "high_throughput": cls.HIGH_THROUGHPUT_VALUES,
            "low_throughput": cls.LOW_THROUGHPUT_VALUES,
            "edge_cases": cls.EDGE_CASE_VALUES
        }
    
    @classmethod
    def get_value_category(cls, value):
        if value in cls.HIGH_THROUGHPUT_VALUES:
            return "HIGH"
        elif value in cls.LOW_THROUGHPUT_VALUES:
            return "LOW"
        elif value in cls.EDGE_CASE_VALUES:
            return "EDGE"
        return "UNKNOWN"

# ============================================================================
# RISC-V REGISTER (wie latency_tests.py)
# ============================================================================

class RISCVRegisters:
    """Definiert gültige Register für ESP32-C6."""
    
    TEMP_REGS = ["a2", "a4", "a5", "a6", "a7"]
    BASE_REG = "a3"
    DST_REGS = ["a2", "a4", "a5", "a6", "a7"]
    SRC_REGS = ["a2", "a4", "a5", "a6", "a7"]
    
    @staticmethod
    def get_independent_registers(count):
        regs = RISCVRegisters.TEMP_REGS[:]
        if count <= len(regs):
            return regs[:count]
        return [regs[i % len(regs)] for i in range(count)]

# ============================================================================
# RISC-V INSTRUKTIONEN
# ============================================================================

class RISCVInstructions:
    """Datenbank aller RISC-V Instruktionen."""
    
    @staticmethod
    def get_all_instructions():
        return {
            "add":  "add {dst}, {src1}, {src2}",
            "sub":  "sub {dst}, {src1}, {src2}",
            "xor":  "xor {dst}, {src1}, {src2}",
            "or":   "or {dst}, {src1}, {src2}",
            "and":  "and {dst}, {src1}, {src2}",
            "sll":  "sll {dst}, {src1}, {src2}",
            "srl":  "srl {dst}, {src1}, {src2}",
            "sra":  "sra {dst}, {src1}, {src2}",
            "addi": "addi {dst}, {src1}, {imm}",
            "lw":   "lw {dst}, {offset}({base})",
            "sw":   "sw {src}, {offset}({base})",
            "mul":  "mul {dst}, {src1}, {src2}",
            "div":  "div {dst}, {src1}, {src2}",
        }
    
    @staticmethod
    def get_throughput_characteristic(insn_name):
        characteristics = {
            "add": "THROUGHPUT_SINGLE_ISSUE",
            "sub": "THROUGHPUT_SINGLE_ISSUE",
            "xor": "THROUGHPUT_SINGLE_ISSUE",
            "or": "THROUGHPUT_SINGLE_ISSUE",
            "and": "THROUGHPUT_SINGLE_ISSUE",
            "sll": "THROUGHPUT_SINGLE_ISSUE",
            "srl": "THROUGHPUT_SINGLE_ISSUE",
            "sra": "THROUGHPUT_SINGLE_ISSUE",
            "addi": "THROUGHPUT_SINGLE_ISSUE",
            "lw": "THROUGHPUT_MEMORY",
            "sw": "THROUGHPUT_MEMORY",
            "mul": "THROUGHPUT_MULTI_CYCLE",
            "div": "THROUGHPUT_DIVIDER",
        }
        return characteristics.get(insn_name, "THROUGHPUT_SINGLE_ISSUE")

# ============================================================================
# THROUGHPUT TEST GENERATOR
# ============================================================================

class ThroughputTestGenerator:
    """Generiert Throughput-Tests."""
    
    @staticmethod
    def generate_all_tests():
        all_tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        print("\n[1/4] Generating base throughput tests...")
        base_tests = ThroughputTestGenerator._generate_base_tests(all_insn)
        all_tests.extend(base_tests)
        print(f"      → {len(base_tests)} base throughput tests")
        
        print("\n[2/4] Generating divider value tests...")
        div_tests = ThroughputTestGenerator._generate_divider_value_tests(all_insn)
        all_tests.extend(div_tests)
        print(f"      → {len(div_tests)} divider value tests")
        
        print("\n[3/4] Generating comparison tests...")
        comp_tests = ThroughputTestGenerator._generate_comparison_tests(all_insn)
        all_tests.extend(comp_tests)
        print(f"      → {len(comp_tests)} comparison tests")
        
        return all_tests
    
    @staticmethod
    def _generate_base_tests(all_insn):
        tests = []
        
        for insn_name, template in all_insn.items():
            if insn_name != "div":  # Divider separat
                for count in [4, 8, 16]:
                    test = ThroughputTestGenerator._create_base_test(
                        insn_name, template, count
                    )
                    if test:
                        tests.append(test)
        
        return tests
    
    @staticmethod
    def _create_base_test(insn_name, template, count):
        registers = RISCVRegisters.get_independent_registers(count)
        instructions = []
        
        category = RISCVInstructions.get_throughput_characteristic(insn_name)
        
        for i in range(count):
            dst = registers[i % len(registers)]
            
            if insn_name == "lw":
                offset = (i * 4) % 60
                instr = template.format(dst=dst, offset=offset, base=RISCVRegisters.BASE_REG)
            elif insn_name == "sw":
                offset = (i * 4) % 60
                instr = template.format(src=dst, offset=offset, base=RISCVRegisters.BASE_REG)
            elif insn_name == "addi":
                src1 = registers[(i + 1) % len(registers)]
                instr = template.format(dst=dst, src1=src1, imm=1)
            else:
                src1 = registers[(i + 1) % len(registers)]
                src2 = registers[(i + 2) % len(registers)]
                instr = template.format(dst=dst, src1=src1, src2=src2)
            
            instructions.append((insn_name, instr))
        
        return {
            "name": f"THROUGHPUT_{insn_name}_{count}",
            "safe_name": f"THROUGHPUT_{insn_name}_{count}",  # Für Funktionsnamen
            "instructions": instructions,
            "iterations": max(1, 3000 // count),
            "description": f"{count}x {insn_name} (unabhängig)",
            "category": category,
            "instruction_count": count,
            "group": "throughput_base",
            "test_value": -1,
            "value_type": "NONE"
        }
    
    @staticmethod
    def _generate_divider_value_tests(all_insn):
        tests = []
        template = all_insn.get("div")
        if not template:
            return tests
        
        for count in [4, 8, 16]:
            # HIGH Throughput
            for value in TestValueRegistry.HIGH_THROUGHPUT_VALUES:
                test = ThroughputTestGenerator._create_div_value_test(
                    template, count, value, "HIGH"
                )
                tests.append(test)
            
            # LOW Throughput
            for value in TestValueRegistry.LOW_THROUGHPUT_VALUES:
                test = ThroughputTestGenerator._create_div_value_test(
                    template, count, value, "LOW"
                )
                tests.append(test)
            
            # EDGE Cases
            for value in TestValueRegistry.EDGE_CASE_VALUES:
                test = ThroughputTestGenerator._create_div_value_test(
                    template, count, value, "EDGE"
                )
                tests.append(test)
        
        return tests
    
    @staticmethod
    def _create_div_value_test(template, count, value, value_type):
        registers = RISCVRegisters.get_independent_registers(count)
        instructions = []
        
        for i in range(count):
            dst = registers[i % len(registers)]
            src1 = registers[(i + 1) % len(registers)]
            src2 = registers[(i + 2) % len(registers)]
            instr = template.format(dst=dst, src1=src1, src2=src2)
            instructions.append(("div", instr))
        
        return {
            "name": f"DIV_{value_type}_{value}_{count}",
            "safe_name": f"DIV_{value_type}_{value}_{count}",
            "instructions": instructions,
            "iterations": max(1, 2000 // count),
            "description": f"Division mit Wert {value} ({value_type}) - {count}x",
            "category": f"THROUGHPUT_DIVIDER_{value_type}",
            "instruction_count": count,
            "group": "throughput_divider",
            "test_value": value,
            "value_type": value_type
        }
    
    @staticmethod
    def _generate_comparison_tests(all_insn):
        tests = []
        template = all_insn.get("div")
        if not template:
            return tests
        
        all_values = (TestValueRegistry.HIGH_THROUGHPUT_VALUES[:3] + 
                     TestValueRegistry.LOW_THROUGHPUT_VALUES[:3])
        
        for value in all_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            # Dependency-Free (Throughput)
            free_test = ThroughputTestGenerator._create_comparison_test(
                template, value, value_type, free=True
            )
            tests.append(free_test)
            
            # Dependent (Latency - gleicher Wert!)
            dep_test = ThroughputTestGenerator._create_comparison_test(
                template, value, value_type, free=False
            )
            tests.append(dep_test)
        
        return tests
    
    @staticmethod
    def _create_comparison_test(template, value, value_type, free=True):
        count = 8
        instructions = []
        
        if free:
            # Dependency-Free
            registers = RISCVRegisters.get_independent_registers(count)
            for i in range(count):
                dst = registers[i % len(registers)]
                src1 = registers[(i + 1) % len(registers)]
                src2 = registers[(i + 2) % len(registers)]
                instr = template.format(dst=dst, src1=src1, src2=src2)
                instructions.append(("div", instr))
            
            name_suffix = "FREE"
            category = "THROUGHPUT_COMPARE_FREE"
            group = "throughput_compare_free"
        else:
            # Dependent (RAW chain)
            last_dst = "a2"
            for i in range(count):
                dst = RISCVRegisters.TEMP_REGS[i % len(RISCVRegisters.TEMP_REGS)]
                src1 = last_dst
                src2 = RISCVRegisters.TEMP_REGS[(i + 2) % len(RISCVRegisters.TEMP_REGS)]
                instr = template.format(dst=dst, src1=src1, src2=src2)
                instructions.append(("div", instr))
                last_dst = dst
            
            name_suffix = "DEP"
            category = "THROUGHPUT_COMPARE_DEP"
            group = "throughput_compare_dep"
        
        return {
            "name": f"COMPARE_DIV_{name_suffix}_{value_type}_{value}",
            "safe_name": f"COMPARE_DIV_{name_suffix}_{value_type}_{value}",
            "instructions": instructions,
            "iterations": 1000,
            "description": f"{name_suffix}: Division mit Wert {value} ({value_type})",
            "category": category,
            "instruction_count": count,
            "group": group,
            "test_value": value,
            "value_type": value_type
    }

# ============================================================================
# C CODE GENERATOR - FIXED: Konsistenter Funktionsname!
# ============================================================================

def generate_test_function(test):
    """C-Code Generator - FIXED: safe_name wird für Funktionsnamen verwendet!"""
    
    # WICHTIG: Verwende safe_name für konsistenten Funktionsnamen!
    func_name = f"test_{test['safe_name']}"
    
    instruction_lines = []
    for insn_name, operands in test["instructions"]:
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    test_value = test.get("test_value", -1)
    value_type = test.get("value_type", "NONE")
    
    func_template = f"""float {func_name}(void) {{
    float total_cycles = 0;
    
    // Safe buffer in RAM
    static uint32_t safe_buffer[64] __attribute__((aligned(64))) = {{
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678,
    }};
    
    uint32_t *ptr = safe_buffer;
    
    // Initial values for registers
    uint32_t r2_val = 0x12345678;
    uint32_t r4_val = 0xABCDEF01;
    uint32_t r5_val = 0xFEDCBA98;
    uint32_t r6_val = 0x0F0F0F0F;
    uint32_t r7_val = 0xF0F0F0F0;
    
    // Test-Wert: {test_value} ({value_type})
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {test["iterations"]}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"
            "mv a2, %[r2_val]\\n"
            "mv a4, %[r4_val]\\n"
            "mv a5, %[r5_val]\\n"
            "mv a6, %[r6_val]\\n"
            "mv a7, %[r7_val]\\n"
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr),
              [r2_val] "r"(r2_val),
              [r4_val] "r"(r4_val),
              [r5_val] "r"(r5_val),
              [r6_val] "r"(r6_val),
              [r7_val] "r"(r7_val)
            : "a2", "a3", "a4", "a5", "a6", "a7", "memory"
        );
        total_cycles += (float)(t_end - t_start);
    }}
    
    portEXIT_CRITICAL(&test_mutex);
    
    // Return CYCLES PER INSTRUCTION (CPI)
    return total_cycles / (float)({test["iterations"]} * {test["instruction_count"]});
}}
"""
    return func_name, func_template

# ============================================================================
# FILE GENERATOR - FIXED: Korrekte Funktionsnamen in Header!
# ============================================================================

def ensure_directories():
    """Stellt sicher, dass alle benötigten Verzeichnisse existieren."""
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    
    os.makedirs(os.path.join(TESTS_DIR, "throughput_base"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "throughput_divider"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "throughput_compare_free"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "throughput_compare_dep"), exist_ok=True)
    
    print(f"  ✓ Created throughput test directories")

def generate_test_files(all_tests):
    """Generiert alle Test-Dateien - FIXED: Konsistente Funktionsnamen!"""
    
    ensure_directories()
    
    # Mapping von Gruppe zu Unterverzeichnis
    group_to_dir = {
        "throughput_base": "throughput_base",
        "throughput_divider": "throughput_divider",
        "throughput_compare_free": "throughput_compare_free",
        "throughput_compare_dep": "throughput_compare_dep",
    }
    
    test_files = []
    test_entries = []  # Für die zentrale C-Datei
    
    print("\nGenerating test files...")
    
    for test in all_tests:
        group = test["group"]
        subdir = group_to_dir.get(group, "throughput_base")
        subdir_path = os.path.join(TESTS_DIR, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        
        # Generiere Funktionsnamen
        func_name, func_code = generate_test_function(test)
        
        # Dateinamen
        c_filename = f"{test['safe_name']}.c"
        h_filename = f"{test['safe_name']}.h"
        
        # Header-Datei - WICHTIG: Gleicher Funktionsname wie in C!
        header_guard = f"THROUGHPUT_{test['safe_name'].upper()}_H"
        header_content = f"""#ifndef {header_guard}
#define {header_guard}

float {func_name}(void);

#endif /* {header_guard} */
"""
        
        with open(os.path.join(subdir_path, h_filename), "w") as f:
            f.write(header_content)
        
        # C-Datei
        c_content = f"""#include <stdio.h>
#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_throughput.h"

extern portMUX_TYPE test_mutex;

{func_code}
"""
        
        with open(os.path.join(subdir_path, c_filename), "w") as f:
            f.write(c_content)
        
        # Für die zentrale Test-Tabelle
        test_entries.append(
            f'    {{"{test["name"]}", {func_name}, {test["iterations"]}, '
            f'{test["instruction_count"]}, "{test["category"]}", "{test["group"]}", '
            f'{test["test_value"]}, "{test["value_type"]}"}}'
        )
        
        test_files.append((test["safe_name"], test, c_filename, h_filename, subdir))
        print(f"  ✓ Generated: tests/{subdir}/{c_filename} -> {func_name}")
    
    # Zentrale Header-Datei
    central_header = """#ifndef ESP32C6_THROUGHPUT_H
#define ESP32C6_THROUGHPUT_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Test-Funktionen - generiert
"""
    
    for safe_name, test, _, h_file, subdir in test_files:
        central_header += f'#include "../tests/{subdir}/{h_file}"\n'
    
    central_header += """
// Test result structure
typedef struct {
    const char* name;
    float (*function)(void);
    int iterations;
    int instruction_count;
    const char* category;
    const char* group;
    int test_value;
    const char* value_type;
} throughput_test_t;

// Initialization
void init_performance_counters(void);

// Test runners
void run_all_throughput_tests(void);
void print_value_comparison(void);

// Externer Zugriff auf Test-Anzahl
extern const int THROUGHPUT_TEST_COUNT;

#endif /* ESP32C6_THROUGHPUT_H */
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_throughput.h"), "w") as f:
        f.write(central_header)
    
    # Test-Runner C-Datei
    test_entries_str = ",\n".join(test_entries)
    
    main_content = f"""#include <stdio.h>
#include <string.h>
#include "esp32c6_throughput.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

// Test statistics
const int THROUGHPUT_TEST_COUNT = {len(test_files)};

void init_performance_counters(void) {{
    __asm__ __volatile__ (
        "li a2, 1\\n"
        "csrw 0x7E0, a2\\n"
        "csrw 0x7E1, a2\\n"
        ::: "a2"
    );
}}

// Test definitions
static const throughput_test_t all_tests[] = {{
{test_entries_str}
}};

#define NUM_TESTS (sizeof(all_tests) / sizeof(all_tests[0]))

void run_all_throughput_tests(void) {{
    printf("\\n========================================================\\n");
    printf("ESP32-C6 THROUGHPUT TESTS\\n");
    printf("========================================================\\n\\n");
    
    printf("Test Statistics: %d tests\\n\\n", NUM_TESTS);
    
    init_performance_counters();
    
    printf("\\n%-35s %-10s %-10s %-15s %s\\n", 
           "Test Name", "CPI", "IPC", "Category", "Value");
    printf("%-35s %-10s %-10s %-15s %s\\n",
           "---------", "---", "---", "--------", "-----");
    
    float total_cpi = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const throughput_test_t* test = &all_tests[i];
        
        float cycles_sum = 0;
        for (int run = 0; run < 3; run++) {{
            cycles_sum += test->function();
        }}
        
        float cycles_avg = cycles_sum / 3.0f;
        float cpi = cycles_avg;
        float ipc = 1.0f / cpi;
        
        total_cpi += cpi;
        
        printf("%-35s %-10.3f %-10.3f %-15s %s %d\\n",
               test->name, cpi, ipc, test->category,
               test->value_type, test->test_value);
    }}
    
    printf("\\nSummary: Average CPI = %.3f, Average IPC = %.3f\\n", 
           total_cpi / NUM_TESTS, 1.0f / (total_cpi / NUM_TESTS));
}}

void print_value_comparison(void) {{
    printf("\\n========================================================\\n");
    printf("VALUE COMPARISON: High vs Low Throughput\\n");
    printf("========================================================\\n\\n");
    
    // Hier kannst du die Auswertung implementieren
    printf("Vergleich der Werte aus Latency-Tests...\\n");
}}
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_throughput.c"), "w") as f:
        f.write(main_content)
    
    # main.c
    main_c = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_throughput.h"

void app_main(void) {
    printf("\\n");
    printf("╔════════════════════════════════════════════════════════════╗\\n");
    printf("║     ESP32-C6 THROUGHPUT ANALYSIS                          ║\\n");
    printf("║     Cycles Per Instruction (CPI) Measurement              ║\\n");
    printf("╚════════════════════════════════════════════════════════════╝\\n");
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    run_all_throughput_tests();
    
    printf("\\n✓ All throughput tests completed!\\n");
    printf("  Total tests: %d\\n", THROUGHPUT_TEST_COUNT);
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}
"""
    
    with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
        f.write(main_c)
    
    # CMakeLists.txt
    cmake_sources = "main.c\n    esp32c6_throughput.c\n"
    for safe_name, test, c_file, h_file, subdir in test_files:
        cmake_sources += f"    ../tests/{subdir}/{c_file}\n"
    
    cmake = f"""idf_component_register(SRCS {cmake_sources}
                       INCLUDE_DIRS "."
                       REQUIRES freertos)
"""
    
    with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
        f.write(cmake)
    
    return test_files

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Hauptfunktion."""
    
    print("\n" + "=" * 80)
    print("  ESP32-C6 THROUGHPUT TEST GENERATOR".center(80))
    print("  Verwendet DIESELBEN Werte wie Latency-Tests!".center(80))
    print("=" * 80)
    
    generator = ThroughputTestGenerator()
    all_tests = generator.generate_all_tests()
    
    print(f"\nTOTAL TESTS: {len(all_tests)}")
    
    generate_test_files(all_tests)
    
    print("\n" + "=" * 80)
    print("  GENERATION COMPLETE!".center(80))
    print("=" * 80)
    
    print("\n📋 Nächste Schritte:")
    print("  1. Baue mit 'idf.py build'")
    print("  2. Flashe mit 'idf.py -p PORT flash monitor'")
    print("\n   WICHTIG: Gleiche Werte wie Latency-Tests ermöglichen Vergleich!")

if __name__ == "__main__":
    random.seed(42)
    main()