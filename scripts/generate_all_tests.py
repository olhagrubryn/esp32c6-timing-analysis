#!/usr/bin/env python3
# scripts/generate_all_tests.py - Hauptgenerator für Latenz und Durchsatz
# FIXED: Korrekte Pfade für Header-Includes

import os
import sys
import random
import argparse
from collections import defaultdict

# Pfad für Imports setzen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Basis-Klassen
from base.config import MAIN_DIR, TESTS_DIR
from base.code_generator import generate_test_function, generate_header_content, generate_c_file_content

# Latenz-Generatoren
from generators.latency_generator import (
    SingleInstructionTestGenerator as LatencySingleGenerator,
    LatencyRAWChainGenerator,
    ZeroIdiomTestGenerator,
    MixedClassTestGenerator,
    MultiInstructionTestGenerator
)

# Durchsatz-Generatoren
from generators.throughput_generator import (
    ThroughputBaseGenerator,
    ThroughputDividerGenerator,
    ThroughputComparisonGenerator
)

from generators.comparison_generator import ComparisonTestGenerator

# ============================================================================
# TEST-SAMMLER
# ============================================================================

class TestCollector:
    @staticmethod
    def collect_latency_tests():
        tests = []
        
        print("\n  [Latency] Single instruction tests...")
        single = LatencySingleGenerator.generate_all()
        tests.extend(single)
        print(f"    → {len(single)} tests")
        
        print("  [Latency] RAW dependency chains...")
        raw = LatencyRAWChainGenerator.generate_class_tests()
        tests.extend(raw)
        print(f"    → {len(raw)} tests")
        
        print("  [Latency] Zero idiom tests...")
        zero = ZeroIdiomTestGenerator.generate_all()
        tests.extend(zero)
        print(f"    → {len(zero)} tests")
        
        print("  [Latency] Mixed class tests...")
        mixed = MixedClassTestGenerator.generate_all()
        tests.extend(mixed)
        print(f"    → {len(mixed)} tests")
        
        print("  [Latency] Multi instruction tests...")
        multi = MultiInstructionTestGenerator.generate_all()
        tests.extend(multi)
        print(f"    → {len(multi)} tests")
        
        print("  [Latency] Comparison tests...")
        comp = ComparisonTestGenerator.generate_latency_for_divider_values()
        comp.extend(ComparisonTestGenerator.generate_latency_for_throughput_comparison())
        tests.extend(comp)
        print(f"    → {len(comp)} tests")
        
        return tests
    
    @staticmethod
    def collect_throughput_tests():
        tests = []
        
        print("\n  [Throughput] Base tests...")
        base = ThroughputBaseGenerator.generate_all()
        tests.extend(base)
        print(f"    → {len(base)} tests")
        
        print("  [Throughput] Divider value tests...")
        div = ThroughputDividerGenerator.generate_all()
        tests.extend(div)
        print(f"    → {len(div)} tests")
        
        print("  [Throughput] Comparison tests...")
        comp = ThroughputComparisonGenerator.generate_all()
        tests.extend(comp)
        print(f"    → {len(comp)} tests")
        
        return tests

# ============================================================================
# DATEI-GENERATOR FÜR Latenz
# ============================================================================

class LatencyFileGenerator:
    """Generiert Dateien für Latenz-Tests."""
    
    @staticmethod
    def ensure_directories():
        """Erstellt benötigte Verzeichnisse."""
        subdirs = ["single", "chains", "sequences", "random", "stress", "memory", "multi", "raw_chains", "mixed"]
        for subdir in subdirs:
            os.makedirs(os.path.join(TESTS_DIR, subdir), exist_ok=True)
        print("    ✓ Latenz-Verzeichnisse erstellt")
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        """Generiert Latenz-Test-Dateien."""
        test_files = []
        
        for test in tests:
            subdir = LatencyFileGenerator._determine_subdir(test)
            subdir_path = os.path.join(TESTS_DIR, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            func_name, func_code = generate_test_function(test, test_type="latency")
            
            c_filename = f"{test['safe_name']}_latency.c"
            h_filename = f"{test['safe_name']}_latency.h"
            
            # Header mit korrektem Pfad (von tests/subdir/ zu main/)
            header_content = f"""#ifndef TEST_{test['safe_name'].upper()}_H
#define TEST_{test['safe_name'].upper()}_H

#include "../../main/test_result.h"

test_result_t {func_name}(void);

#endif /* TEST_{test['safe_name'].upper()}_H */
"""
            with open(os.path.join(subdir_path, h_filename), "w") as f:
                f.write(header_content)
            
            # C-Datei mit korrekten Includes
            c_content = f"""#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_test_suite.h"
#include "../../main/test_result.h"
#include "{h_filename}"

extern portMUX_TYPE test_mutex;

{func_code}
"""
            with open(os.path.join(subdir_path, c_filename), "w") as f:
                f.write(c_content)
            
            description = test.get("description", f"{test['instruction_count']}x {test.get('category', 'unknown')}")
            test_value = test.get("test_value", -1)
            value_type = test.get("value_type", "NONE")
            
            category = test.get("class", test.get("category", "UNKNOWN"))
            
            test_entries.append(
                f'    {{"{test["name"]}", {{.as_result = {func_name}}}, {test["iterations"]}, '
                f'{test["instruction_count"]}, "{description}", '
                f'"{category}", "latency", {test_value}, "{value_type}"}}'
            )
            
            # Für die zentrale Header-Datei: Relativer Pfad von main/ zu den Tests
            header_includes.append(f'#include "../tests/{subdir}/{h_filename}"')
            test_files.append((test["safe_name"], test, c_filename, h_filename, subdir))
            print(f"    ✓ tests/{subdir}/{c_filename}")
        
        return test_files
    
    @staticmethod
    def _determine_subdir(test):
        """Bestimmt das Unterverzeichnis basierend auf Test-Eigenschaften."""
        name = test["name"]
        test_group = test.get("test_group", "")
        insn_count = test["instruction_count"]
        
        if "RAW" in name or test_group == "raw_chains":
            return "raw_chains"
        if "MIXED" in name or test_group == "mixed":
            return "mixed"
        if insn_count == 1:
            return "single"
        if insn_count >= 10 or "LONG" in name:
            return "multi"
        if "CHAIN" in name:
            return "chains"
        if "RAND" in name:
            return "random"
        if "STRESS" in name:
            return "stress"
        if "MEM" in name:
            return "memory"
        return "sequences"

# ============================================================================
# DATEI-GENERATOR FÜR Durchsatz
# ============================================================================

class ThroughputFileGenerator:
    """Generiert Dateien für Durchsatz-Tests."""
    
    @staticmethod
    def ensure_directories():
        """Erstellt benötigte Verzeichnisse."""
        subdirs = ["throughput_base", "throughput_divider", "throughput_compare_free", "throughput_compare_dep"]
        for subdir in subdirs:
            os.makedirs(os.path.join(TESTS_DIR, subdir), exist_ok=True)
        print("    ✓ Durchsatz-Verzeichnisse erstellt")
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        """Generiert Durchsatz-Test-Dateien."""
        test_files = []
        
        group_to_dir = {
            "throughput_base": "throughput_base",
            "throughput_divider": "throughput_divider",
            "throughput_compare_free": "throughput_compare_free",
            "throughput_compare_dep": "throughput_compare_dep",
        }
        
        for test in tests:
            group = test["group"]
            subdir = group_to_dir.get(group, "throughput_base")
            subdir_path = os.path.join(TESTS_DIR, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            func_name, func_code = generate_test_function(test, test_type="throughput")
            
            c_filename = f"{test['safe_name']}.c"
            h_filename = f"{test['safe_name']}.h"
            
            # Header mit korrektem Pfad (von tests/subdir/ zu main/)
            header_content = f"""#ifndef TEST_{test['safe_name'].upper()}_H
#define TEST_{test['safe_name'].upper()}_H

#include "../../main/test_result.h"

test_result_t {func_name}(void);

#endif /* TEST_{test['safe_name'].upper()}_H */
"""
            with open(os.path.join(subdir_path, h_filename), "w") as f:
                f.write(header_content)
            
            # C-Datei mit korrekten Includes
            c_content = f"""#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_test_suite.h"
#include "../../main/test_result.h"
#include "{h_filename}"

extern portMUX_TYPE test_mutex;

{func_code}
"""
            with open(os.path.join(subdir_path, c_filename), "w") as f:
                f.write(c_content)
            
            description = test.get("description", f"{test['instruction_count']}x {test.get('category', 'unknown')}")
            
            test_entries.append(
                f'    {{"{test["name"]}", {{.as_result = {func_name}}}, {test["iterations"]}, '
                f'{test["instruction_count"]}, "{description}", '
                f'"{test["category"]}", "throughput", {test["test_value"]}, "{test["value_type"]}"}}'
            )
            
            # Für die zentrale Header-Datei: Relativer Pfad von main/ zu den Tests
            header_includes.append(f'#include "../tests/{subdir}/{h_filename}"')
            test_files.append((test["safe_name"], test, c_filename, h_filename, subdir))
            print(f"    ✓ tests/{subdir}/{c_filename}")
        
        return test_files

# ============================================================================
# ZENTRALER DATEI-GENERATOR
# ============================================================================

class MasterFileGenerator:
    """Generiert alle zentralen Dateien (main.c, test_result.h, etc.)."""

    @staticmethod
    def generate_test_result_h():
        """Generiert test_result.h mit statistischen Definitionen."""
        content = """// main/test_result.h - Zentrale statistische Definitionen
#ifndef TEST_RESULT_H
#define TEST_RESULT_H

#include <stdint.h>
#include <math.h>

// Statistischer Rückgabetyp für ALLE Tests
typedef struct {
    float mean;      // Mittelwert
    float stddev;    // Standardabweichung
    float min;       // Minimum
    float max;       // Maximum
    float ci;        // 95% Konfidenzintervall
    float cpi;       // Cycles per Instruction
    float rel_error; // Relativer Fehler in %
} test_result_t;

// Funktion zur Berechnung optimaler Iterationen
static inline int calculate_optimal_iterations(float stddev, float mean, float desired_error_percent) {
    if (mean == 0) return 1000;
    
    float z = 1.96;  // 95% Konfidenz
    float E = desired_error_percent / 100.0;
    float rel_stddev = stddev / mean;
    float optimal_n = (z * rel_stddev / E) * (z * rel_stddev / E);
    
    int result = (int)optimal_n + 1;
    if (result < 3) result = 3;
    if (result > 10000) result = 10000;
    return result;
}

#endif /* TEST_RESULT_H */
"""
        with open(os.path.join(MAIN_DIR, "test_result.h"), "w") as f:
            f.write(content)
        print("    ✓ test_result.h")

    @staticmethod
  
    def generate_main_c():
        """Generiert main.c für ESP32-C6 mit korrekter Watchdog-Initialisierung für ESP-IDF v5.5."""
        main_c = """#include <stdio.h>
    #include <string.h>
    #include <stdlib.h>
    #include <ctype.h>
    #include "freertos/FreeRTOS.h"
    #include "freertos/task.h"
    #include "esp32c6_test_suite.h"
    #include "esp_task_wdt.h"

    void print_menu(void) {
        printf("\\n");
        printf("╔════════════════════════════════════════════════════════════╗\\n");
        printf("║     ESP32-C6 BENCHMARKING SUITE                           ║\\n");
        printf("║     Latenz + Durchsatz Analyse mit Statistik             ║\\n");
        printf("╠════════════════════════════════════════════════════════════╣\\n");
        printf("║  1. Alle Tests ausführen                                  ║\\n");
        printf("║  2. Nur Latenz-Tests                                      ║\\n");
        printf("║  3. Nur Durchsatz-Tests                                   ║\\n");
        printf("║  4. Latenz: Single-Instruction Tests                      ║\\n");
        printf("║  5. Latenz: Sequenz-Tests                                 ║\\n");
        printf("║  6. Latenz: Multi-Instruction Tests                       ║\\n");
        printf("║  7. Durchsatz: Basis-Tests                                ║\\n");
        printf("║  8. Durchsatz: Divider-Wert-Tests                         ║\\n");
        printf("║  9. Durchsatz: Vergleichstests (FREE vs DEP)              ║\\n");
        printf("║ 10. Vergleich Latenz vs Durchsatz (gleiche Werte)         ║\\n");
        printf("║  0. Beenden                                               ║\\n");
        printf("╚════════════════════════════════════════════════════════════╝\\n");
        printf("Auswahl (0-10): ");
        fflush(stdout);
    }

    int get_input_esp32c6(void) {
        char input[16] = {0};
        int index = 0;
        int c;
        
        while (1) {
            c = getchar();
            if (c == '\\n' || c == '\\r') {
                if (index == 0) return -1;
                input[index] = '\\0';
                break;
            }
            else if (c == '\\b' || c == 127) {
                if (index > 0) {
                    index--;
                    printf("\\b \\b");
                    fflush(stdout);
                }
            }
            else if (isdigit(c) && index < (sizeof(input) - 1)) {
                input[index++] = (char)c;
                printf("%c", c);
                fflush(stdout);
            }
            vTaskDelay(pdMS_TO_TICKS(5));
        }
        
        printf("\\n");
        int choice = atoi(input);
        if (choice >= 0 && choice <= 10) return choice;
        return -1;
    }

    void app_main(void) {
        // Watchdog für ESP-IDF v5.5 konfigurieren
        esp_task_wdt_config_t wdt_config = {
            .timeout_ms = 30000,  // 30 Sekunden
            .idle_core_mask = 0,  // Keine Idle-Cores
            .trigger_panic = true, // Panic bei Timeout
        };
        esp_task_wdt_init(&wdt_config);
        // Aktuelle Task zum Watchdog hinzufügen
        esp_task_wdt_add(NULL);
        
        vTaskDelay(pdMS_TO_TICKS(500));
        init_performance_counters();
        
        int choice = -1;
        print_menu();
        choice = get_input_esp32c6();
        
        if (choice < 0 || choice > 10) {
            printf("\\n❌ Ungültige Eingabe! Starte Standard: Alle Tests (1)\\n");
            choice = 1;
        }
        
        printf("\\n");
        
        switch (choice) {
            case 1: 
                printf("▶ Alle Tests\\n");
                run_all_tests(); 
                break;
            case 2: 
                printf("▶ Nur Latenz-Tests\\n");
                run_all_latency_tests(); 
                break;
            case 3: 
                printf("▶ Nur Durchsatz-Tests\\n");
                run_all_throughput_tests(); 
                break;
            case 4: 
                printf("▶ Latenz: Single-Instruction\\n");
                run_latency_single_tests(); 
                break;
            case 5: 
                printf("▶ Latenz: Sequenz-Tests\\n");
                run_latency_sequence_tests(); 
                break;
            case 6: 
                printf("▶ Latenz: Multi-Instruction\\n");
                run_latency_multi_tests(); 
                break;
            case 7: 
                printf("▶ Durchsatz: Basis-Tests\\n");
                run_throughput_base_tests(); 
                break;
            case 8: 
                printf("▶ Durchsatz: Divider-Wert-Tests\\n");
                run_throughput_divider_tests(); 
                break;
            case 9: 
                printf("▶ Durchsatz: Vergleichstests\\n");
                run_throughput_comparison_tests(); 
                break;
            case 10: 
                printf("▶ Vergleich Latenz vs Durchsatz\\n");
                compare_latency_throughput(); 
                break;
            case 0: 
                printf("Programm beendet.\\n");
                break;
        }
        
        if (choice != 0) {
            printf("\\n✅ Tests abgeschlossen!\\n");
            printf("Drücke Reset fuer neuen Durchlauf.\\n");
        }
        
        while (1) {
            vTaskDelay(pdMS_TO_TICKS(1000));
            esp_task_wdt_reset();  // Watchdog regelmäßig füttern
        }
    }
    """
        with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
            f.write(main_c)
        print("    ✓ main.c (ESP-IDF v5.5 kompatibel)")

    @staticmethod
    def generate_cmakelists(test_files_latency, test_files_throughput):
        """Generiert CMakeLists.txt mit allen Test-Dateien."""
        
        cmake_sources = "main.c\n    esp32c6_test_suite.c\n"
        
        for _, _, c_file, _, subdir in test_files_latency:
            cmake_sources += f"    ../tests/{subdir}/{c_file}\n"
        
        for _, _, c_file, _, subdir in test_files_throughput:
            cmake_sources += f"    ../tests/{subdir}/{c_file}\n"
        
        cmake = f"""idf_component_register(SRCS {cmake_sources}
                        INCLUDE_DIRS "." ".."
                        REQUIRES freertos driver esp_driver_gptimer)
"""
        with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
            f.write(cmake)
        print("    ✓ CMakeLists.txt")
    
    @staticmethod
    def generate_test_suite_h(header_includes):
        """Generiert zentrale Header-Datei mit Union-Typ."""
        
        header = """#ifndef ESP32C6_TEST_SUITE_H
#define ESP32C6_TEST_SUITE_H

#include <stdint.h>
#include <string.h>
#include "freertos/portmacro.h"
#include "test_result.h"

extern portMUX_TYPE test_mutex;

// Union für typsicheren Funktionscast
typedef union {
    test_result_t (*as_result)(void);
} test_func_t;

// Test-Funktionen - generiert
"""
        header += "\n".join(header_includes)
        header += """

// Initialization
void init_performance_counters(void);

// Haupt-Test-Runner
void run_all_tests(void);
void run_all_latency_tests(void);
void run_all_throughput_tests(void);

// Latenz-spezifisch
void run_latency_single_tests(void);
void run_latency_sequence_tests(void);
void run_latency_multi_tests(void);

// Durchsatz-spezifisch
void run_throughput_base_tests(void);
void run_throughput_divider_tests(void);
void run_throughput_comparison_tests(void);

// Vergleich
void compare_latency_throughput(void);

// Statistiken
extern const int TOTAL_TEST_COUNT;
extern const int LATENCY_TEST_COUNT;
extern const int THROUGHPUT_TEST_COUNT;

#endif /* ESP32C6_TEST_SUITE_H */
"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.h"), "w") as f:
            f.write(header)
        print("    ✓ esp32c6_test_suite.h")
    
    @staticmethod
    def generate_test_suite_c(test_entries_latency, test_entries_throughput):
        """Generiert zentrale C-Datei mit Test-Runnern und statistischer Auswertung."""
        
        all_entries = test_entries_latency + test_entries_throughput
        entries_str = ",\n".join(all_entries)
        
        c_content = f"""#include <stdio.h>
#include <string.h>
#include <math.h>
#include "esp32c6_test_suite.h"
#include "test_result.h"
#include "esp_task_wdt.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

// Test-Statistiken
const int LATENCY_TEST_COUNT = {len(test_entries_latency)};
const int THROUGHPUT_TEST_COUNT = {len(test_entries_throughput)};
const int TOTAL_TEST_COUNT = {len(all_entries)};

// Test-Definitionen mit Union für typsicheren Zugriff
typedef struct {{
    const char* name;
    test_func_t func;
    int iterations;
    int instruction_count;
    const char* description;
    const char* category;
    const char* type;
    int test_value;
    const char* value_type;
}} test_entry_t;

static const test_entry_t all_tests[] = {{
{entries_str}
}};

#define NUM_TESTS (sizeof(all_tests) / sizeof(all_tests[0]))

void init_performance_counters(void) {{
    __asm__ __volatile__ (
        "li a2, 1\\n"
        "csrw 0x7E0, a2\\n"
        "csrw 0x7E1, a2\\n"
        ::: "a2"
    );
}}

void run_all_tests(void) {{
    printf("\\n========================================================\\n");
    printf("ALLE TESTS (%d insgesamt)\\n", TOTAL_TEST_COUNT);
    printf("========================================================\\n");
    run_all_latency_tests();
    run_all_throughput_tests();
}}

void run_all_latency_tests(void) {{
    printf("\\n========================================================\\n");
    printf("LATENZ-TESTS mit statistischer Auswertung (%d Tests)\\n", LATENCY_TEST_COUNT);
    printf("========================================================\\n");
    printf("\\n%-30s %-10s %-10s %-8s %-8s %-10s %-8s %s\\n", 
           "Test Name", "Mean", "StdDev", "Min", "Max", "CI95%%", "Rel%%", "Opt(5/3/1%%)");
    printf("%-30s %-10s %-10s %-8s %-8s %-10s %-8s %s\\n",
           "---------", "----", "------", "---", "---", "-----", "----", "-----------");
    
    float total = 0;
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "latency") == 0) {{
            // Watchdog vor jedem Test füttern
            esp_task_wdt_reset();
            
            test_result_t res = all_tests[i].func.as_result();
            
            float per_inst = res.mean / all_tests[i].iterations / all_tests[i].instruction_count;
            total += per_inst;
            
            printf("%-30s %-10.2f %-10.2f %-8.0f %-8.0f %-10.2f %-8.1f ",
                   all_tests[i].name, 
                   res.mean, res.stddev, res.min, res.max, res.ci, res.rel_error);
            
            int opt_5 = calculate_optimal_iterations(res.stddev, res.mean, 5);
            int opt_3 = calculate_optimal_iterations(res.stddev, res.mean, 3);
            int opt_1 = calculate_optimal_iterations(res.stddev, res.mean, 1);
            printf("%d/%d/%d\\n", opt_5, opt_3, opt_1);
        }}
    }}
    
    printf("\\nAverage latency per instruction: %.2f cycles\\n", total / LATENCY_TEST_COUNT);
}}

void run_all_throughput_tests(void) {{
    printf("\\n========================================================\\n");
    printf("DURCHSATZ-TESTS mit statistischer Auswertung (%d Tests)\\n", THROUGHPUT_TEST_COUNT);
    printf("========================================================\\n");
    printf("\\n%-30s %-10s %-10s %-10s %-8s %-8s %s\\n", 
           "Test Name", "CPI", "StdDev", "CI95%%", "Rel%%", "IPC", "Opt(5/3/1%%)");
    printf("%-30s %-10s %-10s %-10s %-8s %-8s %s\\n",
           "---------", "---", "------", "-----", "----", "---", "-----------");
    
    float total_cpi = 0;
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0) {{
            // Watchdog vor jedem Test füttern
            esp_task_wdt_reset();
            
            test_result_t res = all_tests[i].func.as_result();
            
            float cpi = res.mean / all_tests[i].instruction_count;
            float ipc = 1.0f / cpi;
            total_cpi += cpi;
            
            printf("%-30s %-10.3f %-10.3f %-10.3f %-8.1f %-8.3f ",
                   all_tests[i].name, cpi, res.stddev, res.ci, res.rel_error, ipc);
            
            int opt_5 = calculate_optimal_iterations(res.stddev, res.mean, 5);
            int opt_3 = calculate_optimal_iterations(res.stddev, res.mean, 3);
            int opt_1 = calculate_optimal_iterations(res.stddev, res.mean, 1);
            printf("%d/%d/%d\\n", opt_5, opt_3, opt_1);
        }}
    }}
    
    printf("\\nAverage CPI: %.3f, Average IPC: %.3f\\n", 
           total_cpi / THROUGHPUT_TEST_COUNT, 
           (float)THROUGHPUT_TEST_COUNT / total_cpi);
}}

// ... restliche Funktionen bleiben gleich ...
"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.c"), "w") as f:
            f.write(c_content)
        print("    ✓ esp32c6_test_suite.c")

# ============================================================================
# HAUPTFUNKTION
# ============================================================================

def main():
    """Hauptfunktion - generiert ALLE Tests."""
    
    parser = argparse.ArgumentParser(description='Generiere Latenz- und Durchsatz-Tests')
    parser.add_argument('--latency-only', action='store_true', help='Nur Latenz-Tests generieren')
    parser.add_argument('--throughput-only', action='store_true', help='Nur Durchsatz-Tests generieren')
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("  ESP32-C6 TEST GENERATOR".center(80))
    print("  Latenz + Durchsatz mit gleichen Werten!".center(80))
    print("=" * 80)
    
    latency_tests = []
    throughput_tests = []
    
    if not args.throughput_only:
        print("\n📊 Sammele LATENZ-Tests...")
        latency_tests = TestCollector.collect_latency_tests()
        print(f"  → {len(latency_tests)} Latenz-Tests")
    
    if not args.latency_only:
        print("\n📊 Sammele DURCHSATZ-Tests...")
        throughput_tests = TestCollector.collect_throughput_tests()
        print(f"  → {len(throughput_tests)} Durchsatz-Tests")
    
    print(f"\n📊 GESAMT: {len(latency_tests) + len(throughput_tests)} Tests")
    
    print("\n📁 Generiere Test-Dateien...")
    
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    
    test_entries_latency = []
    test_entries_throughput = []
    header_includes = []
    test_files_latency = []
    test_files_throughput = []
    
    if latency_tests:
        print("\n  LATENZ-Testdateien:")
        LatencyFileGenerator.ensure_directories()
        test_files_latency = LatencyFileGenerator.generate_files(
            latency_tests, test_entries_latency, header_includes
        )
    
    if throughput_tests:
        print("\n  DURCHSATZ-Testdateien:")
        ThroughputFileGenerator.ensure_directories()
        test_files_throughput = ThroughputFileGenerator.generate_files(
            throughput_tests, test_entries_throughput, header_includes
        )
    
    print("\n  Zentrale Dateien:")
    MasterFileGenerator.generate_test_result_h()
    MasterFileGenerator.generate_test_suite_h(header_includes)
    MasterFileGenerator.generate_test_suite_c(test_entries_latency, test_entries_throughput)
    MasterFileGenerator.generate_main_c()
    MasterFileGenerator.generate_cmakelists(test_files_latency, test_files_throughput)
    
    print("\n" + "=" * 80)
    print("  GENERIERUNG ABGESCHLOSSEN!".center(80))
    print("=" * 80)
    
    print(f"\n📊 STATISTIK:")
    print(f"  • Latenz-Tests: {len(latency_tests)}")
    print(f"  • Durchsatz-Tests: {len(throughput_tests)}")
    print(f"  • Gesamt: {len(latency_tests) + len(throughput_tests)}")
    print(f"\n📁 Dateien in main/ und tests/")
    print(f"\n📋 Nächste Schritte:")
    print(f"  1. idf.py clean")
    print(f"  2. idf.py build")
    print(f"  3. idf.py -p PORT flash monitor")

if __name__ == "__main__":
    random.seed(42)
    main()