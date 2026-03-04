#!/usr/bin/env python3
# scripts/base/code_generator.py - KORRIGIERTE VERSION für Load/Store Tests mit nur 2 Iterationen

from typing import Tuple

def generate_test_function(test: dict, test_type: str = "latency") -> Tuple[str, str]:
    """
    Generiert C-Code mit optimierter Register-Nutzung und Cache-Warmup.
    Für ESP32-C6: Nur 2 Iterationen pro Test.
    """
    
    func_name = f"test_{test['safe_name']}"
    
    instruction_lines = []
    for i, (insn_name, operands) in enumerate(test["instructions"]):
        if i > 0 and test_type == "latency":
            instruction_lines.append(f'            // RAW: {test["instructions"][i-1][1].split()[1]} → {operands.split()[1]}\n')
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    # FIX: Für ESP32-C6 nur 2 Iterationen
    iterations = 2
    
    test_value = test.get("test_value", -1)
    value_type = test.get("value_type", "NONE")
    
    # Prüfe ob Load/Store Tests
    is_load_store = any(insn[0] in ['lb','lh','lw','lbu','lhu','sb','sh','sw'] 
                       for insn in test["instructions"])
    
    # Für Load/Store-Tests - SPEZIALBEHANDLUNG!
    if is_load_store:
        if test_type == "throughput":
            return generate_throughput_loadstore_function(func_name, test, instruction_block,
                                                         iterations, test_value, value_type)
        else:
            return generate_loadstore_test_function(func_name, test, instruction_block,
                                                   iterations, test_value, value_type)
    
    # Für normale Throughput-Tests (keine Load/Store)
    if test_type == "throughput":
        return generate_throughput_test_function(func_name, test, instruction_block,
                                                iterations, test_value, value_type)
    
    # Für normale Latency-Tests
    return generate_latency_test_function(func_name, test, instruction_block,
                                         iterations, test_value, value_type)


def generate_loadstore_test_function(func_name: str, test: dict, instruction_block: str,
                                    iterations: int, test_value, value_type) -> Tuple[str, str]:
    """
    SPEZIELLE VERSION FÜR LATENCY LOAD/STORE-TESTS mit Cache-Warmup.
    Für ESP32-C6: Nur 2 Iterationen, erste wird verworfen.
    """
    
    # Bestimme welche Register tatsächlich in den Instruktionen verwendet werden
    used_regs = set()
    base_registers = set()  # Speziell für Base-Pointer
    
    for _, operands in test["instructions"]:
        parts = operands.replace(',', '').split()
        # Die Base-Register sind die letzten in Load/Store Instruktionen
        if '(' in operands and ')' in operands:
            # Extrahiere Base-Register aus z.B. "lb t0, 0(s0)"
            base_part = operands.split('(')[1].split(')')[0]
            if base_part:
                base_registers.add(base_part)
        
        for part in parts:
            if part in ['t0','t1','t2','t3','t4','t5','t6',
                       'a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    # Stelle sicher, dass ALLE Base-Pointer initialisiert werden!
    for base_reg in base_registers:
        used_regs.add(base_reg)
    
    # Clobber-Liste
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    # Buffer mit Werten
    buffer_decl = """    
    // Safe buffer in RAM - für Load/Store Tests
    static uint32_t safe_buffer[128] __attribute__((aligned(64))) = {
        [0]  = 0x11111111, [1]  = 0x22222222, [2]  = 0x33333333, [3]  = 0x44444444,
        [4]  = 0x55555555, [5]  = 0x66666666, [6]  = 0x77777777, [7]  = 0x88888888,
        [8]  = 0x99999999, [9]  = 0xAAAAAAAA, [10] = 0xBBBBBBBB, [11] = 0xCCCCCCCC,
        [12] = 0xDDDDDDDD, [13] = 0xEEEEEEEE, [14] = 0xFFFFFFFF, [15] = 0x12345678,
        [16] = 0x11111111, [17] = 0x22222222, [18] = 0x33333333, [19] = 0x44444444,
        [20] = 0x55555555, [21] = 0x66666666, [22] = 0x77777777, [23] = 0x88888888,
        [24] = 0x99999999, [25] = 0xAAAAAAAA, [26] = 0xBBBBBBBB, [27] = 0xCCCCCCCC,
        [28] = 0xDDDDDDDD, [29] = 0xEEEEEEEE, [30] = 0xFFFFFFFF, [31] = 0x87654321,
    };
    
    // Zeiger auf safe_buffer für Base-Register
    uint32_t * const base_ptr = safe_buffer;"""
    
    # Basis-Pointer - ALLE Base-Register initialisieren!
    reg_init_code = [
        '    uint32_t base_ptr_val = (uint32_t)safe_buffer;',
        '    uint32_t safe_buffer_addr = (uint32_t)safe_buffer;',
    ]
    
    # Für jedes verwendete Base-Register einen Wert erzeugen
    for base_reg in sorted(base_registers):
        if base_reg in ['s0', 's1', 's2']:
            offset = 0
            if base_reg == 's1':
                offset = 16
            elif base_reg == 's2':
                offset = 32
            reg_init_code.append(f'    uint32_t {base_reg}_val = (uint32_t)safe_buffer + {offset};')
        elif base_reg in ['a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']:
            reg_init_code.append(f'    uint32_t {base_reg}_val = (uint32_t)safe_buffer;')
        else:
            reg_init_code.append(f'    uint32_t {base_reg}_val = (uint32_t)safe_buffer;')
    
    # Work-Register
    work_regs = ['t0', 't1', 't2', 't3', 't4', 't5', 't6']
    for reg in work_regs:
        if reg in used_regs and reg not in base_registers:
            reg_init_code.append(f'    uint32_t {reg}_val = 0x{reg[1]}1111111;')
    
    # Load-Register-Code - ALLE Base-Register laden!
    load_regs_lines = ['            // Basis-Register laden']
    
    for base_reg in sorted(base_registers):
        load_regs_lines.append(f'            "mv {base_reg}, %[{base_reg}_val]\\n"')
    
    # Work-Register laden
    for reg in sorted(used_regs):
        if reg not in base_registers and reg in work_regs:
            load_regs_lines.append(f'            "mv {reg}, %[{reg}_val]\\n"')
    
    load_regs_str = '\n'.join(load_regs_lines)
    
    # Input-Liste - ALLE Werte
    input_list = []
    for base_reg in sorted(base_registers):
        input_list.append(f'[{base_reg}_val] "r"({base_reg}_val)')
    
    for reg in sorted(used_regs):
        if reg not in base_registers and reg in work_regs:
            input_list.append(f'[{reg}_val] "r"({reg}_val)')
    
    inputs_str = ',\n            '.join(input_list) if input_list else ""
    reg_init_str = '\n'.join(reg_init_code)
    
    # Cache-Warmup Block - Reduziert auf 2 Warmup-Durchläufe
    warmup_code = f"""
    // =======================================================
    // CACHE WARMUP - 2 Warmup-Durchläufe ohne Messung
    // =======================================================
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs_str}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : : {inputs_str} : {clobber_str}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    
    // Kurze Pause nach Warmup
    vTaskDelay(pdMS_TO_TICKS(1));
"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen - Nur 2 Iterationen
    uint32_t measurements[2];
    {buffer_decl}
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    
{reg_init_str}
    
    // =======================================================
    // CACHE WARMUP
    // =======================================================
{warmup_code}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    uint32_t cycles = 0;
    
    // FIX: Nur 2 Iterationen, erste wird verworfen
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog bei jeder Iteration füttern
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
{load_regs_str}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs_str}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        
        
        // Erste Iteration (iter=0) wird verworfen, zweite (iter=1) wird gespeichert
        if (iter > 0) {{
            cycles = t_end - t_start - 1; // Korrektur für Overhead
            measurements[0] = cycles;  // Nur eine Messung speichern
            total_cycles = cycles;
            result.min = cycles;
            result.max = cycles;
        }}
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN - Für eine einzelne Messung
    // =======================================================
    
    result.mean = (float)total_cycles;
    result.stddev = 0.0f;  // Keine Standardabweichung bei einer Messung
    result.ci = 0.0f;       // Kein Konfidenzintervall
    result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_throughput_loadstore_function(func_name: str, test: dict, instruction_block: str,
                                          iterations: int, test_value, value_type) -> Tuple[str, str]:
    """
    SPEZIELLE VERSION FÜR THROUGHPUT LOAD/STORE-TESTS mit Cache-Warmup.
    Für ESP32-C6: Nur 2 Iterationen, erste wird verworfen.
    """
    
    # Extrahiere Base-Register
    base_registers = set()
    for _, operands in test["instructions"]:
        if '(' in operands and ')' in operands:
            base_part = operands.split('(')[1].split(')')[0]
            if base_part:
                base_registers.add(base_part)
    
    # Minimale Register für Throughput Load/Store
    clobber_list = ['"t0"', '"t1"', '"t2"', '"a2"', '"a4"', '"a5"', '"memory"']
    for base_reg in base_registers:
        clobber_list.append(f'"{base_reg}"')
    clobber_str = ', '.join(clobber_list)
    
    # Buffer mit initialisierten Werten
    buffer_decl = """    
    // Safe buffer in RAM - für Load/Store Tests
    static uint32_t safe_buffer[128] __attribute__((aligned(64))) = {
        [0]  = 0x11111111, [1]  = 0x22222222, [2]  = 0x33333333, [3]  = 0x44444444,
        [4]  = 0x55555555, [5]  = 0x66666666, [6]  = 0x77777777, [7]  = 0x88888888,
        [8]  = 0x99999999, [9]  = 0xAAAAAAAA, [10] = 0xBBBBBBBB, [11] = 0xCCCCCCCC,
        [12] = 0xDDDDDDDD, [13] = 0xEEEEEEEE, [14] = 0xFFFFFFFF, [15] = 0x12345678,
        [16] = 0x11111111, [17] = 0x22222222, [18] = 0x33333333, [19] = 0x44444444,
        [20] = 0x55555555, [21] = 0x66666666, [22] = 0x77777777, [23] = 0x88888888,
        [24] = 0x99999999, [25] = 0xAAAAAAAA, [26] = 0xBBBBBBBB, [27] = 0xCCCCCCCC,
        [28] = 0xDDDDDDDD, [29] = 0xEEEEEEEE, [30] = 0xFFFFFFFF, [31] = 0x87654321,
    };
    
    uint32_t *safe_buffer_ptr = safe_buffer;"""
    
    # Einfache Register-Initialisierung
    reg_init_lines = [
        '    uint32_t t0_val = 0x11111111;',
        '    uint32_t t1_val = 0x22222222;',
        '    uint32_t t2_val = 0x33333333;',
        '    uint32_t a2_val = 0xAAAAAAAA;',
        '    uint32_t a4_val = 0xBBBBBBBB;',
        '    uint32_t a5_val = 0xCCCCCCCC;',
        '    uint32_t safe_ptr = (uint32_t)safe_buffer;',
    ]
    
    for base_reg in base_registers:
        offset = 0
        if base_reg == 's1':
            offset = 16
        elif base_reg == 's2':
            offset = 32
        reg_init_lines.append(f'    uint32_t {base_reg}_val = (uint32_t)safe_buffer + {offset};')
    
    reg_init = '\n'.join(reg_init_lines)
    
    # Load-Register-Code
    load_regs_lines = []
    for base_reg in base_registers:
        load_regs_lines.append(f'            "mv {base_reg}, %[{base_reg}_val]\\n"')
    
    load_regs_lines.extend([
        '            "mv t0, %[t0_val]\\n"',
        '            "mv t1, %[t1_val]\\n"',
        '            "mv t2, %[t2_val]\\n"',
        '            "mv a2, %[a2_val]\\n"',
        '            "mv a4, %[a4_val]\\n"',
        '            "mv a5, %[a5_val]\\n"',
    ])
    
    load_regs = '\n'.join(load_regs_lines)
    
    # Input-Liste
    input_list = []
    for base_reg in base_registers:
        input_list.append(f'[{base_reg}_val] "r"({base_reg}_val)')
    
    input_list.extend([
        '[t0_val] "r"(t0_val)',
        '[t1_val] "r"(t1_val)',
        '[t2_val] "r"(t2_val)',
        '[a2_val] "r"(a2_val)',
        '[a4_val] "r"(a4_val)',
        '[a5_val] "r"(a5_val)',
    ])
    
    inputs = ',\n            '.join(input_list)
    
    # Cache-Warmup Block - Reduziert auf 2 Warmup-Durchläufe
    warmup_code = f"""
    // =======================================================
    // CACHE WARMUP - 2 Warmup-Durchläufe ohne Messung
    // =======================================================
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
            {load_regs}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : : {inputs} : {clobber_str}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    
    vTaskDelay(pdMS_TO_TICKS(1));
"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen - Nur 2 Iterationen
    uint32_t measurements[2];
    {buffer_decl}
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    {reg_init}
    
    // =======================================================
    // CACHE WARMUP
    // =======================================================
{warmup_code}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    uint32_t cycles = 0;
    
    // FIX: Nur 2 Iterationen, erste wird verworfen
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog bei jeder Iteration füttern
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            // Register mit Testwerten laden
            {load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        // Erste Iteration (iter=0) wird verworfen, zweite (iter=1) wird gespeichert
        if (iter > 0) {{
            cycles = t_end - t_start - 1; // Korrektur für Overhead
            measurements[0] = cycles;  // Nur eine Messung speichern
            total_cycles = cycles;
            result.min = cycles;
            result.max = cycles;
        }}
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN - Für eine einzelne Messung
    // =======================================================
    
    result.mean = (float)total_cycles;
    result.stddev = 0.0f;
    result.ci = 0.0f;
    result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_latency_test_function(func_name: str, test: dict, instruction_block: str,
                                  iterations: int, test_value, value_type) -> Tuple[str, str]:
    """Generiert Code für Latency-Tests (keine Load/Store) mit Cache-Warmup.
       Für ESP32-C6: Nur 2 Iterationen, erste wird verworfen."""
    
    # Bestimme welche Register verwendet werden
    used_regs = set()
    for _, operands in test["instructions"]:
        parts = operands.replace(',', '').split()
        for part in parts:
            if part in ['t0','t1','t2','t3','t4','t5','t6',
                       'a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    # Für lange Ketten: Reduziere die Register
    if len(test["instructions"]) > 10:
        important_regs = {'t0', 't1', 't2', 'a2', 'a4', 'a5', 's0'}
        used_regs = used_regs.intersection(important_regs)
    
    # Clobber-Liste
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    # Register-Initialisierung
    reg_init_code = []
    
    reg_values = {
        't0': '0x11111111', 't1': '0x22222222', 't2': '0x33333333',
        't3': '0x44444444', 't4': '0x55555555', 't5': '0x66666666',
        't6': '0x77777777',
        'a0': '0x88888888', 'a1': '0x99999999', 'a2': '0xAAAAAAAA',
        'a3': '0x12345678',  # Dummy für a3
        'a4': '0xBBBBBBBB', 'a5': '0xCCCCCCCC', 'a6': '0xDDDDDDDD',
        'a7': '0xEEEEEEEE',
        's0': '0x11111111', 's1': '0x22222222', 's2': '0x33333333',
        's3': '0x01010101', 's4': '0x02020202', 's5': '0x03030303',
        's6': '0x04040404', 's7': '0x05050505', 's8': '0x06060606',
        's9': '0x07070707', 's10': '0x08080808', 's11': '0x09090909',
    }
    
    for reg, val in reg_values.items():
        if reg in used_regs:
            reg_init_code.append(f'    uint32_t {reg}_val = {val};')
    
    # Load-Register-Code
    load_regs_code = []
    for reg in sorted(used_regs):
        if reg in reg_values:
            load_regs_code.append(f'            "mv {reg}, %[{reg}_val]\\n"')
    
    load_regs_str = ''.join(load_regs_code)
    
    # Input-Liste
    input_list = []
    for reg in sorted(used_regs):
        if reg in reg_values:
            input_list.append(f'[{reg}_val] "r"({reg}_val)')
    
    inputs_str = ',\n            '.join(input_list) if input_list else ""
    reg_init_str = '\n'.join(reg_init_code)
    
    # Cache-Warmup Block - Reduziert auf 2 Warmup-Durchläufe
    warmup_code = f"""
    // =======================================================
    // CACHE WARMUP - 2 Warmup-Durchläufe ohne Messung
    // =======================================================
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs_str}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : : {inputs_str} : {clobber_str}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    
    vTaskDelay(pdMS_TO_TICKS(1));
"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen - Nur 2 Iterationen
    uint32_t measurements[2];
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    
{reg_init_str}
    
    // =======================================================
    // CACHE WARMUP
    // =======================================================
{warmup_code}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    uint32_t cycles = 0;
    
    // FIX: Nur 2 Iterationen, erste wird verworfen
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog bei jeder Iteration füttern
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            // Register mit Testwerten laden
{load_regs_str}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs_str}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        // Erste Iteration (iter=0) wird verworfen, zweite (iter=1) wird gespeichert
        if (iter > 0) {{
            cycles = t_end - t_start - 1; // Korrektur für Overhead
            measurements[0] = cycles;  // Nur eine Messung speichern
            total_cycles = cycles;
            result.min = cycles;
            result.max = cycles;
        }}
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN - Für eine einzelne Messung
    // =======================================================
    
    result.mean = (float)total_cycles;
    result.stddev = 0.0f;
    result.ci = 0.0f;
    result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_throughput_test_function(func_name: str, test: dict, instruction_block: str,
                                     iterations: int, test_value, value_type) -> Tuple[str, str]:
    """
    Spezielle Version für normale Throughput-Tests (keine Load/Store) mit Cache-Warmup.
    Für ESP32-C6: Nur 2 Iterationen, erste wird verworfen.
    """
    
    # Minimale Register für Throughput
    clobber_list = ['"t0"', '"t1"', '"t2"', '"a2"', '"a4"', '"a5"', '"memory"']
    clobber_str = ', '.join(clobber_list)
    
    # Einfache Register-Initialisierung
    reg_init = """
    uint32_t t0_val = 0x11111111;
    uint32_t t1_val = 0x22222222;
    uint32_t t2_val = 0x33333333;
    uint32_t a2_val = 0xAAAAAAAA;
    uint32_t a4_val = 0xBBBBBBBB;
    uint32_t a5_val = 0xCCCCCCCC;
"""
    
    # Load-Register-Code
    load_regs = """
            "mv t0, %[t0_val]\\n"
            "mv t1, %[t1_val]\\n"
            "mv t2, %[t2_val]\\n"
            "mv a2, %[a2_val]\\n"
            "mv a4, %[a4_val]\\n"
            "mv a5, %[a5_val]\\n"
"""
    
    # Input-Liste
    inputs = """[t0_val] "r"(t0_val), [t1_val] "r"(t1_val), [t2_val] "r"(t2_val),
            [a2_val] "r"(a2_val),
            [a4_val] "r"(a4_val), [a5_val] "r"(a5_val)"""
    
    # Cache-Warmup Block - Reduziert auf 2 Warmup-Durchläufe
    warmup_code = f"""
    // =======================================================
    // CACHE WARMUP - 2 Warmup-Durchläufe ohne Messung
    // =======================================================
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
            {load_regs}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : : {inputs} : {clobber_str}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    
    vTaskDelay(pdMS_TO_TICKS(1));
"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen - Nur 2 Iterationen
    uint32_t measurements[2];
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    {reg_init}
    
    // =======================================================
    // CACHE WARMUP
    // =======================================================
{warmup_code}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    uint32_t cycles = 0;
    
    // FIX: Nur 2 Iterationen, erste wird verworfen
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog bei jeder Iteration füttern
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            // Register mit Testwerten laden
            {load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        // Erste Iteration (iter=0) wird verworfen, zweite (iter=1) wird gespeichert
       if (iter > 0) {{
            cycles = t_end - t_start - 1; // Korrektur für Overhead
            measurements[0] = cycles;  // Nur eine Messung speichern
            total_cycles = cycles;
            result.min = cycles;
            result.max = cycles;
        }}
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN - Für eine einzelne Messung
    // =======================================================
    
    result.mean = (float)total_cycles;
    result.stddev = 0.0f;
    result.ci = 0.0f;
    result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_header_content(test: dict, func_name: str) -> str:
    """Generiert den Inhalt einer Header-Datei für einen Test."""
    header_guard = f"TEST_{test['safe_name'].upper()}_H"
    
    return f"""#ifndef {header_guard}
#define {header_guard}

#include "../../main/test_result.h"

test_result_t {func_name}(void);

#endif /* {header_guard} */
"""


def generate_c_file_content(test: dict, func_code: str) -> str:
    """Generiert den Inhalt einer C-Datei für einen Test."""
    return f"""#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_test_suite.h"
#include "../../main/test_result.h"

extern portMUX_TYPE test_mutex;

{func_code}
"""