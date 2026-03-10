#!/usr/bin/env python3
# scripts/generate_latency_tests.py - ESP32-C6 Instruction Latency Test Generator


import os
import sys
import random
import shutil
import itertools
from collections import defaultdict


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

class RISCVRegisters:
    """Definiert gültige Register für ESP32-C6."""
    
    # Verfügbare temporäre Register (nicht a0/a1 da für Return/Stack)
    # a2-a7 sind frei verwendbar, aber a3 ist reserviert für Base Pointer!
    TEMP_REGS = ["a2", "a4", "a5", "a6", "a7"]  # a3 entfernt!
    
    # Für Load/Store: Basis-Register 
    BASE_REG = "a3"  
    
    # Für Dependency Chains
    DST_REGS = ["a2", "a4", "a5", "a6", "a7"]
    
    # Für Source Register 
    SRC_REGS = ["a2", "a4", "a5", "a6", "a7"] 
    
    @staticmethod
    def get_register_combinations():
        """Verschiedene Register-Kombinationen für Tests - OHNE a3 als dst/src!"""
        return {
            "same_reg": ["a2", "a2", "a2"],  # dst = src1 = src2
            "diff_reg": ["a2", "a4", "a5"],  # alle verschieden
            "dst_src1": ["a2", "a2", "a4"],  # dst = src1
            "dst_src2": ["a2", "a4", "a2"],  # dst = src2
            "src1_src2": ["a4", "a4", "a4"],  # src1 = src2
        }
    
    @staticmethod
    def get_stress_registers(count):
        """Generiert eine Liste von Registern für Stress-Tests - OHNE a3."""
        regs = RISCVRegisters.TEMP_REGS[:]  # a2,a4,a5,a6,a7
        if count <= len(regs):
            return regs[:count]
        else:
            return [regs[i % len(regs)] for i in range(count)]


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
        """Gibt den gültigen Immediate-Bereich für eine Instruktion zurück."""
        if insn_name in ["slli", "srli", "srai"]:
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 15, 16, 24, 31]
        elif insn_name in ["addi", "xori", "ori", "andi", "slti", "sltiu"]:
            return [0, 1, 2, 4, 8, 16, 32, 64, 128, 255, 256, 511, 1023, 2047]
        else:
            return [0, 1, 2, 4, 8, 16, 32, 64]


class MultiInstructionTestGenerator:
    """Multi-Instruction Tests (10-30 Instruktionen)."""
    
    @staticmethod
    def generate_all():
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        counts = [10, 20, 30]
        
        for category, insn_set in categories.items():
            for insn_name in sorted(insn_set)[:3]:
                if category == "LOAD":
                    for dst in RISCVRegisters.DST_REGS[:1]:
                        for count in counts:
                            instrs = []
                            for i in range(count):
                                offset = (i * 4) % 32
                                instr = f"{insn_name} {dst}, {offset}({RISCVRegisters.BASE_REG})"
                                instrs.append((insn_name, instr))
                            
                 
                            test = {
                                "name": f"{insn_name}_multi{count}",
                                "safe_name": f"{insn_name}_multi{count}",
                                "instructions": instrs,
                                "iterations": 200,
                                "category": f"{category}_MULTI",  
                                "instruction_count": count,
                                "type": "latency",
                                "test_group": "multi"  
                            }
                            tests.append(test)
        return tests
    
    @staticmethod
    def _generate_memory_tests(insn_name, template, category, counts):
        """Memory Tests mit mehreren Instruktionen."""
        tests = []
        iterations_base = 200
        
        if category == "LOAD":
            for dst in RISCVRegisters.DST_REGS[:2]:
                for count in counts:
                    instr_list = []
                    for i in range(count):
                        offset = (i * 4) % 32
                        if "lb" in insn_name or "lbu" in insn_name:
                            instr = f"{insn_name} {dst}, {offset}({RISCVRegisters.BASE_REG})"
                        else:
                            instr = template.format(dst=dst, base=RISCVRegisters.BASE_REG)
                        instr_list.append((insn_name, instr))
                    
                    test = {
                        "name": f"{insn_name}_{dst}_multi{count}",
                        "instructions": instr_list,
                        "iterations": iterations_base,
                        "description": f"Multi {count}x {insn_name} to {dst}",
                        "category": category,
                        "instruction_count": count,
                        "variant": f"multi_{count}"
                    }
                    tests.append(test)
        
        elif category == "STORE":
            for src in RISCVRegisters.DST_REGS[:2]:
                for count in counts:
                    instr_list = []
                    for i in range(count):
                        offset = (i * 4) % 32
                        if "sb" in insn_name:
                            instr = f"{insn_name} {src}, {offset}({RISCVRegisters.BASE_REG})"
                        else:
                            instr = template.format(src=src, base=RISCVRegisters.BASE_REG)
                        instr_list.append((insn_name, instr))
                    
                    test = {
                        "name": f"{insn_name}_{src}_multi{count}",
                        "instructions": instr_list,
                        "iterations": iterations_base,
                        "description": f"Multi {count}x {insn_name} from {src}",
                        "category": category,
                        "instruction_count": count,
                        "variant": f"multi_{count}"
                    }
                    tests.append(test)
        
        return tests
    
    @staticmethod
    def _generate_immediate_tests(insn_name, template, counts):
        """Immediate Tests mit mehreren Instruktionen."""
        tests = []
        iterations_base = 200
        valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)[:3]
        
        for imm in valid_imms:
            for count in counts:
                instr_list = []
                for i in range(count):
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                    instr = template.format(dst=dst, src1=src1, imm=imm)
                    instr_list.append((insn_name, instr))
                
                test = {
                    "name": f"{insn_name}_imm{imm}_multi{count}",
                    "instructions": instr_list,
                    "iterations": iterations_base,
                    "description": f"Multi {count}x {insn_name} imm={imm}",
                    "category": "IMMEDIATE",
                    "instruction_count": count,
                    "variant": f"multi_{count}"
                }
                tests.append(test)
        
        return tests
    
    @staticmethod
    def _generate_reg2reg_tests(insn_name, template, counts):
        """Register-to-Register Tests mit mehreren Instruktionen."""
        tests = []
        iterations_base = 200
        reg_combs = RISCVRegisters.get_register_combinations()
        
        for comb_name, regs in list(reg_combs.items())[:2]:
            dst, src1, src2 = regs
            for count in counts:
                instr_list = []
                for i in range(count):
                    if i % 5 == 0:
                        alt_dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        alt_src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        alt_src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                        instr = template.format(dst=alt_dst, src1=alt_src1, src2=alt_src2)
                    else:
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                    instr_list.append((insn_name, instr))
                
                test = {
                    "name": f"{insn_name}_{comb_name}_multi{count}",
                    "instructions": instr_list,
                    "iterations": iterations_base,
                    "description": f"Multi {count}x {insn_name} {comb_name}",
                    "category": "REG2REG",
                    "instruction_count": count,
                    "variant": f"multi_{count}"
                }
                tests.append(test)
        
        return tests
    
    @staticmethod
    def _generate_divmul_tests(insn_name, template, counts):
        """Division/Multiplikation Tests mit mehreren Instruktionen."""
        tests = []
        iterations_base = 100
        div_counts = [10, 20]
        
        reg_combs = RISCVRegisters.get_register_combinations()
        for comb_name, regs in list(reg_combs.items())[:1]:
            dst, src1, src2 = regs
            for count in div_counts:
                instr_list = []
                for i in range(count):
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                    instr_list.append((insn_name, instr))
                
                test = {
                    "name": f"{insn_name}_{comb_name}_multi{count}",
                    "instructions": instr_list,
                    "iterations": iterations_base,
                    "description": f"Multi {count}x {insn_name} {comb_name}",
                    "category": "DIV_MUL",
                    "instruction_count": count,
                    "variant": f"multi_{count}"
                }
                tests.append(test)
        
        return tests



class MultiSequenceTestGenerator:
    """Generiert lange Sequenz-Tests mit 20-50 Instruktionen."""
    
    @staticmethod
    def generate_multi_sequence_tests():
        """Generiert zusätzliche lange Sequenz-Tests."""
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        print("\n      → Generating MULTI-SEQUENCE tests (20-50 ops)...")
        
        # 1. LANGE Dependency Chains
        for category in ["REG2REG", "IMMEDIATE"]:
            for length in [20, 30, 40]:
                chain = MultiSequenceTestGenerator._generate_long_chain(category, length)
                if chain:
                    test = {
                        "name": f"LONG_CHAIN_{category}_{length}",
                        "instructions": chain,
                        "iterations": 150,
                        "description": f"Long chain of {length} {category} instr",
                        "category": category,
                        "instruction_count": length,
                        "insn_name": "long_chain"
                    }
                    tests.append(test)
        
        # 2. LANGE Random Sequences
        for category in ["REG2REG", "IMMEDIATE", "LOAD"]:
            for i in range(3):
                length = random.randint(25, 50)
                seq = MultiSequenceTestGenerator._generate_long_random(category, length)
                if seq:
                    test = {
                        "name": f"LONG_RAND_{category}_{i+1}_{length}",
                        "instructions": seq,
                        "iterations": 150,
                        "description": f"Long random {length} {category} instr",
                        "category": category,
                        "instruction_count": length,
                        "insn_name": "long_random"
                    }
                    tests.append(test)
        
        # 3. Memory Stress Tests
        for pattern in ["sequential", "random", "strided"]:
            for count in [20, 30, 40]:
                seq = MultiSequenceTestGenerator._generate_memory_sequence(pattern, count)
                if seq:
                    test = {
                        "name": f"MEM_STRESS_{pattern}_{count}",
                        "instructions": seq,
                        "iterations": 150,
                        "description": f"Memory stress {pattern} {count} loads",
                        "category": "LOAD",
                        "instruction_count": count,
                        "insn_name": "memory_stress"
                    }
                    tests.append(test)
        
        return tests
    
    @staticmethod
    def _generate_long_chain(category, length):
        """Generiert eine lange Dependency Chain."""
        instructions = []
        
        if category == "REG2REG":
            for i in range(length):
                dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                if i == 0:
                    src1 = RISCVRegisters.SRC_REGS[0]
                    src2 = RISCVRegisters.SRC_REGS[1]
                else:
                    src1 = instructions[-1][1].split()[1].rstrip(',')
                    if src1 not in RISCVRegisters.SRC_REGS:
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                    src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                
                op = random.choice(["add", "xor", "or"])
                instr = f"{op} {dst}, {src1}, {src2}"
                instructions.append((op, instr))
        
        elif category == "IMMEDIATE":
            for i in range(length):
                dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                if i == 0:
                    src1 = RISCVRegisters.SRC_REGS[0]
                else:
                    src1 = instructions[-1][1].split()[1].rstrip(',')
                    if src1 not in RISCVRegisters.SRC_REGS:
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                
                imm = (i * 2) % 256
                instr = f"addi {dst}, {src1}, {imm}"
                instructions.append(("addi", instr))
        
        return instructions if len(instructions) == length else None
    
    @staticmethod
    def _generate_long_random(category, length):
        """Generiert eine lange zufällige Sequenz."""
        instructions = []
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        
        if category not in categories:
            return None
            
        insn_list = sorted(list(categories[category]))
        
        for i in range(length):
            insn_name = random.choice(insn_list)
            if insn_name in all_insn:
                template = all_insn[insn_name]
                
                try:
                    if category == "LOAD":
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        offset = random.choice([0, 4, 8, 12, 16, 20, 24, 28])
                        instr = f"{insn_name} {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    
                    elif category == "IMMEDIATE":
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                        imm = random.choice(valid_imms)
                        instr = template.format(dst=dst, src1=src1, imm=imm)
                    
                    else:  # REG2REG
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                    
                    instructions.append((insn_name, instr))
                except:
                    continue
        
        return instructions if instructions else None
    
    @staticmethod
    def _generate_memory_sequence(pattern, count):
        """Generiert eine Memory-Zugriffssequenz."""
        instructions = []
        
        for i in range(count):
            dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
            
            if pattern == "sequential":
                offset = (i * 4) % 64
            elif pattern == "strided":
                offset = (i * 8) % 64
            else:  
                offset = random.choice([0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60])
            
            if i % 3 == 0:
                instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
            elif i % 3 == 1:
                instr = f"lh {dst}, {offset}({RISCVRegisters.BASE_REG})"
            else:
                instr = f"lb {dst}, {offset}({RISCVRegisters.BASE_REG})"
            
            instructions.append(("load", instr))
        
        return instructions


class SingleInstructionTestGenerator:
    """Original - Generiert Single-Instruction Tests (1 Instruktion pro Durchlauf)."""
    
    @staticmethod
    def generate_test_variations(insn_name, insn_template, category):
        """Original - FIXED: Kein a3 als src1!"""
        tests = []
        
        # Basis-Konfigurationen
        if category in ["LOAD", "STORE"]:
            iterations_base = 500
            prefix = "Memory"
            
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
            
            elif category == "STORE":
                for src in RISCVRegisters.DST_REGS:
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
            
            for imm in valid_imms[:6]:
                try:
                    
                    concrete_instr = insn_template.format(
                        dst="a2",
                        src1="a4",  
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
        """Original - unverändert."""
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


class SequenceTestGenerator:
    """Original - Generiert kurze Sequenz-Tests (2-6 Instruktionen)."""
    
    @staticmethod
    def generate_dependency_chains(insn_name, category, length=5):
        """Original - FIXED: Kein a3 als src1!"""
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
                    if i == 0:
                        dst = "a2"
                        src1 = "a4"  
                        src2 = "a5"
                    else:
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.DST_REGS[(i-1) % len(RISCVRegisters.DST_REGS)]
                        src2 = RISCVRegisters.SRC_REGS[(i+2) % len(RISCVRegisters.SRC_REGS)]
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                
                instructions.append((insn_name, instr))
            except Exception as e:
                continue
        
        return instructions if instructions else None
    
    @staticmethod
    def generate_random_sequence(category, min_len=2, max_len=6):
        """Original - unverändert."""
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
        """Original - unverändert."""
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        # 1. Dependency Chains
        print("\n      → Generating dependency chains...")
        for category, insn_set in categories.items():
            if category in ["LOAD", "STORE"]:
                continue
            
            for insn_name in sorted(insn_set)[:2]:
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
        
        # 2. Instruction Mixes
        print("      → Generating instruction mixes...")
        for category, insn_set in categories.items():
            insn_list = sorted(list(insn_set))
            for length in [2, 3, 4]:
                if len(insn_list) >= length:
                    test = SequenceTestGenerator.generate_sequence_test(
                        insn_list[:length], category, f"{category}_mix{length}"
                    )
                    if test: tests.append(test)
        
        # 3. Random Sequences
        print("      → Generating random sequences...")
        for category in categories.keys():
            if category in ["LOAD", "STORE"]:
                num_random = 5
            else:
                num_random = 10
            for i in range(num_random):
                seq = SequenceTestGenerator.generate_random_sequence(
                    category, min_len=3, max_len=6
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
        
        # 4. Register Stress Tests
        print("      → Generating register stress tests...")
        for category in ["REG2REG", "IMMEDIATE"]:
            for reg_count in [3, 4, 5]:
                instructions = []
                regs = RISCVRegisters.get_stress_registers(reg_count)
                for i in range(6):
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
        
        # 5. Memory Access Patterns
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
        """Original - unverändert."""
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



def generate_test_function(test):
    """C-Code Generator - FIXED: a3 wird in JEDER Iteration mit ptr initialisiert!"""
    
    func_name = f"test_{test['name'].replace('-', '_').replace('.', '_')}"
    
    instruction_lines = []
    
    for insn_name, operands in test["instructions"]:
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
  
  
    func_template = f"""float {func_name}(void) {{
    float total_cycles = 0;
    
    // Safe buffer in RAM - mit initialisierten Werten!
    static uint32_t safe_buffer[64] __attribute__((aligned(64))) = {{
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678,
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x87654321
    }};
    
    uint32_t *ptr = safe_buffer;
    
    // Initial values for registers
    uint32_t r2_val = 0x12345678;
    uint32_t r3_val = 0x87654321;
    uint32_t r4_val = 0xABCDEF01;
    uint32_t r5_val = 0xFEDCBA98;
    uint32_t r6_val = 0x0F0F0F0F;
    uint32_t r7_val = 0xF0F0F0F0;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {test["iterations"]}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            // FIXED: a3 wird in JEDER Iteration neu initialisiert!
            "mv a3, %[mem_ptr]\\n"      // a3 = gültiger Speicherpointer (JEDE Iteration!)
            
            // Initialize work registers with test values
            "mv a2, %[r2_val]\\n"
            "mv a4, %[r4_val]\\n"
            "mv a5, %[r5_val]\\n"
            "mv a6, %[r6_val]\\n"
            "mv a7, %[r7_val]\\n"
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n" // Start cycle count
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"   // End cycle count
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr),  // WICHTIG: ptr wird bei JEDER Iteration übergeben!
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
    return total_cycles;
}}
"""
    return func_template



def ensure_directories():
    """Stellt sicher, dass alle benötigten Verzeichnisse existieren."""
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    
    os.makedirs(os.path.join(TESTS_DIR, "single"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "chains"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "sequences"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "random"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "stress"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "memory"), exist_ok=True)
    os.makedirs(os.path.join(TESTS_DIR, "multi"), exist_ok=True)
    
    print(f"  ✓ Created test subdirectories")

def generate_all_test_files(all_tests):
    """Generiert alle Test-Files mit Kategorisierung."""
    
    ensure_directories()
    

    test_files = []
    test_categories = defaultdict(list)
    
    # Kategorisiere Tests
    for test in all_tests:
        if test["instruction_count"] == 1:
            subdir = "single"
        elif "multi" in test.get("variant", "") or "MULTI" in test["name"] or "LONG" in test["name"]:
            subdir = "multi"
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
            print(f"  ✓ Generated: tests/{subdir}/{c_filename} ({test['instruction_count']} ops)")
    


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
extern const int MULTI_TEST_COUNT;
extern const int SEQUENCE_TEST_COUNT;
extern const int RANDOM_TEST_COUNT;

#endif /* ESP32C6_LATENCY_TESTS_H */
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_latency_tests.h"), "w") as f:
        f.write(central_header)
    

    test_definitions = []
    for safe_name, test, _, _, subdir in test_files:
        test_definitions.append(f'    {{"{test["name"]}", test_{safe_name}, {test["iterations"]}, {test["instruction_count"]}, "{test["description"]}", "{test["category"]}", "{subdir}"}}')
    
    test_definitions_str = ",\n".join(test_definitions)
    
    single_count = len([t for t in test_files if t[1]["instruction_count"] == 1])
    multi_count = len([t for t in test_files if t[1]["instruction_count"] > 1])
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
const int MULTI_TEST_COUNT = {multi_count};
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
    printf("  • Multi instruction tests: %d (10-50 ops)\\n", MULTI_TEST_COUNT);
    printf("  • Sequence tests: %d\\n", SEQUENCE_TEST_COUNT);
    printf("  • Random tests: %d\\n", RANDOM_TEST_COUNT);
    printf("\\n");
    
    init_performance_counters();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    printf("\\n%-30s %-12s %-12s %-12s %-15s %s\\n", 
           "Test Name", "Total Cycles", "CPI", "Latency/Op", "Group", "Category");
    printf("%-30s %-12s %-12s %-12s %-15s %s\\n",
           "---------", "-----------", "---", "----------", "-----", "--------");
    
    int total_latency = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const latency_test_t* test = &all_tests[i];
        
        // 3 Runs für statistische Signifikanz
        int cycles_sum = 0;
        
        for (int run = 0; run < 3; run++) {{
            int cycles = test->function();
            cycles_sum += cycles;
        }}
        
        int cpi = cycles_avg / test->instruction_count;
        int per_instruction = cycles_avg / (float)test->iterations / (float)test->instruction_count;
        
        total_latency += per_instruction;
        
        printf("%-30s %-12.2f %-12.2f %-12.2f %-15s %s\\n",
               test->name, cycles_avg, cpi, per_instruction, test->group, test->category);
        
        vTaskDelay(pdMS_TO_TICKS(2));
    }}
    
    printf("\\n========================================================\\n");
    printf("SUMMARY STATISTICS\\n");
    printf("========================================================\\n");
    printf("  • Average cycles per instruction: %.2f\\n", total_latency / NUM_TESTS);
    printf("  • Minimum cycles per instruction: %.2f\\n", min_latency);
    printf("  • Maximum cycles per instruction: %.2f\\n", max_latency);
    printf("\\n");
}}

void run_category_tests(const char* category) {{
    printf("\\nRunning tests for category: %s\\n", category);
    printf("------------------------------------------------\\n");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        const latency_test_t* test = &all_tests[i];
        if (strcmp(test->category, category) == 0) {{
            float cycles = test->function();
            float per_instruction = cycles / (float)test->iterations / (float)test->instruction_count;
            printf("%-30s: %8.2f cycles/op\\n", test->name, per_instruction);
        }}
    }}
}}

void print_statistical_summary(void) {{
    float cpi_values[NUM_TESTS];
    int count = 0;
    float sum = 0, sum_sq = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        float cycles = all_tests[i].function();
        float cpi = cycles / (float)all_tests[i].instruction_count;
        cpi_values[count++] = cpi;
        sum += cpi;
        sum_sq += cpi * cpi;
    }}
    
    float mean = sum / count;
    
    printf("\\nStatistical Summary:\\n");
    printf("  Mean CPI: %.2f\\n", mean);
}}
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_latency_tests.c"), "w") as f:
        f.write(main_content)
  
    main_c = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_latency_tests.h"

void app_main(void) {
    printf("\\n");
    printf("╔════════════════════════════════════════════════════════════╗\\n");
    printf("║     ESP32-C6 INSTRUCTION LATENCY BENCHMARKING SUITE        ║\\n");
    printf("║              Bachelorarbeit - Umfassende Analyse           ║\\n");
    printf("║           Single + Multi-Instruction Tests (10-50 ops)     ║\\n");
    printf("╚════════════════════════════════════════════════════════════╝\\n");
    printf("\\n");
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Komplette Test-Suite
    run_all_latency_tests();
    
    printf("\\n✓ All tests completed successfully!\\n");
    printf("  Total tests executed: %d\\n", LATENCY_TEST_COUNT);
    printf("  Multi-instruction tests: %d\\n", MULTI_TEST_COUNT);
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}
"""
    
    with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
        f.write(main_c)
    
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


def generate_complete_test_suite():
    """Hauptfunktion: Generiert Test-Suite mit SINGLE + MULTI instruction tests."""
    
    print("\n" + "=" * 80)
    print("  ESP32-C6 INSTRUCTION LATENCY TEST GENERATOR".center(80))
    print("  Bachelorarbeit - Umfassende Benchmarking-Analyse".center(80))
    print("  MIT: Single-Instruction Tests + Multi-Instruction Tests".center(80))
    print("  FIXED: a3 wird in JEDER Iteration initialisiert!".center(80))
    print("=" * 80)
    
 
    print("\n[1/5] Generating SINGLE instruction tests (1 op)...")
    single_tests = SingleInstructionTestGenerator.generate_all_single_instruction_tests()
    print(f"      → {len(single_tests)} single instruction test variants")
    


    print("\n[2/5] Generating SEQUENCE tests (2-6 ops)...")
    sequence_tests = SequenceTestGenerator.generate_all_sequence_tests()
    print(f"      → {len(sequence_tests)} sequence test variants")
    
   
    print("\n[3/5] Generating MULTI-INSTRUCTION tests (10,20,30 ops)...")
    multi_tests = MultiInstructionTestGenerator.generate_multi_instruction_tests()
    print(f"      → {len(multi_tests)} multi-instruction test variants")
    
   
   
    print("\n[4/5] Generating LONG SEQUENCE tests (20-50 ops)...")
    long_tests = MultiSequenceTestGenerator.generate_multi_sequence_tests()
    print(f"      → {len(long_tests)} long sequence test variants")
    

    print("\n[5/5] Combining ALL test suites...")
    all_tests = single_tests + sequence_tests + multi_tests + long_tests
    print(f"      → TOTAL TESTS: {len(all_tests)}")
    print(f"      → Single: {len(single_tests)}")
    print(f"      → Sequence: {len(sequence_tests)}")
    print(f"      → Multi: {len(multi_tests)}")
    print(f"      → Long: {len(long_tests)}")
    

    print("\nGenerating test files...")
    test_files = generate_all_test_files(all_tests)
    
    print("\n" + "=" * 80)
    print("  GENERATION COMPLETE!".center(80))
    print("=" * 80)
    
    print(f"\n📊 FINAL TEST STATISTICS:")
    print(f"   • TOTAL TESTS: {len(all_tests)}")
    print(f"   • Single instruction (1 op): {len(single_tests)}")
    print(f"   • Short sequences (2-6 ops): {len(sequence_tests)}")
    print(f"   • Multi-instruction (10-30 ops): {len(multi_tests)}")
    print(f"   • Long sequences (20-50 ops): {len(long_tests)}")
    
    lengths = [t["instruction_count"] for t in all_tests]
    print(f"\n📊 INSTRUCTION COUNT DISTRIBUTION:")
    print(f"   • Min: {min(lengths)} op")
    print(f"   • Max: {max(lengths)} ops")
    print(f"   • Avg: {sum(lengths)/len(lengths):.1f} ops")
    print(f"   • Total instruction executions: {sum([t['instruction_count'] * t['iterations'] for t in all_tests])}")
    
    return all_tests


if __name__ == "__main__":
    random.seed(42)
    tests = generate_complete_test_suite()