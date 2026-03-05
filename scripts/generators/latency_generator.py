#!/usr/bin/env python3
# scripts/generators/latency_generator.py

import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class LatencyRAWChainGenerator:
    """RAW Dependency Chains."""
    
    @staticmethod
    def create_raw_chain(insn_name: str, insn_template: str, 
                        class_name: str, chain_length: int,
                        register_set: str = "mixed") -> list:
        
        if register_set == "t_regs":
            regs = [RISCVRegisters.T0, RISCVRegisters.T1, RISCVRegisters.T2,
                    RISCVRegisters.T3, RISCVRegisters.T4, RISCVRegisters.T5, RISCVRegisters.T6]
        elif register_set == "a_regs":
            regs = [RISCVRegisters.A0, RISCVRegisters.A1, RISCVRegisters.A2,
                    RISCVRegisters.A4, RISCVRegisters.A5, RISCVRegisters.A6, RISCVRegisters.A7]
        elif register_set == "s_regs":
            regs = [RISCVRegisters.S0, RISCVRegisters.S1, RISCVRegisters.S2,
                    RISCVRegisters.S3, RISCVRegisters.S4, RISCVRegisters.S5, RISCVRegisters.S6,
                    RISCVRegisters.S7, RISCVRegisters.S8, RISCVRegisters.S9, RISCVRegisters.S10,
                    RISCVRegisters.S11]
        else:  # mixed
            regs = RISCVRegisters.CHAIN_REGS
        
        instructions = []
        
        for i in range(chain_length):
            dst = regs[i % len(regs)]
            
            if class_name in ["CLASS5_LOAD", "CLASS6_STORE"]:
                base_reg = RISCVRegisters.BASE_REG
                offset = (i * 4) % 64
                
                if class_name == "CLASS5_LOAD":
                    instr = insn_template.format(dst=dst, base=base_reg, offset=offset)
                else:
                    instr = insn_template.format(src=dst, base=base_reg, offset=offset)
                
                instructions.append((insn_name, instr))
            
            elif class_name == "CLASS7_IMMEDIATE":
                if i == 0:
                    src1 = regs[(i+1) % len(regs)]
                else:
                    src1 = instructions[-1][1].split()[1].rstrip(',')
                    if src1 not in regs:
                        src1 = regs[(i+1) % len(regs)]
                imm = 1
                instr = insn_template.format(dst=dst, src1=src1, imm=imm)
                instructions.append((insn_name, instr))
            else:
                if i == 0:
                    src1 = regs[(i+1) % len(regs)]
                    src2 = regs[(i+2) % len(regs)]
                else:
                    src1 = instructions[-1][1].split()[1].rstrip(',')
                    if src1 not in regs:
                        src1 = regs[(i+1) % len(regs)]
                    src2 = regs[(i+2) % len(regs)]
                instr = insn_template.format(dst=dst, src1=src1, src2=src2)
                instructions.append((insn_name, instr))
        
        return instructions
    
    @staticmethod
    def generate_class_tests():
        tests, all_insn = [], RISCVInstructions.get_all_instructions()
        classes = RISCVInstructions.get_instructions_by_class()
        
        print("\n      → Generating RAW dependency chains...")
        reg_sets = ["t_regs", "a_regs", "s_regs", "mixed"]
        
        for class_name, insn_set in classes.items():
            lengths = [2,3,4] if class_name in ["CLASS5_LOAD","CLASS6_STORE"] else [3,5,7,10]
            base_iter = 200 if class_name in ["CLASS5_LOAD","CLASS6_STORE"] else 300
            
            for insn_name in sorted(insn_set)[:2]:
                if insn_name not in all_insn: continue
                tmpl = all_insn[insn_name]
                
                for reg_set in reg_sets:
                    for length in lengths:
                        chain = LatencyRAWChainGenerator.create_raw_chain(insn_name, tmpl, class_name, length, reg_set)
                        if chain:
                            iter = min(base_iter, 100 if class_name=="CLASS4_DIV" else 200 if class_name in ["CLASS3_MUL","CLASS5_LOAD","CLASS6_STORE"] else 300)
                            tests.append({
                                "name": f"RAW_{class_name}_{insn_name}_{length}_{reg_set}",
                                "safe_name": f"RAW_{class_name}_{insn_name}_{length}_{reg_set}",
                                "instructions": chain, "iterations": iter, "category": class_name,
                                "instruction_count": length, "description": f"RAW chain of {length} {insn_name} using {reg_set}",
                                "test_group": "raw_chains", "type": "latency", "test_value": -1, "value_type": "NONE"
                            })
        return tests


class SingleInstructionTestGenerator:
    """Single Instruction Tests mit verschiedenen Offsets für Load/Store."""
    
    @staticmethod
    def generate_all():
        tests, all_insn = [], RISCVInstructions.get_all_instructions()
        classes = RISCVInstructions.get_instructions_by_class()
        
        print("\n      → Generating single instruction tests...")
        
        for class_name, insn_set in classes.items():
            for insn_name in sorted(insn_set):
                if insn_name not in all_insn: continue
                tmpl = all_insn[insn_name]
                
                if class_name == "CLASS5_LOAD" or class_name == "CLASS6_STORE":
                    offsets = [0, 4, 8, 12, 16, 20, 24, 28]
                    for offset in offsets:
                        for dst in [RISCVRegisters.A2, RISCVRegisters.A4, RISCVRegisters.A5]:
                            try:
                                if class_name == "CLASS5_LOAD":
                                    instr = tmpl.format(dst=dst, base=RISCVRegisters.BASE_REG, offset=offset)
                                else:
                                    instr = tmpl.format(src=dst, base=RISCVRegisters.BASE_REG, offset=offset)
                                
                                tests.append({
                                    "name": f"SINGLE_{class_name}_{insn_name}_{dst}_off{offset}",
                                    "safe_name": f"SINGLE_{class_name}_{insn_name}_{dst}_off{offset}",
                                    "instructions": [(insn_name, instr)], "iterations": 300,
                                    "category": class_name, "instruction_count": 1,
                                    "description": f"Single {insn_name} to {dst} offset {offset}",
                                    "test_group": "single", "type": "latency", "test_value": -1, "value_type": "NONE"
                                })
                            except: continue
                else:
                    for comb_name, regs in RISCVRegisters.get_register_combinations().items():
                        dst, src1, src2 = regs
                        try:
                            if class_name == "CLASS7_IMMEDIATE":
                                imm = RISCVInstructions.get_valid_immediate_range(insn_name)[0]
                                instr = tmpl.format(dst=dst, src1=src1, imm=imm)
                            else:
                                instr = tmpl.format(dst=dst, src1=src1, src2=src2)
                            
                            tests.append({
                                "name": f"SINGLE_{class_name}_{insn_name}_{comb_name}",
                                "safe_name": f"SINGLE_{class_name}_{insn_name}_{comb_name}",
                                "instructions": [(insn_name, instr)], "iterations": 300,
                                "category": class_name, "instruction_count": 1,
                                "description": f"Single {insn_name} with {comb_name}",
                                "test_group": "single", "type": "latency", "test_value": -1, "value_type": "NONE"
                            })
                        except: continue
        return tests


class ZeroIdiomTestGenerator:
    """Zero-Idioms (sub/xor)."""
    
    @staticmethod
    def generate_all():
        tests = []
        print("\n      → Generating zero idiom tests...")
        
        for insn_name, tmpl in [("sub", "sub {dst}, {src}, {src}"), ("xor", "xor {dst}, {src}, {src}")]:
            for reg in [RISCVRegisters.T0, RISCVRegisters.A0, RISCVRegisters.S0]:
                instr = tmpl.format(dst=reg, src=reg)
                tests.append({
                    "name": f"ZEROIDIOM_{insn_name}_{reg}",
                    "safe_name": f"ZEROIDIOM_{insn_name}_{reg}",
                    "instructions": [(insn_name, instr)], "iterations": 500,
                    "category": "CLASS1_ALU_ZERO", "instruction_count": 1,
                    "description": f"Zero idiom: {insn_name} {reg}, {reg}, {reg}",
                    "test_group": "zero_idioms", "type": "latency", "test_value": -1, "value_type": "NONE"
                })
                
                tests.append({
                    "name": f"ZEROIDIOM_CHAIN_{insn_name}_{reg}",
                    "safe_name": f"ZEROIDIOM_CHAIN_{insn_name}_{reg}",
                    "instructions": [(insn_name, instr), ("add", f"add {RISCVRegisters.T1}, {reg}, {RISCVRegisters.T2}")],
                    "iterations": 300, "category": "CLASS1_ALU_ZERO_CHAIN", "instruction_count": 2,
                    "description": f"Zero idiom chain: {insn_name} → add",
                    "test_group": "zero_idioms", "type": "latency", "test_value": -1, "value_type": "NONE"
                })
        return tests


class MixedClassTestGenerator:
    """Cross-Class Dependency Chains."""
    
    @staticmethod
    def generate_all():
        tests = []
        print("\n      → Generating mixed class tests...")
        
        for alu in ["add","xor"]:
            for imm in ["addi","xori"]:
                tests.append({
                    "name": f"MIXED_ALU_IMM_{alu}_{imm}",
                    "safe_name": f"MIXED_ALU_IMM_{alu}_{imm}",
                    "instructions": [
                        (alu, f"{alu} {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}"),
                        (imm, f"{imm} {RISCVRegisters.T1}, {RISCVRegisters.T0}, 1"),
                        (alu, f"{alu} {RISCVRegisters.T2}, {RISCVRegisters.T1}, {RISCVRegisters.T3}"),
                    ], "iterations": 300, "category": "MIXED_CLASS1_ALU_IMM", "instruction_count": 3,
                    "description": "ALU vs Immediate", "test_group": "mixed", "type": "latency",
                    "test_value": -1, "value_type": "NONE"
                })
        
        for shift in ["sll"]:
            for alu in ["add"]:
                tests.append({
                    "name": f"MIXED_SHIFT_ALU_{shift}_{alu}",
                    "safe_name": f"MIXED_SHIFT_ALU_{shift}_{alu}",
                    "instructions": [
                        (shift, f"{shift} {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}"),
                        (alu, f"{alu} {RISCVRegisters.T1}, {RISCVRegisters.T0}, {RISCVRegisters.T3}"),
                    ], "iterations": 300, "category": "MIXED_CLASS2_SHIFT_ALU", "instruction_count": 2,
                    "description": "Shift → ALU", "test_group": "mixed", "type": "latency",
                    "test_value": -1, "value_type": "NONE"
                })
        return tests


class MultiInstructionTestGenerator:
    """Multi-Instruction Tests - Lange Chains."""
    
    @staticmethod
    def generate_all():
        tests, all_insn = [], RISCVInstructions.get_all_instructions()
        print("\n      → Generating long RAW chains...")
        
        for length in [10,20,30]:
            for insn in ["add","xor"]:
                chain = LatencyRAWChainGenerator.create_raw_chain(insn, all_insn[insn], "CLASS1_ALU", length, "mixed")
                if chain:
                    tests.append({
                        "name": f"LONG_RAW_{insn.upper()}_{length}",
                        "safe_name": f"LONG_RAW_{insn.upper()}_{length}",
                        "instructions": chain, "iterations": 150, "category": "CLASS1_ALU_LONG",
                        "instruction_count": length, "description": f"Long RAW chain of {length} {insn}",
                        "test_group": "long_chains", "type": "latency", "test_value": -1, "value_type": "NONE"
                    })
        return tests


class ShiftRegisterTestGenerator:
    """Tests für Register-Shifts mit explizit gesetzten Shift-Beträgen."""
    
    @staticmethod
    def generate_all():
        tests = []
        print("\n      → Generating register shift tests with controlled amounts...")
        
        shift_amounts = [0, 1, 2, 4, 8, 16, 31]
        
        for insn_name in ["sll", "srl", "sra"]:
            for shamt in shift_amounts:
                instructions = [
                    ("li", f"li {RISCVRegisters.T1}, {shamt}"),
                    (insn_name, f"{insn_name} {RISCVRegisters.T0}, {RISCVRegisters.T2}, {RISCVRegisters.T1}")
                ]
                tests.append({
                    "name": f"SHIFT_REG_{insn_name}_shamt{shamt}",
                    "safe_name": f"SHIFT_REG_{insn_name}_shamt{shamt}",
                    "instructions": instructions,
                    "iterations": 500,
                    "category": "CLASS2_SHIFT_REG",
                    "instruction_count": 2,
                    "description": f"{insn_name} with shift amount {shamt} loaded into register",
                    "test_group": "shift_register",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        return tests


class MultiSequenceTestGenerator:
    """Generiert lange Sequenz-Tests mit 20-50 Instruktionen."""
    
    @staticmethod
    def generate_multi_sequence_tests():
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        print("\n      → Generating MULTI-SEQUENCE tests (20-50 ops)...")
        
        for category in ["REG2REG", "IMMEDIATE"]:
            for length in [20, 30, 40]:
                chain = MultiSequenceTestGenerator._generate_long_chain(category, length)
                if chain:
                    tests.append({
                        "name": f"LONG_CHAIN_{category}_{length}",
                        "safe_name": f"LONG_CHAIN_{category}_{length}",
                        "instructions": chain,
                        "iterations": 150,
                        "description": f"Long chain of {length} {category} instr",
                        "category": category,
                        "instruction_count": length,
                        "type": "latency",
                        "test_group": "long_chains",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        for category in ["REG2REG", "IMMEDIATE", "LOAD"]:
            for i in range(3):
                length = random.randint(25, 50)
                seq = MultiSequenceTestGenerator._generate_long_random(category, length)
                if seq:
                    tests.append({
                        "name": f"LONG_RAND_{category}_{i+1}_{length}",
                        "safe_name": f"LONG_RAND_{category}_{i+1}_{length}",
                        "instructions": seq,
                        "iterations": 150,
                        "description": f"Long random {length} {category} instr",
                        "category": category,
                        "instruction_count": length,
                        "type": "latency",
                        "test_group": "long_random",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        for pattern in ["sequential", "random", "strided"]:
            for count in [20, 30, 40]:
                seq = MultiSequenceTestGenerator._generate_memory_sequence(pattern, count)
                if seq:
                    tests.append({
                        "name": f"MEM_STRESS_{pattern}_{count}",
                        "safe_name": f"MEM_STRESS_{pattern}_{count}",
                        "instructions": seq,
                        "iterations": 150,
                        "description": f"Memory stress {pattern} {count} loads",
                        "category": "LOAD",
                        "instruction_count": count,
                        "type": "latency",
                        "test_group": "memory_stress",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        return tests
    
    @staticmethod
    def _generate_long_chain(category, length):
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
                    
                    else:
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


class DividerLatencyGenerator:
    """Latenztests für Division/Remainder mit verschiedenen Werten."""
    
    @staticmethod
    def generate_all():
        tests = []
        print("\n      → Generating divider latency tests with value categories...")
        
        div_insns = ["div", "divu", "rem", "remu"]
        
        chain_template = [
            ("{insn}", "{insn} a2, a4, a5"),
            ("{insn}", "{insn} a4, a2, a6"),
            ("{insn}", "{insn} a6, a4, a7")
        ]
        
        for insn in div_insns:
            for val in TestValueRegistry.HIGH_THROUGHPUT_VALUES:
                instructions = [(insn, templ.format(insn=insn)) for (_, templ) in chain_template]
                tests.append({
                    "name": f"DIV_LATENCY_{insn}_HIGH_{val}",
                    "safe_name": f"DIV_LATENCY_{insn}_HIGH_{val}",
                    "instructions": instructions,
                    "iterations": 200,
                    "category": f"DIV_LATENCY_HIGH",
                    "instruction_count": 3,
                    "description": f"{insn} latency with HIGH value {val}",
                    "test_group": "div_latency",
                    "type": "latency",
                    "test_value": val,
                    "value_type": "HIGH"
                })
            
            for val in TestValueRegistry.LOW_THROUGHPUT_VALUES:
                instructions = [(insn, templ.format(insn=insn)) for (_, templ) in chain_template]
                tests.append({
                    "name": f"DIV_LATENCY_{insn}_LOW_{val}",
                    "safe_name": f"DIV_LATENCY_{insn}_LOW_{val}",
                    "instructions": instructions,
                    "iterations": 200,
                    "category": f"DIV_LATENCY_LOW",
                    "instruction_count": 3,
                    "description": f"{insn} latency with LOW value {val}",
                    "test_group": "div_latency",
                    "type": "latency",
                    "test_value": val,
                    "value_type": "LOW"
                })
            
            for val in TestValueRegistry.EDGE_CASE_VALUES:
                instructions = [(insn, templ.format(insn=insn)) for (_, templ) in chain_template]
                tests.append({
                    "name": f"DIV_LATENCY_{insn}_EDGE_{val}",
                    "safe_name": f"DIV_LATENCY_{insn}_EDGE_{val}",
                    "instructions": instructions,
                    "iterations": 200,
                    "category": f"DIV_LATENCY_EDGE",
                    "instruction_count": 3,
                    "description": f"{insn} latency with EDGE value {val}",
                    "test_group": "div_latency",
                    "type": "latency",
                    "test_value": val,
                    "value_type": "EDGE"
                })
        
        return tests