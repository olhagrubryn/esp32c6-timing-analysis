#!/usr/bin/env python3
# scripts/generate_latency_tests.py - ESP32-C6 Instruction Latency Test Generator
# FIXED: Nur gültige RISC-V Register (a0-a7, aber a0/a1 sind reserved)

import os
import sys
import random
import shutil
import itertools
from collections import defaultdict

# ============================================================================
# Pfad-Konfiguration
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

# ============================================================================
# GÜLTIGE RISC-V REGISTER FÜR ESP32-C6
# ============================================================================

class RISCVRegisters:
    """Definiert gültige Register für ESP32-C6."""
    
    # Verfügbare temporäre Register (nicht a0/a1 da für Return/Stack)
    # a2-a7 sind frei verwendbar
    TEMP_REGS = ["a2", "a3", "a4", "a5", "a6", "a7"]
    
    # Für Load/Store: Basis-Register (muss erhalten bleiben)
    BASE_REG = "a3"
    
    # Für Dependency Chains: Verschiedene Destination Register
    DST_REGS = ["a2", "a4", "a5", "a6", "a7"]
    
    # Für Source Register
    SRC_REGS = ["a2", "a3", "a4", "a5", "a6", "a7"]
    
    @staticmethod
    def get_register_combinations():
        """Verschiedene Register-Kombinationen für Tests."""
        return {
            "same_reg": ["a2", "a2", "a2"],  # dst = src1 = src2
            "diff_reg": ["a2", "a3", "a4"],  # alle verschieden
            "dst_src1": ["a2", "a2", "a3"],  # dst = src1
            "dst_src2": ["a2", "a3", "a2"],  # dst = src2
            "src1_src2": ["a3", "a3", "a3"],  # src1 = src2
        }
    
    @staticmethod
    def get_stress_registers(count):
        """Generiert eine Liste von Registern für Stress-Tests."""
        if count <= 6:
            return RISCVRegisters.TEMP_REGS[:count]
        else:
            # Falls mehr benötigt, recycled
            return [RISCVRegisters.TEMP_REGS[i % len(RISCVRegisters.TEMP_REGS)] for i in range(count)]

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
    
    @staticmethod
    def get_valid_immediate_range(insn_name):
        """
        Gibt den gültigen Immediate-Bereich für eine Instruktion zurück.
        RISC-V hat verschiedene Immediate-Größen je nach Instruktionstyp.
        """
        # Shift-Instruktionen: 5 Bit (0-31)
        if insn_name in ["slli", "srli", "srai"]:
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 15, 16, 24, 31]
        
        # ALU Immediate: 12 Bit signed (-2048 bis 2047)
        elif insn_name in ["addi", "xori", "ori", "andi", "slti", "sltiu"]:
            return [0, 1, 2, 4, 8, 16, 32, 64, 128, 255, 256, 511, 1023, 2047]
        
        # Default: kleine positive Zahlen
        else:
            return [0, 1, 2, 4, 8, 16, 32, 64]

# ============================================================================
# 2. SINGLE-INSTRUKTION TEST GENERATOR - FIXED REGISTER
# ============================================================================

class SingleInstructionTestGenerator:
    """Generiert für JEDE Instruktion mehrere Varianten."""
    
    @staticmethod
    def generate_test_variations(insn_name, insn_template, category):
        """Erstellt mehrere Varianten für eine Instruktion."""
        tests = []
        
        # Basis-Konfigurationen
        if category in ["LOAD", "STORE"]:
            iterations_base = 500
            prefix = "Memory"
            
            # LOAD: Verschiedene Destination Register (NICHT a3!)
            if category == "LOAD":
                for dst in RISCVRegisters.DST_REGS:
                    try:
                        concrete_instr = insn_template.format(
                            dst=dst, 
                            base=RISCVRegisters.BASE_REG
                        )
                        test = {
                            "name": f"{insn_name}_{dst}",
                            "instructions": [(insn_name, concrete_instr)],
                            "iterations": iterations_base,
                            "description": f"{prefix} {insn_name} to {dst}",
                            "category": category,
                            "instruction_count": 1,
                            "variant": f"dst_{dst}"
                        }
                        tests.append(test)
                    except:
                        continue
            
            # STORE: Verschiedene Source Register
            elif category == "STORE":
                for src in RISCVRegisters.DST_REGS:  # Store von verschiedenen Quellen
                    try:
                        concrete_instr = insn_template.format(
                            src=src, 
                            base=RISCVRegisters.BASE_REG
                        )
                        test = {
                            "name": f"{insn_name}_{src}",
                            "instructions": [(insn_name, concrete_instr)],
                            "iterations": iterations_base,
                            "description": f"{prefix} {insn_name} from {src}",
                            "category": category,
                            "instruction_count": 1,
                            "variant": f"src_{src}"
                        }
                        tests.append(test)
                    except:
                        continue
        
        elif category == "IMMEDIATE":
            iterations_base = 1000
            prefix = "Immediate"
            valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
            
            for imm in valid_imms[:6]:  # Maximal 6 Varianten
                try:
                    concrete_instr = insn_template.format(
                        dst="a2",
                        src1="a3",
                        imm=imm
                    )
                    test = {
                        "name": f"{insn_name}_imm{imm}",
                        "instructions": [(insn_name, concrete_instr)],
                        "iterations": iterations_base,
                        "description": f"{prefix} {insn_name} with imm={imm}",
                        "category": category,
                        "instruction_count": 1,
                        "variant": f"imm_{imm}"
                    }
                    tests.append(test)
                except:
                    pass
        
        elif category == "REG2REG":
            iterations_base = 1000
            prefix = "ALU"
            reg_combs = RISCVRegisters.get_register_combinations()
            
            for comb_name, regs in reg_combs.items():
                dst, src1, src2 = regs
                # Prüfe ob alle Register gültig sind
                if all(r in RISCVRegisters.SRC_REGS for r in [dst, src1, src2]):
                    try:
                        concrete_instr = insn_template.format(
                            dst=dst,
                            src1=src1,
                            src2=src2
                        )
                        test = {
                            "name": f"{insn_name}_{comb_name}",
                            "instructions": [(insn_name, concrete_instr)],
                            "iterations": iterations_base,
                            "description": f"{prefix} {insn_name} with {comb_name}",
                            "category": category,
                            "instruction_count": 1,
                            "variant": comb_name
                        }
                        tests.append(test)
                    except:
                        pass
        
        elif category == "DIV_MUL":
            iterations_base = 200
            prefix = "Arithmetic"
            reg_combs = RISCVRegisters.get_register_combinations()
            
            for comb_name, regs in reg_combs.items():
                dst, src1, src2 = regs
                if all(r in RISCVRegisters.SRC_REGS for r in [dst, src1, src2]):
                    try:
                        concrete_instr = insn_template.format(
                            dst=dst,
                            src1=src1,
                            src2=src2
                        )
                        test = {
                            "name": f"{insn_name}_{comb_name}",
                            "instructions": [(insn_name, concrete_instr)],
                            "iterations": iterations_base,
                            "description": f"{prefix} {insn_name} with {comb_name}",
                            "category": category,
                            "instruction_count": 1,
                            "variant": comb_name
                        }
                        tests.append(test)
                    except:
                        pass
        
        return tests
    
    @staticmethod
    def generate_all_single_instruction_tests():
        """Generiert ALLE Varianten für jede Instruktion."""
        all_tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        
        for category, insn_set in categories.items():
            for insn_name in sorted(insn_set):
                if insn_name in all_insn:
                    variations = SingleInstructionTestGenerator.generate_test_variations(
                        insn_name, 
                        all_insn[insn_name],
                        category
                    )
                    all_tests.extend(variations)
        
        return all_tests

# ============================================================================
# 3. SEQUENZ TEST GENERATOR - FIXED REGISTER
# ============================================================================

class SequenceTestGenerator:
    """Generiert umfangreiche Sequenz-Tests mit vielen Varianten."""
    
    @staticmethod
    def generate_dependency_chains(insn_name, category, length=5):
        """Generiert eine Dependency Chain mit einer Instruktion."""
        instructions = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        if insn_name not in all_insn:
            return None
            
        template = all_insn[insn_name]
        
        for i in range(length):
            try:
                if category in ["LOAD", "STORE"]:
                    if category == "LOAD":
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        instr = template.format(dst=dst, base=RISCVRegisters.BASE_REG)
                    else:  # STORE
                        src = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        instr = template.format(src=src, base=RISCVRegisters.BASE_REG)
                
                elif category == "IMMEDIATE":
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                    valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                    imm = valid_imms[i % len(valid_imms)]
                    instr = template.format(dst=dst, src1=src1, imm=imm)
                
                else:  # REG2REG oder DIV_MUL
                    # Echte Dependency Chain: Ergebnis wird nächste Quelle
                    if i == 0:
                        dst = "a2"
                        src1 = "a3"
                        src2 = "a4"
                    else:
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.DST_REGS[(i-1) % len(RISCVRegisters.DST_REGS)]  # Abhängig vom vorherigen
                        src2 = RISCVRegisters.SRC_REGS[(i+2) % len(RISCVRegisters.SRC_REGS)]
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                
                instructions.append((insn_name, instr))
            except Exception as e:
                continue
        
        return instructions if instructions else None
    
    @staticmethod
    def generate_random_sequence(category, min_len=2, max_len=6):
        """Generiert eine vollständig zufällige Sequenz."""
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        
        if category not in categories:
            return None
            
        insn_list = sorted(list(categories[category]))
        length = random.randint(min_len, max_len)
        selected = random.sample(insn_list, min(length, len(insn_list)))
        
        instructions = []
        
        for i, insn_name in enumerate(selected):
            if insn_name in all_insn:
                template = all_insn[insn_name]
                
                try:
                    if category == "LOAD":
                        dst = random.choice(RISCVRegisters.DST_REGS)
                        instr = template.format(dst=dst, base=RISCVRegisters.BASE_REG)
                    
                    elif category == "STORE":
                        src = random.choice(RISCVRegisters.DST_REGS)
                        instr = template.format(src=src, base=RISCVRegisters.BASE_REG)
                    
                    elif category == "IMMEDIATE":
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                        imm = random.choice(valid_imms)
                        instr = template.format(dst=dst, src1=src1, imm=imm)
                    
                    else:  # REG2REG oder DIV_MUL
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                    
                    instructions.append((insn_name, instr))
                except:
                    continue
        
        return instructions if instructions else None
    
    @staticmethod
    def generate_all_sequence_tests():
        """Generiert ALLE möglichen Sequenz-Tests."""
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        # 1. Dependency Chains für jede Instruktion
        print("\n      → Generating dependency chains...")
        for category, insn_set in categories.items():
            if category in ["LOAD", "STORE"]:
                continue  # Skip für Memory
            
            for insn_name in sorted(insn_set)[:2]:  # Erste 2 pro Kategorie
                for length in [3, 4]:
                    chain = SequenceTestGenerator.generate_dependency_chains(
                        insn_name, category, length
                    )
                    if chain and len(chain) == length:
                        test = {
                            "name": f"CHAIN_{insn_name}_{length}",
                            "instructions": chain,
                            "iterations": 200 if category == "DIV_MUL" else 300,
                            "description": f"Dependency chain of {length} {insn_name}",
                            "category": category,
                            "instruction_count": len(chain),
                            "insn_name": "chain"
                        }
                        tests.append(test)
        
        # 2. Mix verschiedener Instruktionen
        print("      → Generating instruction mixes...")
        for category, insn_set in categories.items():
            insn_list = sorted(list(insn_set))
            
            for length in [2, 3, 4]:
                if len(insn_list) >= length:
                    test = SequenceTestGenerator.generate_sequence_test(
                        insn_list[:length], category, f"{category}_mix{length}"
                    )
                    if test: tests.append(test)
        
        # 3. Zufällige Sequenzen
        print("      → Generating random sequences...")
        for category in categories.keys():
            if category in ["LOAD", "STORE"]:
                num_random = 5
            else:
                num_random = 10
            
            for i in range(num_random):
                seq = SequenceTestGenerator.generate_random_sequence(
                    category, 
                    min_len=3, 
                    max_len=6
                )
                if seq:
                    test = {
                        "name": f"RAND_{category}_{i+1:03d}",
                        "instructions": seq,
                        "iterations": 200 if category == "DIV_MUL" else 300,
                        "description": f"Random sequence #{i+1} of {len(seq)} {category} instr",
                        "category": category,
                        "instruction_count": len(seq),
                        "insn_name": "random"
                    }
                    tests.append(test)
        
        # 4. Register-Stress-Tests - FIXED: Nur gültige Register!
        print("      → Generating register stress tests...")
        for category in ["REG2REG", "IMMEDIATE"]:
            for reg_count in [3, 4, 5]:  # Max 5 da wir nur a2-a7 haben (6 Register)
                instructions = []
                regs = RISCVRegisters.get_stress_registers(reg_count)
                
                for i in range(6):  # 6 Instruktionen
                    try:
                        if category == "REG2REG":
                            dst = regs[i % len(regs)]
                            src1 = regs[(i+1) % len(regs)]
                            src2 = regs[(i+2) % len(regs)]
                            instr = f"add {dst}, {src1}, {src2}"
                            instructions.append(("add", instr))
                        else:  # IMMEDIATE
                            dst = regs[i % len(regs)]
                            src1 = regs[(i+1) % len(regs)]
                            instr = f"addi {dst}, {src1}, 1"
                            instructions.append(("addi", instr))
                    except:
                        continue
                
                if instructions:
                    test = {
                        "name": f"STRESS_{category}_reg{reg_count}",
                        "instructions": instructions,
                        "iterations": 200,
                        "description": f"Register stress test with {reg_count} registers",
                        "category": category,
                        "instruction_count": len(instructions),
                        "insn_name": "stress"
                    }
                    tests.append(test)
        
        # 5. Memory Access Patterns (nur LOAD) - FIXED: Gültige Offsets
        print("      → Generating memory access patterns...")
        for pattern in ["sequential", "random"]:
            for count in [2, 3, 4]:
                instructions = []
                for i in range(count):
                    try:
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        if pattern == "sequential":
                            offset = i * 4
                        else:
                            offset = random.choice([0, 4, 8, 12, 16, 20, 24, 28])
                        instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                        instructions.append(("lw", instr))
                    except:
                        continue
                
                if instructions:
                    test = {
                        "name": f"MEM_{pattern}_{count}",
                        "instructions": instructions,
                        "iterations": 200,
                        "description": f"{pattern} memory access ({count} loads)",
                        "category": "LOAD",
                        "instruction_count": len(instructions),
                        "insn_name": "memory"
                    }
                    tests.append(test)
        
        return tests
    
    @staticmethod
    def generate_sequence_test(insn_list, category, name_suffix):
        """Erstellt einen Test mit einer Sequenz von Instruktionen."""
        instructions = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        for i, insn_name in enumerate(insn_list):
            if insn_name in all_insn:
                template = all_insn[insn_name]
                
                try:
                    if category == "LOAD":
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        instr = template.format(dst=dst, base=RISCVRegisters.BASE_REG)
                        instructions.append((insn_name, instr))
                        
                    elif category == "STORE":
                        src = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        instr = template.format(src=src, base=RISCVRegisters.BASE_REG)
                        instructions.append((insn_name, instr))
                        
                    elif category == "IMMEDIATE":
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                        imm = valid_imms[i % len(valid_imms)]
                        instr = template.format(dst=dst, src1=src1, imm=imm)
                        instructions.append((insn_name, instr))
                        
                    else:  # REG2REG oder DIV_MUL
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                        instructions.append((insn_name, instr))
                except:
                    continue
        
        if not instructions:
            return None
            
        if category in ["LOAD", "STORE"]:
            iterations = 200
        elif category == "DIV_MUL":
            iterations = 100
        else:
            iterations = 300
        
        return {
            "name": f"SEQ_{name_suffix}",
            "instructions": instructions,
            "iterations": iterations,
            "description": f"Sequence of {len(instructions)} {category} instructions",
            "category": category,
            "instruction_count": len(instructions),
            "insn_name": "sequence"
        }

# ============================================================================
# 4. C CODE GENERATOR
# ============================================================================

def generate_test_function(test):
    """Generiert C-Code für EINEN Test."""
    
    func_name = f"test_{test['name'].replace('-', '_').replace('.', '_')}"
    
    instruction_lines = []
    
    # Instruktionen mit korrekter Syntax
    for insn_name, operands in test["instructions"]:
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    # C-Funktion Template mit Speicher-Initialisierung
    func_template = f"""float {func_name}(void) {{
    float total_cycles = 0;
    
    // Safe buffer in RAM - mit initialisierten Werten!
    static uint32_t safe_buffer[32] __attribute__((aligned(32))) = {{
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
    uint32_t r7_val = 0x0F0F0F0F;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {test["iterations"]}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"      // a3 = safe_buffer (BLEIBT ERHALTEN!)
            "mv a4, %[mem_ptr]\\n"
            "mv a5, %[mem_ptr]\\n"
            "mv a6, %[mem_ptr]\\n"
            "mv a7, %[mem_ptr]\\n"
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n" // Start cycle count
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"   // End cycle count
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr), "r"(r3_val), "r"(r4_val), "r"(r5_val), "r"(r6_val), "r"(r7_val)
            : "a2", "a3", "a4", "a5", "a6", "a7", "memory"
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
    
    # Erstelle Unterverzeichnisse für verschiedene Test-Typen
    os.makedirs(os.path.join(TESTS_DIR, "single"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "chains"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "sequences"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "random"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "stress"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "memory"), exist_ok=True)
    
    print(f"  ✓ Created test subdirectories")

def generate_all_test_files(all_tests):
    """Generiert alle Test-Files mit Kategorisierung."""
    
    ensure_directories()
    
    # ========================================================================
    # 1. Generiere Test-Files in verschiedenen Unterverzeichnissen
    # ========================================================================
    
    test_files = []
    test_categories = defaultdict(list)
    
    # Kategorisiere Tests
    for test in all_tests:
        if test["instruction_count"] == 1:
            subdir = "single"
        elif "CHAIN" in test["name"]:
            subdir = "chains"
        elif "SEQ" in test["name"]:
            subdir = "sequences"
        elif "RAND" in test["name"]:
            subdir = "random"
        elif "STRESS" in test["name"]:
            subdir = "stress"
        elif "MEM" in test["name"]:
            subdir = "memory"
        else:
            subdir = "sequences"
        
        test_categories[subdir].append(test)
    
    # Generiere Files für jede Kategorie
    for subdir, tests in test_categories.items():
        subdir_path = os.path.join(TESTS_DIR, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        
        for test in tests:
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
#include "../../main/esp32c6_latency_tests.h"

extern portMUX_TYPE test_mutex;

{test_func}
"""
            
            with open(os.path.join(subdir_path, c_filename), "w") as f:
                f.write(c_content)
            
            with open(os.path.join(subdir_path, h_filename), "w") as f:
                f.write(header_content)
            
            test_files.append((safe_name, test, c_filename, h_filename, subdir))
            print(f"  ✓ Generated: tests/{subdir}/{c_filename}")
    
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
    
    for safe_name, test, _, h_file, subdir in test_files:
        central_header += f'#include "../tests/{subdir}/{h_file}"\n'
    
    central_header += """
// Initialization
void init_performance_counters(void);

// Test runners
void run_all_latency_tests(void);
void run_category_tests(const char* category);
void run_test_group(const char* group);
void print_csv_results(void);
void print_detailed_results(void);
void print_statistical_summary(void);

// Externer Zugriff auf Test-Anzahl
extern const int LATENCY_TEST_COUNT;
extern const int SINGLE_TEST_COUNT;
extern const int SEQUENCE_TEST_COUNT;
extern const int RANDOM_TEST_COUNT;

#endif /* ESP32C6_LATENCY_TESTS_H */
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_latency_tests.h"), "w") as f:
        f.write(central_header)
    
    # ========================================================================
    # 3. Generiere MAIN Test-Runner
    # ========================================================================
    
    test_definitions = []
    for safe_name, test, _, _, subdir in test_files:
        test_definitions.append(f'    {{"{test["name"]}", test_{safe_name}, {test["iterations"]}, {test["instruction_count"]}, "{test["description"]}", "{test["category"]}", "{subdir}"}}')
    
    test_definitions_str = ",\n".join(test_definitions)
    
    single_count = len([t for t in test_files if t[1]["instruction_count"] == 1])
    seq_count = len([t for t in test_files if "SEQ" in t[1]["name"] or "CHAIN" in t[1]["name"]])
    random_count = len([t for t in test_files if "RAND" in t[1]["name"]])
    
    main_content = f"""#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

// Test statistics
const int LATENCY_TEST_COUNT = {len(test_files)};
const int SINGLE_TEST_COUNT = {single_count};
const int SEQUENCE_TEST_COUNT = {seq_count};
const int RANDOM_TEST_COUNT = {random_count};

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
    const char* group;
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
    printf("Bachelorarbeit - Umfassende Benchmarking-Analyse\\n");
    printf("========================================================\\n\\n");
    
    printf("Test Statistics:\\n");
    printf("  • Total tests: %d\\n", NUM_TESTS);
    printf("  • Single instruction tests: %d\\n", SINGLE_TEST_COUNT);
    printf("  • Sequence tests: %d\\n", SEQUENCE_TEST_COUNT);
    printf("  • Random tests: %d\\n", RANDOM_TEST_COUNT);
    printf("\\n");
    
    init_performance_counters();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    printf("\\n%-25s %-10s %-10s %-10s %-15s %s\\n", 
           "Test Name", "Cycles", "CPI", "Latency", "Group", "Category");
    printf("%-25s %-10s %-10s %-10s %-15s %s\\n",
           "---------", "------", "---", "-------", "-----", "--------");
    
    float total_latency = 0;
    float min_latency = 999999;
    float max_latency = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const latency_test_t* test = &all_tests[i];
        
        // 3 Runs für statistische Signifikanz
        float cycles_sum = 0;
        
        for (int run = 0; run < 3; run++) {{
            float cycles = test->function();
            cycles_sum += cycles;
        }}
        
        float cycles_avg = cycles_sum / 3.0f;
        float cpi = cycles_avg / (float)test->instruction_count;
        float latency = cycles_avg / (float)test->iterations;
        
        total_latency += latency;
        if (latency < min_latency) min_latency = latency;
        if (latency > max_latency) max_latency = latency;
        
        printf("%-25s %-10.2f %-10.2f %-10.2f %-15s %s\\n",
               test->name, cycles_avg, cpi, latency, test->group, test->category);
        
        vTaskDelay(pdMS_TO_TICKS(5));
    }}
    
    printf("\\n========================================================\\n");
    printf("SUMMARY STATISTICS\\n");
    printf("========================================================\\n");
    printf("  • Average latency across all tests: %.2f cycles\\n", total_latency / NUM_TESTS);
    printf("  • Minimum latency: %.2f cycles\\n", min_latency);
    printf("  • Maximum latency: %.2f cycles\\n", max_latency);
    printf("\\n");
}}

// ... (rest of runner functions from previous version) ...
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
    printf("\\n");
    printf("╔════════════════════════════════════════════════════════════╗\\n");
    printf("║     ESP32-C6 INSTRUCTION LATENCY BENCHMARKING SUITE        ║\\n");
    printf("║              Bachelorarbeit - Umfassende Analyse           ║\\n");
    printf("╚════════════════════════════════════════════════════════════╝\\n");
    printf("\\n");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // Komplette Test-Suite
    run_all_latency_tests();
    
    printf("\\n✓ All tests completed successfully!\\n");
    printf("  Total tests executed: %d\\n", LATENCY_TEST_COUNT);
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}
"""
    
    with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
        f.write(main_c)
    
    # ========================================================================
    # 5. Generiere CMakeLists.txt
    # ========================================================================
    
    cmake_sources = "main.c\n    esp32c6_latency_tests.c\n"
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
# 6. MAIN GENERATOR
# ============================================================================

def generate_complete_test_suite():
    """Hauptfunktion: Generiert Test-Suite für Bachelorarbeit."""
    
    print("\n" + "=" * 80)
    print("  ESP32-C6 INSTRUCTION LATENCY TEST GENERATOR".center(80))
    print("  Bachelorarbeit - Umfassende Benchmarking-Analyse".center(80))
    print("=" * 80)
    
    # 1. Generiere Single-Instruction Varianten
    print("\n[1/4] Generating SINGLE instruction tests...")
    single_tests = SingleInstructionTestGenerator.generate_all_single_instruction_tests()
    print(f"      → {len(single_tests)} single instruction test variants")
    
    # 2. Generiere Sequenz-Tests
    print("\n[2/4] Generating SEQUENCE tests...")
    sequence_tests = SequenceTestGenerator.generate_all_sequence_tests()
    print(f"      → {len(sequence_tests)} sequence test variants")
    
    # 3. Kombiniere alle Tests
    print("\n[3/4] Combining test suite...")
    all_tests = single_tests + sequence_tests
    print(f"      → Total tests: {len(all_tests)}")
    
    # 4. Generiere alle Test-Files
    print("\n[4/4] Generating test files...")
    test_files = generate_all_test_files(all_tests)
    
    print("\n" + "=" * 80)
    print("  GENERATION COMPLETE!".center(80))
    print("=" * 80)
    
    print(f"\n📊 FINAL TEST STATISTICS:")
    print(f"   • TOTAL TESTS: {len(all_tests)}")
    print(f"   • Single instruction variants: {len(single_tests)}")
    print(f"   • Sequence tests: {len(sequence_tests)}")
    
    return all_tests

# ============================================================================
# 7. MAIN
# ============================================================================

if __name__ == "__main__":
    random.seed(42)
    tests = generate_complete_test_suite()