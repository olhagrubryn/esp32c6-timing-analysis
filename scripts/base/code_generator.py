#!/usr/bin/env python3
# scripts/base/code_generator.py - FINALE VERSION

from typing import Tuple

def generate_test_function(test: dict, test_type: str = "latency") -> Tuple[str, str]:
    """Generiert C-Code mit optimierter Register-Nutzung und Cache-Warmup."""
    
    func_name = f"test_{test['safe_name']}"
    
    instruction_lines = []
    for i, (insn_name, operands) in enumerate(test["instructions"]):
        if i > 0 and test_type == "latency":
            prev_parts = test["instructions"][i-1][1].split()
            curr_parts = operands.split()
            
            if len(prev_parts) >= 2 and len(curr_parts) >= 2:
                prev_dest = prev_parts[1].rstrip(',')
                curr_src = curr_parts[1].rstrip(',')
                instruction_lines.append(f'            // RAW: {prev_dest} → {curr_src}\n')
            else:
                instruction_lines.append(f'            // RAW chain\n')
        
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    is_load_store = any(insn[0] in ['lb','lh','lw','lbu','lhu','sb','sh','sw'] 
                       for insn in test["instructions"])
    is_branch = any(insn[0] in ['jal', 'jalr', 'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu']
                   for insn in test["instructions"])
    
    if is_load_store:
        if test_type == "throughput":
            return generate_throughput_loadstore_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))
        return generate_loadstore_test_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))
    
    if test_type == "throughput":
        return generate_throughput_test_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"))
    
    return generate_latency_test_function(func_name, test, instruction_block, test.get("test_value", -1), test.get("value_type", "NONE"), is_branch)

def generate_loadstore_test_function(func_name: str, test: dict, instruction_block: str,
                                    test_value, value_type) -> Tuple[str, str]:
    """Load/Store Tests mit dynamischer Buffer-Initialisierung."""
    
    used_regs = set()
    base_registers = set()
    
    for _, operands in test["instructions"]:
        parts = operands.replace(',', '').split()
        if '(' in operands and ')' in operands:
            base_part = operands.split('(')[1].split(')')[0]
            if base_part:
                base_registers.add(base_part)
                used_regs.add(base_part)
        
        for part in parts:
            if part in ['t0','t1','t2','t3','t4','t5','t6',
                       'a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    # Buffer-Deklaration (ohne Initialisierung)
    buffer_decl = """    
    // Safe buffer in RAM
    static uint32_t safe_buffer[128] __attribute__((aligned(64)));
    """
    
    # Dynamische Initialisierung zur Laufzeit - MIT KORREKTEN PRINTF FORMATS
    init_code = """
    // Dynamische Initialisierung des Buffers
    for (int i = 0; i < 128; i++) {
        safe_buffer[i] = 0xDEADBEEF;
    }
    
    // === POINTER-CHASE-KETTEN FÜR VERSCHIEDENE LÄNGEN ===
    // Jede Kette besteht aus (len) aufeinanderfolgenden 32-Bit-Wörtern:
    // - die ersten (len-1) Wörter enthalten Zeiger auf das nächste Wort
    // - das letzte Wort enthält einen Datenwert (0xDEADBEEF + len)
    int current = 0;
    for (int len = 2; len <= 6; len++) {
        int start = current;
        for (int i = 0; i < len-1; i++) {
            safe_buffer[start + i] = (uint32_t)&safe_buffer[start + i + 1];
        }
        safe_buffer[start + len - 1] = 0xDEADBEEF + len;  // eindeutiger Datenwert
        current += len;  // nächste Kette beginnt danach
    }
    
    // Debug-Ausgabe (minimal)
    printf("Buffer at: 0x%08lx\\n", (unsigned long)safe_buffer);
    """
    
    reg_init_code = [
        '    uint32_t safe_buffer_addr = (uint32_t)safe_buffer;',
    ]
    
    for base_reg in sorted(base_registers):
        reg_init_code.append(f'    uint32_t {base_reg}_val = safe_buffer_addr;')
    
    work_regs = ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 'a2', 'a4', 'a5', 'a6', 'a7']
    if test_value != -1:
        for i, reg in enumerate(work_regs):
            if reg in used_regs and reg not in base_registers:
                val = (test_value + i*0x111) & 0xFFFFFFFF
                reg_init_code.append(f'    uint32_t {reg}_val = 0x{val:08X}; // {value_type}')
    else:
        default_values = {
            't0': '0x11111111', 't1': '0x22222222', 't2': '0x33333333',
            't3': '0x44444444', 't4': '0x55555555', 't5': '0x66666666',
            't6': '0x77777777', 'a2': '0xAAAAAAAA', 'a4': '0xBBBBBBBB',
            'a5': '0xCCCCCCCC', 'a6': '0xDDDDDDDD', 'a7': '0xEEEEEEEE',
        }
        for reg in work_regs:
            if reg in used_regs and reg not in base_registers and reg in default_values:
                reg_init_code.append(f'    uint32_t {reg}_val = {default_values[reg]};')
    
    load_regs_lines = ['            // Basis-Register laden']
    
    for base_reg in sorted(base_registers):
        load_regs_lines.append(f'            "mv {base_reg}, %[{base_reg}_val]\\n"')
    
    for reg in sorted(used_regs):
        if reg not in base_registers and reg in work_regs:
            if any(f'{reg}_val' in line for line in reg_init_code):
                load_regs_lines.append(f'            "mv {reg}, %[{reg}_val]\\n"')
    
    load_regs_str = '\n'.join(load_regs_lines)
    
    input_list = []
    for base_reg in sorted(base_registers):
        input_list.append(f'[{base_reg}_val] "r"({base_reg}_val)')
    
    for reg in sorted(used_regs):
        if reg not in base_registers and reg in work_regs:
            if any(f'{reg}_val' in line for line in reg_init_code):
                input_list.append(f'[{reg}_val] "r"({reg}_val)')
    
    inputs_str = ',\n            '.join(input_list) if input_list else ""
    reg_init_str = '\n'.join(reg_init_code)
    
    warmup_code = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs_str}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : 
            : {inputs_str}
            : {clobber_str}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));
"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    {buffer_decl}
    
{init_code}
    
{reg_init_str}
{warmup_code}
    
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
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
        
        if (iter > 0) {{
            cycles = t_end - t_start - 1;
            total_cycles = cycles;
            result.min = cycles;
            result.max = cycles;
        }}
    }}
    
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
    
    reg_init = []
    for base in base_regs:
        offset = 16 if base=='s1' else 32 if base=='s2' else 0
        reg_init.append(f'    uint32_t {base}_val = (uint32_t)safe_buffer + {offset};')
    
    work_regs = ['t0','t1','t2','a2','a4','a5','a6','a7']
    if test_value != -1:
        for i, reg in enumerate(work_regs):
            val = (test_value + i*0x111) & 0xFFFFFFFF
            reg_init.append(f'    uint32_t {reg}_val = 0x{val:08X}; // {value_type}')
    else:
        defaults = {
            't0':'0x11111111','t1':'0x22222222','t2':'0x33333333',
            'a2':'0xAAAAAAAA','a4':'0xBBBBBBBB','a5':'0xCCCCCCCC',
            'a6':'0xDDDDDDDD','a7':'0xEEEEEEEE'
        }
        for reg in work_regs:
            reg_init.append(f'    uint32_t {reg}_val = {defaults[reg]};')
    
    load_regs = ''.join([f'            "mv {base}, %[{base}_val]\\n"' for base in base_regs] +
                        [f'            "mv {reg}, %[{reg}_val]\\n"' for reg in work_regs])
    
    inputs = [f'[{base}_val] "r"({base}_val)' for base in base_regs] + \
             [f'[{reg}_val] "r"({reg}_val)' for reg in work_regs]
    
    warmup = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
            {load_regs}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : 
            : {', '.join(inputs)}
            : {', '.join(clobber)}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));"""
    
    func = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};

    {buffer}
    
{chr(10).join(reg_init)}
{warmup}
    
    result.min = 999999999; result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
            {load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
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


def generate_latency_test_function(func_name: str, test: dict, instruction_block: str, test_value, value_type, is_branch=False) -> Tuple[str, str]:
    """Latency Tests mit Unterstützung für Testwerte und Branches."""
    
    used_regs = set()
    for _, operands in test["instructions"]:
        for part in operands.replace(',', '').split():
            if part in ['t0','t1','t2','t3','t4','t5','t6','a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11', 'ra']:
                used_regs.add(part)
    
    if len(test["instructions"]) > 10:
        used_regs = used_regs.intersection({'t0','t1','t2','a2','a4','a5','s0'})
    
    default_values = {
        't0':'0x11111111','t1':'0x22222222','t2':'0x33333333','t3':'0x44444444',
        't4':'0x55555555','t5':'0x66666666','t6':'0x77777777','a0':'0x88888888',
        'a1':'0x99999999','a2':'0xAAAAAAAA','a3':'0x12345678','a4':'0xBBBBBBBB',
        'a5':'0xCCCCCCCC','a6':'0xDDDDDDDD','a7':'0xEEEEEEEE','s0':'0x11111111',
        's1':'0x22222222','s2':'0x33333333','s3':'0x01010101','s4':'0x02020202',
        's5':'0x03030303','s6':'0x04040404','s7':'0x05050505','s8':'0x06060606',
        's9':'0x07070707','s10':'0x08080808','s11':'0x09090909', 'ra':'0x12345678',
    }
    
    reg_init = []
    if test_value != -1:
        for i, reg in enumerate(sorted(used_regs)):
            if reg in default_values:
                val = (test_value + i*0x111) & 0xFFFFFFFF
                reg_init.append(f'    uint32_t {reg}_val = 0x{val:08X}; // {value_type}')
    else:
        reg_init = [f'    uint32_t {reg}_val = {default_values[reg]};' for reg in sorted(used_regs) if reg in default_values]
    
    load_regs = ''.join([f'            "mv {reg}, %[{reg}_val]\\n"' for reg in sorted(used_regs) if reg in default_values])
    inputs = [f'[{reg}_val] "r"({reg}_val)' for reg in sorted(used_regs) if reg in default_values]
    
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    if is_branch and '"ra"' not in clobber_list:
        clobber_list.append('"ra"')
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    warmup = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : 
            : {', '.join(inputs)}
            : {clobber_str}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));"""
    
    func = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
{chr(10).join(reg_init)}
{warmup}
    
    result.min = 999999999; result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
{load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {', '.join(inputs)}
            : {clobber_str}
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
    """Throughput Tests."""
    
    clobber = '"t0","t1","t2","a2","a4","a5","a6","a7","memory"'
    
    reg_init = []
    work_regs = ['t0','t1','t2','a2','a4','a5','a6','a7']
    if test_value != -1:
        for i, reg in enumerate(work_regs):
            val = (test_value + i*0x111) & 0xFFFFFFFF
            reg_init.append(f'    uint32_t {reg}_val = 0x{val:08X}; // {value_type}')
    else:
        defaults = {
            't0':'0x11111111','t1':'0x22222222','t2':'0x33333333',
            'a2':'0xAAAAAAAA','a4':'0xBBBBBBBB','a5':'0xCCCCCCCC',
            'a6':'0xDDDDDDDD','a7':'0xEEEEEEEE'
        }
        for reg in work_regs:
            reg_init.append(f'    uint32_t {reg}_val = {defaults[reg]};')
    
    reg_init_str = '\n'.join(reg_init)
    
    load_regs = ''.join([f'            "mv {reg}, %[{reg}_val]\\n"' for reg in work_regs])
    inputs = ', '.join([f'[{reg}_val] "r"({reg}_val)' for reg in work_regs])
    
    warmup = f"""
    for (int warm = 0; warm < 2; warm++) {{
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
            {load_regs}
            "fence\\n"
{instruction_block}
            "fence\\n"
            : 
            : {inputs}
            : {clobber}
        );
        portEXIT_CRITICAL(&test_mutex);
    }}
    vTaskDelay(pdMS_TO_TICKS(1));"""
    
    func = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    {reg_init_str}
{warmup}
    
    result.min = 999999999; result.max = 0;
    uint32_t cycles = 0;
    
    for (int iter = 0; iter < 2; iter++) {{
        uint32_t t_start, t_end;
        esp_task_wdt_reset();
        
        portENTER_CRITICAL(&test_mutex);
        __asm__ __volatile__ (
            {load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
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