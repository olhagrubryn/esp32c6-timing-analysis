#!/usr/bin/env python3
# scripts/base/code_generator.py - Optimierte Version

from typing import Tuple

def generate_test_function(test: dict, test_type: str = "latency") -> Tuple[str, str]:
    """Generiert C-Code mit optimierter Register-Nutzung und Cache-Warmup."""
    
    func_name = f"test_{test['safe_name']}"
    
    instruction_lines = []
    for i, (insn_name, operands) in enumerate(test["instructions"]):
        if i > 0 and test_type == "latency":
            instruction_lines.append(f'            // RAW: {test["instructions"][i-1][1].split()[1]} → {operands.split()[1]}\n')
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    is_load_store = any(insn[0] in ['lb','lh','lw','lbu','lhu','sb','sh','sw'] 
                       for insn in test["instructions"])
    
    if is_load_store:
        if test_type == "throughput":
            return generate_throughput_loadstore_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))
        return generate_loadstore_test_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))
    
    if test_type == "throughput":
        return generate_throughput_test_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))
    
    return generate_latency_test_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))


def generate_loadstore_test_function(func_name: str, test: dict, instruction_block: str,
                                    test_value, value_type) -> Tuple[str, str]:
    """
    SPEZIELLE VERSION FÜR LATENCY LOAD/STORE-TESTS mit Cache-Warmup.
    FIXED: Keine doppelten Variablendefinitionen!
    """
    
    # Bestimme welche Register tatsächlich in den Instruktionen verwendet werden
    used_regs = set()
    base_registers = set()
    
    for _, operands in test["instructions"]:
        parts = operands.replace(',', '').split()
        # Die Base-Register sind die letzten in Load/Store Instruktionen
        if '(' in operands and ')' in operands:
            # Extrahiere Base-Register aus z.B. "lb t0, 0(s0)"
            base_part = operands.split('(')[1].split(')')[0]
            if base_part:
                base_registers.add(base_part)
                used_regs.add(base_part)
        
        for part in parts:
            if part in ['t0','t1','t2','t3','t4','t5','t6',
                       'a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    # Clobber-Liste
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    # Buffer mit Werten - OHNE safe_buffer_addr!
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
    
    # Basis-Pointer Initialisierung - NUR HIER definieren, nicht im buffer_decl!
    reg_init_code = [
        '    uint32_t safe_buffer_addr = (uint32_t)safe_buffer;',
    ]
    
    # Für jedes verwendete Base-Register einen Wert erzeugen
    for base_reg in sorted(base_registers):
        reg_init_code.append(f'    uint32_t {base_reg}_val = safe_buffer_addr;')
    
    # Work-Register (für Daten)
    work_regs = ['t0', 't1', 't2', 't3', 't4', 't5', 't6']
    for reg in work_regs:
        if reg in used_regs and reg not in base_registers:
            reg_init_code.append(f'    uint32_t {reg}_val = 0x{reg[1]}1111111;')
    
    # Load-Register-Code
    load_regs_lines = ['            // Basis-Register laden']
    
    for base_reg in sorted(base_registers):
        load_regs_lines.append(f'            "mv {base_reg}, %[{base_reg}_val]\\n"')
    
    for reg in sorted(used_regs):
        if reg not in base_registers and reg in work_regs:
            load_regs_lines.append(f'            "mv {reg}, %[{reg}_val]\\n"')
    
    load_regs_str = '\n'.join(load_regs_lines)
    
    # Input-Liste
    input_list = []
    for base_reg in sorted(base_registers):
        input_list.append(f'[{base_reg}_val] "r"({base_reg}_val)')
    
    for reg in sorted(used_regs):
        if reg not in base_registers and reg in work_regs:
            input_list.append(f'[{reg}_val] "r"({reg}_val)')
    
    inputs_str = ',\n            '.join(input_list) if input_list else ""
    reg_init_str = '\n'.join(reg_init_code)
    
    # Cache-Warmup Block
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
    result.stddev = 0.0f;
    result.ci = 0.0f;
    result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_throughput_loadstore_function(func_name: str, test: dict, instruction_block: str, test_value, value_type) -> Tuple[str, str]:
    """Throughput Load/Store Tests."""
    
    base_regs = set()
    for _, operands in test["instructions"]:
        if '(' in operands and ')' in operands:
            base_regs.add(operands.split('(')[1].split(')')[0])
    
    clobber = ['"t0"','"t1"','"t2"','"a2"','"a4"','"a5"','"memory"'] + [f'"{r}"' for r in base_regs]
    
    buffer = """
    static uint32_t safe_buffer[128] __attribute__((aligned(64))) = {
        [0]=0x11111111,[1]=0x22222222,[2]=0x33333333,[3]=0x44444444,
        [4]=0x55555555,[5]=0x66666666,[6]=0x77777777,[7]=0x88888888,
        [8]=0x99999999,[9]=0xAAAAAAAA,[10]=0xBBBBBBBB,[11]=0xCCCCCCCC,
        [12]=0xDDDDDDDD,[13]=0xEEEEEEEE,[14]=0xFFFFFFFF,[15]=0x12345678,
    };
    uint32_t *safe_buffer_ptr = safe_buffer;"""
    
    reg_init = ['    uint32_t t0_val=0x11111111, t1_val=0x22222222, t2_val=0x33333333;',
                '    uint32_t a2_val=0xAAAAAAAA, a4_val=0xBBBBBBBB, a5_val=0xCCCCCCCC;',
                '    uint32_t safe_ptr=(uint32_t)safe_buffer;']
    
    for base in base_regs:
        offset = 16 if base=='s1' else 32 if base=='s2' else 0
        reg_init.append(f'    uint32_t {base}_val = (uint32_t)safe_buffer + {offset};')
    
    load_regs = ''.join([f'            "mv {base}, %[{base}_val]\\n"' for base in base_regs] +
                        ['            "mv t0, %[t0_val]\\n"', '"mv t1, %[t1_val]\\n"', '"mv t2, %[t2_val]\\n"',
                         '"mv a2, %[a2_val]\\n"', '"mv a4, %[a4_val]\\n"', '"mv a5, %[a5_val]\\n"'])
    
    inputs = [f'[{base}_val] "r"({base}_val)' for base in base_regs] + \
             ['[t0_val] "r"(t0_val)','[t1_val] "r"(t1_val)','[t2_val] "r"(t2_val)',
              '[a2_val] "r"(a2_val)','[a4_val] "r"(a4_val)','[a5_val] "r"(a5_val)']
    
    warmup = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ ({load_regs}"fence\\n"
{instruction_block}            "fence\\n"
            : : {', '.join(inputs)} : {', '.join(clobber)}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));"""
    
    func = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    uint32_t measurements[2];
    {buffer}
    
{chr(10).join(reg_init)}
{warmup}
    
    result.min = 999999999; result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ ({load_regs}"fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {', '.join(inputs)}
            : {', '.join(clobber)}
        );
        portEXIT_CRITICAL(&test_mutex);
        
        if (iter > 0) {{
            cycles = t_end - t_start - 1;
            result.min = result.max = result.mean = cycles;
        }}
    }}
    
    result.stddev = result.ci = result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    return result;
}}"""
    return func_name, func


def generate_latency_test_function(func_name: str, test: dict, instruction_block: str, test_value, value_type) -> Tuple[str, str]:
    """Latency Tests (non load/store)."""
    
    used_regs = set()
    for _, operands in test["instructions"]:
        for part in operands.replace(',', '').split():
            if part in ['t0','t1','t2','t3','t4','t5','t6','a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    if len(test["instructions"]) > 10:
        used_regs = used_regs.intersection({'t0','t1','t2','a2','a4','a5','s0'})
    
    values = {
        't0':'0x11111111','t1':'0x22222222','t2':'0x33333333','t3':'0x44444444',
        't4':'0x55555555','t5':'0x66666666','t6':'0x77777777','a0':'0x88888888',
        'a1':'0x99999999','a2':'0xAAAAAAAA','a3':'0x12345678','a4':'0xBBBBBBBB',
        'a5':'0xCCCCCCCC','a6':'0xDDDDDDDD','a7':'0xEEEEEEEE','s0':'0x11111111',
        's1':'0x22222222','s2':'0x33333333','s3':'0x01010101','s4':'0x02020202',
        's5':'0x03030303','s6':'0x04040404','s7':'0x05050505','s8':'0x06060606',
        's9':'0x07070707','s10':'0x08080808','s11':'0x09090909',
    }
    
    reg_init = [f'    uint32_t {reg}_val = {values[reg]};' for reg in sorted(used_regs) if reg in values]
    load_regs = ''.join([f'            "mv {reg}, %[{reg}_val]\\n"' for reg in sorted(used_regs) if reg in values])
    inputs = [f'[{reg}_val] "r"({reg}_val)' for reg in sorted(used_regs) if reg in values]
    clobber = ', '.join([f'"{reg}"' for reg in sorted(used_regs)]) + ', "memory"'
    
    warmup = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs}            "fence\\n"
{instruction_block}            "fence\\n"
            : : {', '.join(inputs)} : {clobber}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));"""
    
    func = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    uint32_t measurements[2];
    
{chr(10).join(reg_init)}
{warmup}
    
    result.min = 999999999; result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs}            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {', '.join(inputs)}
            : {clobber}
        );
        portEXIT_CRITICAL(&test_mutex);
        
        if (iter > 0) {{
            cycles = t_end - t_start - 1;
            result.min = result.max = result.mean = cycles;
        }}
    }}
    
    result.stddev = result.ci = result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    return result;
}}"""
    return func_name, func


def generate_throughput_test_function(func_name: str, test: dict, instruction_block: str, test_value, value_type) -> Tuple[str, str]:
    """Throughput Tests (non load/store)."""
    
    clobber = '"t0","t1","t2","a2","a4","a5","memory"'
    reg_init = """
    uint32_t t0_val = 0x11111111;
    uint32_t t1_val = 0x22222222;
    uint32_t t2_val = 0x33333333;
    uint32_t a2_val = 0xAAAAAAAA;
    uint32_t a4_val = 0xBBBBBBBB;
    uint32_t a5_val = 0xCCCCCCCC;
"""
    load_regs = """
            "mv t0, %[t0_val]\\n"
            "mv t1, %[t1_val]\\n"
            "mv t2, %[t2_val]\\n"
            "mv a2, %[a2_val]\\n"
            "mv a4, %[a4_val]\\n"
            "mv a5, %[a5_val]\\n"
"""
    inputs = '[t0_val] "r"(t0_val), [t1_val] "r"(t1_val), [t2_val] "r"(t2_val), [a2_val] "r"(a2_val), [a4_val] "r"(a4_val), [a5_val] "r"(a5_val)'
    
    warmup = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ ({load_regs}"fence\\n"
{instruction_block}            "fence\\n"
            : : {inputs} : {clobber}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));"""
    
    func = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    uint32_t measurements[2];
    {reg_init}
{warmup}
    
    result.min = 999999999; result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ ({load_regs}"fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs}
            : {clobber}
        );
        portEXIT_CRITICAL(&test_mutex);
        
        if (iter > 0) {{
            cycles = t_end - t_start - 1;
            result.min = result.max = result.mean = cycles;
        }}
    }}
    
    result.stddev = result.ci = result.rel_error = 0.0f;
    result.cpi = result.mean / (float){test['instruction_count']};
    return result;
}}"""
    return func_name, func


def generate_header_content(test: dict, func_name: str) -> str:
    """Header-Datei Inhalt."""
    return f"""#ifndef TEST_{test['safe_name'].upper()}_H
#define TEST_{test['safe_name'].upper()}_H

#include "../../main/test_result.h"
test_result_t {func_name}(void);
#endif /* TEST_{test['safe_name'].upper()}_H */
"""


def generate_c_file_content(test: dict, func_code: str) -> str:
    """C-Datei Inhalt."""
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