#!/usr/bin/env python3
# scripts/generate_all_tests.py - KORRIGIERT

import os, sys, random, argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base.config import MAIN_DIR, TESTS_DIR
from base.code_generator import generate_test_function, generate_header_content, generate_c_file_content
from generators.latency_generator import *
from generators.throughput_generator import *
from generators.comparison_generator import ComparisonTestGenerator

# ============================================================================
# TEST-SAMMLER
# ============================================================================

class TestCollector:
    @staticmethod
    def collect_latency_tests():
        tests = []
        print("\n  [Latency] Collecting tests...")
        
        # Korrekte Klassennamen verwenden!
        for name, gen in [
            ("Single instruction", SingleInstructionTestGenerator.generate_all),
            ("RAW chains", LatencyRAWChainGenerator.generate_class_tests),
            ("Zero idioms", ZeroIdiomTestGenerator.generate_all),
            ("Mixed class", MixedClassTestGenerator.generate_all),
            ("Multi instruction", MultiInstructionTestGenerator.generate_all),
            ("Comparison", lambda: ComparisonTestGenerator.generate_latency_for_divider_values() + 
                                   ComparisonTestGenerator.generate_latency_for_throughput_comparison())
        ]:
            print(f"    → {name}...")
            for t in gen():
                t['type'] = 'latency'
                t.setdefault('test_value', -1)
                t.setdefault('value_type', 'NONE')
                tests.append(t)
        
        return tests
    
    @staticmethod
    def collect_throughput_tests():
        tests = []
        print("\n  [Throughput] Collecting tests...")
        
        for name, gen in [
            ("Base", ThroughputBaseGenerator.generate_all),
            ("Divider", ThroughputDividerGenerator.generate_all),
            ("Comparison", ThroughputComparisonGenerator.generate_all)
        ]:
            print(f"    → {name}...")
            for t in gen():
                t['type'] = 'throughput'
                tests.append(t)
        
        return tests


# ============================================================================
# DATEI-GENERATOREN
# ============================================================================

class LatencyFileGenerator:
    @staticmethod
    def ensure_directories():
        for d in ["single","chains","sequences","random","stress","memory","multi","raw_chains","mixed"]:
            os.makedirs(os.path.join(TESTS_DIR, d), exist_ok=True)
    
    @staticmethod
    def _subdir(test):
        n, g, ic, c = test["name"], test.get("test_group",""), test["instruction_count"], test.get("category","")
        if "LOAD" in c or "STORE" in c or "MEM" in n: return "memory"
        if "RAW" in n or g == "raw_chains": return "raw_chains"
        if "MIXED" in n or g == "mixed": return "mixed"
        if ic == 1: return "single"
        if ic >= 10 or "LONG" in n: return "multi"
        if "CHAIN" in n: return "chains"
        if "RAND" in n: return "random"
        if "STRESS" in n: return "stress"
        return "sequences"
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        test_files = []
        for test in tests:
            subdir = LatencyFileGenerator._subdir(test)
            os.makedirs(os.path.join(TESTS_DIR, subdir), exist_ok=True)
            
            fn, fc = generate_test_function(test, "latency")
            cf, hf = f"{test['safe_name']}_latency.c", f"{test['safe_name']}_latency.h"
            
            with open(os.path.join(TESTS_DIR, subdir, hf), "w") as f:
                f.write(generate_header_content(test, fn))
            
            with open(os.path.join(TESTS_DIR, subdir, cf), "w") as f:
                f.write(generate_c_file_content(test, fc))
            
            test_entries.append(
                f'    {{"{test["name"]}", {{.as_result = {fn}}}, {test["iterations"]}, '
                f'{test["instruction_count"]}, "{test.get("description","")}", '
                f'"{test.get("category","UNKNOWN")}", "latency", {test.get("test_value",-1)}, "{test.get("value_type","NONE")}"}}'
            )
            header_includes.append(f'#include "../tests/{subdir}/{hf}"')
            test_files.append((test["safe_name"], test, cf, hf, subdir))
            print(f"    ✓ tests/{subdir}/{cf}")
        return test_files


class ThroughputFileGenerator:
    @staticmethod
    def ensure_directories():
        for d in ["throughput_base","throughput_divider","throughput_compare_free","throughput_compare_dep"]:
            os.makedirs(os.path.join(TESTS_DIR, d), exist_ok=True)
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        group_dir = {
            "throughput_base": "throughput_base",
            "throughput_divider": "throughput_divider",
            "throughput_compare_free": "throughput_compare_free",
            "throughput_compare_dep": "throughput_compare_dep",
        }
        
        test_files = []
        for test in tests:
            subdir = group_dir.get(test.get("group","throughput_base"), "throughput_base")
            os.makedirs(os.path.join(TESTS_DIR, subdir), exist_ok=True)
            
            fn, fc = generate_test_function(test, "throughput")
            cf, hf = f"{test['safe_name']}.c", f"{test['safe_name']}.h"
            
            with open(os.path.join(TESTS_DIR, subdir, hf), "w") as f:
                f.write(generate_header_content(test, fn))
            
            with open(os.path.join(TESTS_DIR, subdir, cf), "w") as f:
                f.write(generate_c_file_content(test, fc))
            
            test_entries.append(
                f'    {{"{test["name"]}", {{.as_result = {fn}}}, {test["iterations"]}, '
                f'{test["instruction_count"]}, "{test.get("description","")}", '
                f'"{test["category"]}", "throughput", {test.get("test_value",-1)}, "{test.get("value_type","NONE")}"}}'
            )
            header_includes.append(f'#include "../tests/{subdir}/{hf}"')
            test_files.append((test["safe_name"], test, cf, hf, subdir))
            print(f"    ✓ tests/{subdir}/{cf}")
        return test_files


# ============================================================================
# ZENTRALE DATEI-GENERATOREN
# ============================================================================

class MasterFileGenerator:
    @staticmethod
    def generate_test_result_h():
        content = """#ifndef TEST_RESULT_H
#define TEST_RESULT_H

#include <stdint.h>
#include <math.h>

typedef struct {
    float mean, stddev, min, max, ci, cpi, rel_error;
} test_result_t;

static inline int calculate_optimal_iterations(float stddev, float mean, float desired_error_percent) {
    if (mean == 0) return 1000;
    float z = 1.96, E = desired_error_percent / 100.0, rel_stddev = stddev / mean;
    int n = (int)((z * rel_stddev / E) * (z * rel_stddev / E)) + 1;
    return n < 3 ? 3 : (n > 10000 ? 10000 : n);
}
#endif"""
        with open(os.path.join(MAIN_DIR, "test_result.h"), "w") as f:
            f.write(content)
    
    @staticmethod
    def generate_main_c():
        content = """#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_test_suite.h"
#include "esp_task_wdt.h"

void print_menu(void) {
    printf("\\n╔════════════════════════════════════════════════╗\\n");
    printf("║ ESP32-C6 BENCHMARKING SUITE                   ║\\n");
    printf("╠════════════════════════════════════════════════╣\\n");
    printf("║ 1. Alle Tests       2. Nur Latenz             ║\\n");
    printf("║ 3. Nur Durchsatz     4. Latenz: Single        ║\\n");
    printf("║ 5. Latenz: Sequenz   6. Latenz: Multi         ║\\n");
    printf("║ 7. Durchsatz: Base   8. Durchsatz: Divider    ║\\n");
    printf("║ 9. Durchsatz: Comp  10. Vergleich L/D         ║\\n");
    printf("║ 0. Beenden                                     ║\\n");
    printf("╚════════════════════════════════════════════════╝\\n");
    printf("Auswahl: "); fflush(stdout);
}

int get_input_esp32c6(void) {
    char input[16] = {0}; int idx = 0, c;
    while (1) {
        c = getchar();
        if (c == '\\n' || c == '\\r') { if (idx == 0) return -1; input[idx] = '\\0'; break; }
        else if ((c == '\\b' || c == 127) && idx > 0) { idx--; printf("\\b \\b"); fflush(stdout); }
        else if (isdigit(c) && idx < 15) { input[idx++] = (char)c; printf("%c", c); fflush(stdout); }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    printf("\\n"); int choice = atoi(input);
    return (choice >= 0 && choice <= 10) ? choice : -1;
}

void app_main(void) {
    esp_task_wdt_config_t wdt_config = { .timeout_ms = 30000, .idle_core_mask = 0, .trigger_panic = true };
    esp_task_wdt_init(&wdt_config); esp_task_wdt_add(NULL);
    vTaskDelay(pdMS_TO_TICKS(500));
    
    printf("\\n╔════════════════════════════════════════════════╗\\n");
    printf("║ ESP32-C6 BENCHMARKING SUITE                   ║\\n");
    printf("╚════════════════════════════════════════════════╝\\n");
    init_performance_counters();
    
    while (1) {
        print_menu();
        int choice = get_input_esp32c6();
        if (choice < 0 || choice > 10) { printf("\\n❌ Ungültig!\\n"); continue; }
        printf("\\n");
        
        switch (choice) {
            case 1: run_all_tests(); break;
            case 2: run_all_latency_tests(); break;
            case 3: run_all_throughput_tests(); break;
            case 4: run_latency_single_tests(); break;
            case 5: run_latency_sequence_tests(); break;
            case 6: run_latency_multi_tests(); break;
            case 7: run_throughput_base_tests(); break;
            case 8: run_throughput_divider_tests(); break;
            case 9: run_throughput_comparison_tests(); break;
            case 10: compare_latency_throughput(); break;
            case 0: printf("Beendet.\\n"); break;
        }
        if (choice != 0) { printf("\\n✅ Fertig! Taste für Menü...\\n"); }
        esp_task_wdt_reset(); vTaskDelay(pdMS_TO_TICKS(100));
    }
}"""
        with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
            f.write(content)
    
    @staticmethod
    def generate_cmakelists(test_files_l, test_files_t):
        sources = "main.c\n    esp32c6_test_suite.c\n"
        for _,_,cf,_,sd in test_files_l + test_files_t:
            sources += f"    ../tests/{sd}/{cf}\n"
        
        with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
            f.write(f"idf_component_register(SRCS {sources} INCLUDE_DIRS \".\" \"..\" REQUIRES freertos driver esp_driver_gptimer)\n")
    
    @staticmethod
    def generate_test_suite_h(header_includes):
        h = """#ifndef ESP32C6_TEST_SUITE_H
#define ESP32C6_TEST_SUITE_H

#include <stdint.h>
#include <string.h>
#include "freertos/portmacro.h"
#include "test_result.h"

extern portMUX_TYPE test_mutex;

typedef union { test_result_t (*as_result)(void); } test_func_t;

"""
        h += "\n".join(header_includes)
        h += """

void init_performance_counters(void);
void run_all_tests(void);
void run_all_latency_tests(void);
void run_all_throughput_tests(void);
void run_latency_single_tests(void);
void run_latency_sequence_tests(void);
void run_latency_multi_tests(void);
void run_throughput_base_tests(void);
void run_throughput_divider_tests(void);
void run_throughput_comparison_tests(void);
void compare_latency_throughput(void);

extern const int TOTAL_TEST_COUNT, LATENCY_TEST_COUNT, THROUGHPUT_TEST_COUNT;
#endif"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.h"), "w") as f:
            f.write(h)
    
    @staticmethod
    def generate_test_suite_c(entries_l, entries_t):
        all_entries = entries_l + entries_t
        entries_str = ",\n".join(all_entries)
        c = f"""#include <stdio.h>
#include <string.h>
#include <math.h>
#include "esp32c6_test_suite.h"
#include "test_result.h"
#include "esp_task_wdt.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

const int LATENCY_TEST_COUNT = {len(entries_l)};
const int THROUGHPUT_TEST_COUNT = {len(entries_t)};
const int TOTAL_TEST_COUNT = {len(all_entries)};

typedef struct {{
    const char* name; test_func_t func; int iterations; int instruction_count;
    const char* description; const char* category; const char* type;
    int test_value; const char* value_type;
}} test_entry_t;

static const test_entry_t all_tests[] = {{
{entries_str}
}};
#define NUM_TESTS (sizeof(all_tests)/sizeof(all_tests[0]))

void init_performance_counters(void) {{
    __asm__ __volatile__ ("li a2, 1\\ncsrw 0x7E0, a2\\ncsrw 0x7E1, a2\\n" ::: "a2");
}}

void run_latency_single_tests(void) {{
    printf("\\n--- Single Instruction Latency ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && strstr(all_tests[i].category,"SINGLE"))
            printf("%s: %.2f cycles\\n", all_tests[i].name, all_tests[i].func.as_result().mean);
}}

void run_latency_sequence_tests(void) {{
    printf("\\n--- Sequence Latency Tests ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && (strstr(all_tests[i].category,"CHAIN")||strstr(all_tests[i].category,"SEQUENCE")))
            printf("%s: %.2f cycles (CPI: %.2f)\\n", all_tests[i].name, all_tests[i].func.as_result().mean, all_tests[i].func.as_result().cpi);
}}

void run_latency_multi_tests(void) {{
    printf("\\n--- Multi Instruction Latency ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && (strstr(all_tests[i].category,"MULTI")||all_tests[i].instruction_count>=10))
            printf("%s (%d ops): %.2f cycles (CPI: %.2f)\\n", all_tests[i].name, all_tests[i].instruction_count, all_tests[i].func.as_result().mean, all_tests[i].func.as_result().cpi);
}}

void run_all_latency_tests(void) {{
    printf("\\n=== LATENZ (%d Tests) ===\\n", LATENCY_TEST_COUNT);
    printf("%-30s %-10s %-10s %-8s %-8s %-10s %s\\n","Test","Mean","StdDev","Min","Max","CI95%%","Rel%%");
    float total=0;
    for (int i=0; i<NUM_TESTS; i++) if (!strcmp(all_tests[i].type,"latency")) {{
        test_result_t r = all_tests[i].func.as_result();
        total += r.mean / all_tests[i].iterations / all_tests[i].instruction_count;
        printf("%-30s %-10.2f %-10.2f %-8.0f %-8.0f %-10.2f %-8.1f\\n", all_tests[i].name, r.mean, r.stddev, r.min, r.max, r.ci, r.rel_error);
    }}
    printf("Avg latency per instr: %.2f cycles\\n", total/LATENCY_TEST_COUNT);
}}

void run_throughput_base_tests(void) {{
    printf("\\n--- Base Throughput ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"throughput") && strstr(all_tests[i].category,"BASE"))
            printf("%s: CPI = %.3f\\n", all_tests[i].name, all_tests[i].func.as_result().cpi);
}}

void run_throughput_divider_tests(void) {{
    printf("\\n--- Divider Throughput ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"throughput") && strstr(all_tests[i].category,"DIVIDER"))
            printf("%s (Wert=%d, %s): CPI = %.3f\\n", all_tests[i].name, all_tests[i].test_value, all_tests[i].value_type, all_tests[i].func.as_result().cpi);
}}

void run_throughput_comparison_tests(void) {{
    printf("\\n--- Throughput Comparison ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"throughput") && strstr(all_tests[i].category,"COMPARE"))
            printf("%s: CPI = %.3f\\n", all_tests[i].name, all_tests[i].func.as_result().cpi);
}}

void run_all_throughput_tests(void) {{
    printf("\\n=== DURCHSATZ (%d Tests) ===\\n", THROUGHPUT_TEST_COUNT);
    printf("%-30s %-10s %-10s %-10s %s\\n","Test","CPI","StdDev","CI95%%","Rel%%");
    float total_cpi=0;
    for (int i=0; i<NUM_TESTS; i++) if (!strcmp(all_tests[i].type,"throughput")) {{
        test_result_t r = all_tests[i].func.as_result();
        total_cpi += r.cpi;
        printf("%-30s %-10.3f %-10.3f %-10.3f %-8.1f\\n", all_tests[i].name, r.cpi, r.stddev, r.ci, r.rel_error);
    }}
    printf("Average CPI: %.3f\\n", total_cpi/THROUGHPUT_TEST_COUNT);
}}

void run_all_tests(void) {{ run_all_latency_tests(); run_all_throughput_tests(); }}

void compare_latency_throughput(void) {{
    printf("\\n=== VERGLEICH Latenz vs Durchsatz ===\\n");
    printf("%-20s %-12s %-12s %-12s\\n","Wert","Latenz CPI","Durchsatz CPI","Ratio");
    for (int v=0; v<NUM_TESTS; v++) if (all_tests[v].test_value>0) {{
        int val = all_tests[v].test_value;
        float lcpi=0, tcpi=0; int fl=0, ft=0;
        for (int i=0; i<NUM_TESTS; i++) if (all_tests[i].test_value==val) {{
            test_result_t r = all_tests[i].func.as_result();
            if (!strcmp(all_tests[i].type,"latency") && !fl) {{ lcpi=r.cpi; fl=1; }}
            if (!strcmp(all_tests[i].type,"throughput") && !ft) {{ tcpi=r.cpi; ft=1; }}
        }}
        if (fl&&ft) printf("%-20d %-12.3f %-12.3f %-12.3f\\n", val, lcpi, tcpi, tcpi/lcpi);
    }}
}}"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.c"), "w") as f:
            f.write(c)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--latency-only', action='store_true')
    parser.add_argument('--throughput-only', action='store_true')
    args = parser.parse_args()
    
    print("\n" + "="*60 + "\n  ESP32-C6 TEST GENERATOR\n" + "="*60)
    
    latency_tests = [] if args.throughput_only else TestCollector.collect_latency_tests()
    throughput_tests = [] if args.latency_only else TestCollector.collect_throughput_tests()
    
    print(f"\n📊 GESAMT: {len(latency_tests) + len(throughput_tests)} Tests")
    print("\n📁 Generiere Dateien...")
    
    os.makedirs(MAIN_DIR, exist_ok=True); os.makedirs(TESTS_DIR, exist_ok=True)
    
    entries_l, entries_t, includes, files_l, files_t = [], [], [], [], []
    
    if latency_tests:
        LatencyFileGenerator.ensure_directories()
        files_l = LatencyFileGenerator.generate_files(latency_tests, entries_l, includes)
    
    if throughput_tests:
        ThroughputFileGenerator.ensure_directories()
        files_t = ThroughputFileGenerator.generate_files(throughput_tests, entries_t, includes)
    
    MasterFileGenerator.generate_test_result_h()
    MasterFileGenerator.generate_test_suite_h(includes)
    MasterFileGenerator.generate_test_suite_c(entries_l, entries_t)
    MasterFileGenerator.generate_main_c()
    MasterFileGenerator.generate_cmakelists(files_l, files_t)
    
    print("\n" + "="*60 + "\n  GENERIERUNG ABGESCHLOSSEN!\n" + "="*60)
    print(f"\n📊 STATISTIK: Latenz: {len(latency_tests)}, Durchsatz: {len(throughput_tests)}, Gesamt: {len(latency_tests)+len(throughput_tests)}")
    print("\n📋 Nächste Schritte: idf.py clean && idf.py build && idf.py -p PORT flash monitor")

if __name__ == "__main__":
    random.seed(42)
    main()