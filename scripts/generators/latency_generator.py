#!/usr/bin/env python3
# scripts/generators/latency_generator.py

import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions

class LatencyRAWChainGenerator:
    """RAW Dependency Chains."""
    
    @staticmethod
    def create_raw_chain(insn_name: str, insn_template: str, 
                        class_name: str, chain_length: int,
                        register_set: str = "mixed") -> list:
        """
        Erzeugt eine RAW-Abhängigkeitskette.
        Für Load/Store wird NUR a3 als Basis-Pointer verwendet!
        """
        
        # Wähle Register-Set
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
        last_dest = None
        
        for i in range(chain_length):
            # Wähle Destination
            dst = regs[i % len(regs)]
            
            if class_name in ["CLASS5_LOAD", "CLASS6_STORE"]:
                # FÜR LOAD/STORE: s0 als Basis-Pointer verwenden (nicht a3!)
                base_reg = RISCVRegisters.S0  # WICHTIG: s0 statt a3!
                
                if class_name == "CLASS5_LOAD":
                    # Load: dst = memory[base_reg]
                    instr = insn_template.format(dst=dst, base=base_reg)
                else:  # STORE
                    # Store: memory[base_reg] = dst
                    instr = insn_template.format(src=dst, base=base_reg)
                
                instructions.append((insn_name, instr))
    
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
    """Single Instruction Tests."""
    
    @staticmethod
    def generate_all():
        tests, all_insn = [], RISCVInstructions.get_all_instructions()
        classes = RISCVInstructions.get_instructions_by_class()
        
        print("\n      → Generating single instruction tests...")
        
        for class_name, insn_set in classes.items():
            for insn_name in sorted(insn_set):
                if insn_name not in all_insn: continue
                tmpl = all_insn[insn_name]
                
                for comb_name, regs in RISCVRegisters.get_register_combinations().items():
                    dst, src1, src2 = regs
                    try:
                        if class_name == "CLASS5_LOAD":
                            instr = tmpl.format(dst=dst, base=RISCVRegisters.S0)
                        elif class_name == "CLASS6_STORE":
                            instr = tmpl.format(src=dst, base=RISCVRegisters.S0)
                        elif class_name == "CLASS7_IMMEDIATE":
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
        
        # ALU vs Immediate
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
        
        # Shift → ALU
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