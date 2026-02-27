#!/usr/bin/env python3
# scripts/generators/latency_generator.py - Mit vollständiger Register-Auswahl

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions

class LatencyRAWChainGenerator:
    """
    Implementiert RAW Dependency Chains mit verschiedenen Register-Typen.
    """
    
    @staticmethod
    # In generators/latency_generator.py, in der create_raw_chain Methode:

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
                # FÜR LOAD/STORE: NUR a3 als Basis-Pointer verwenden!
                base_reg = RISCVRegisters.A3  # a3 ist der einzige Base-Pointer
                
                if class_name == "CLASS5_LOAD":
                    # Load: dst = memory[base_reg]
                    instr = insn_template.format(dst=dst, base=base_reg)
                else:  # STORE
                    # Store: memory[base_reg] = dst
                    instr = insn_template.format(src=dst, base=base_reg)
                
                instructions.append((insn_name, instr))
                last_dest = dst
                
            elif class_name == "CLASS7_IMMEDIATE":
                # Immediate: Nur ein Register-Input
                valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                imm = valid_imms[i % len(valid_imms)]
                
                if i == 0:
                    src1 = regs[(i + 1) % len(regs)]
                else:
                    src1 = last_dest
                
                instr = insn_template.format(dst=dst, src1=src1, imm=imm)
                instructions.append((insn_name, instr))
                last_dest = dst
                
            else:
                # ALU, Shift, Mul, Div
                if i == 0:
                    src1 = regs[(i + 1) % len(regs)]
                    src2 = regs[(i + 2) % len(regs)]
                else:
                    src1 = last_dest
                    src2 = regs[(i + 2) % len(regs)]
                
                instr = insn_template.format(dst=dst, src1=src1, src2=src2)
                instructions.append((insn_name, instr))
                last_dest = dst
        
        return instructions
    
    @staticmethod
    def generate_class_tests():
        """Generiert RAW-Chain-Tests."""
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        classes = RISCVInstructions.get_instructions_by_class()
        
        print("\n      → Generating RAW dependency chains...")
        
        # Teste mit verschiedenen Register-Sets
        register_sets = ["t_regs", "a_regs", "s_regs", "mixed"]
        
        for class_name, insn_set in classes.items():
            # Verschiedene Kettenlängen
            if class_name in ["CLASS5_LOAD", "CLASS6_STORE"]:
                # Für Load/Store: Kürzere Ketten
                chain_lengths = [2, 3, 4]
                iterations_base = 200
            else:
                chain_lengths = [3, 5, 7, 10]
                iterations_base = 300
            
            for insn_name in sorted(insn_set)[:2]:
                if insn_name not in all_insn:
                    continue
                    
                template = all_insn[insn_name]
                
                for reg_set in register_sets:
                    for length in chain_lengths:
                        chain = LatencyRAWChainGenerator.create_raw_chain(
                            insn_name, template, class_name, length, reg_set
                        )
                        
                        if chain:
                            # Iterationen basierend auf Klasse
                            if class_name == "CLASS4_DIV":
                                iterations = min(iterations_base, 100)
                            elif class_name in ["CLASS3_MUL", "CLASS5_LOAD", "CLASS6_STORE"]:
                                iterations = min(iterations_base, 200)
                            else:
                                iterations = min(iterations_base, 300)
                            
                            test = {
                                "name": f"RAW_{class_name}_{insn_name}_{length}_{reg_set}",
                                "safe_name": f"RAW_{class_name}_{insn_name}_{length}_{reg_set}",
                                "instructions": chain,
                                "iterations": iterations,
                                "category": class_name,
                                "instruction_count": length,
                                "description": f"RAW chain of {length} {insn_name} using {reg_set}",
                                "test_group": "raw_chains",
                                "type": "latency",
                                "test_value": -1,
                                "value_type": "NONE"
                            }
                            tests.append(test)
        
        return tests


class SingleInstructionTestGenerator:
    """Single-Instruction Tests mit verschiedenen Register-Kombinationen."""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        classes = RISCVInstructions.get_instructions_by_class()
        
        print("\n      → Generating single instruction tests...")
        
        for class_name, insn_set in classes.items():
            # Überspringe Load/Store Klassen komplett!
            if class_name in ["CLASS5_LOAD", "CLASS6_STORE"]:
                print(f"        Überspringe {class_name} (wird später aktiviert)")
                continue
                
            for insn_name in sorted(insn_set):
                if insn_name not in all_insn:
                    continue
                    
                template = all_insn[insn_name]
                
                # Verschiedene Register-Kombinationen testen
                reg_combs = RISCVRegisters.get_register_combinations()
                
                for comb_name, regs in reg_combs.items():
                    dst, src1, src2 = regs
                    
                    try:
                        if class_name == "CLASS7_IMMEDIATE":
                            valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                            instr = template.format(dst=dst, src1=src1, imm=valid_imms[0])
                        else:
                            instr = template.format(dst=dst, src1=src1, src2=src2)
                        
                        test = {
                            "name": f"SINGLE_{class_name}_{insn_name}_{comb_name}",
                            "safe_name": f"SINGLE_{class_name}_{insn_name}_{comb_name}",
                            "instructions": [(insn_name, instr)],
                            "iterations": 500,
                            "category": class_name,
                            "instruction_count": 1,
                            "description": f"Single {insn_name} with {comb_name}",
                            "test_group": "single",
                            "type": "latency",
                            "test_value": -1,
                            "value_type": "NONE"
                        }
                        tests.append(test)
                    except Exception as e:
                        continue
        
        return tests


class ZeroIdiomTestGenerator:
    """Testet Zero-Idioms (sub rd, rs, rs und xor rd, rs, rs)."""
    
    @staticmethod
    def generate_all():
        tests = []
        
        print("\n      → Generating zero idiom tests...")
        
        zero_instructions = [
            ("sub", "sub {dst}, {src}, {src}"),
            ("xor", "xor {dst}, {src}, {src}")
        ]
        
        # Teste mit verschiedenen Registern
        for insn_name, template in zero_instructions:
            for reg in [RISCVRegisters.T0, RISCVRegisters.A0, RISCVRegisters.S0]:
                instr = template.format(dst=reg, src=reg)
                
                test = {
                    "name": f"ZEROIDIOM_{insn_name}_{reg}",
                    "safe_name": f"ZEROIDIOM_{insn_name}_{reg}",
                    "instructions": [(insn_name, instr)],
                    "iterations": 500,
                    "category": "CLASS1_ALU_ZERO",
                    "instruction_count": 1,
                    "description": f"Zero idiom: {insn_name} {reg}, {reg}, {reg}",
                    "test_group": "zero_idioms",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                }
                tests.append(test)
                
                # Auch als kurze Kette testen
                chain = [
                    (insn_name, instr),
                    ("add", f"add {RISCVRegisters.T1}, {reg}, {RISCVRegisters.T2}")
                ]
                
                test = {
                    "name": f"ZEROIDIOM_CHAIN_{insn_name}_{reg}",
                    "safe_name": f"ZEROIDIOM_CHAIN_{insn_name}_{reg}",
                    "instructions": chain,
                    "iterations": 300,
                    "category": "CLASS1_ALU_ZERO_CHAIN",
                    "instruction_count": 2,
                    "description": f"Zero idiom chain: {insn_name} → add",
                    "test_group": "zero_idioms",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                }
                tests.append(test)
        
        return tests


class MixedClassTestGenerator:
    """Cross-Class Dependency Chains - OHNE Load/Store für jetzt."""
    
    @staticmethod
    def generate_all():
        tests = []
        
        print("\n      → Generating mixed class tests (nur ALU)...")
        
        # 1. ALU vs Immediate (OK)
        alu_insns = ["add", "xor"]
        imm_insns = ["addi", "xori"]
        
        for alu in alu_insns:
            for imm in imm_insns:
                chain = [
                    (alu, f"{alu} {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}"),
                    (imm, f"{imm} {RISCVRegisters.T1}, {RISCVRegisters.T0}, 1"),
                    (alu, f"{alu} {RISCVRegisters.T2}, {RISCVRegisters.T1}, {RISCVRegisters.T3}"),
                ]
                
                tests.append({
                    "name": f"MIXED_ALU_IMM_{alu}_{imm}",
                    "safe_name": f"MIXED_ALU_IMM_{alu}_{imm}",
                    "instructions": chain,
                    "iterations": 300,
                    "category": "MIXED_CLASS1_ALU_IMM",
                    "instruction_count": 3,
                    "description": "ALU vs Immediate - operand count influence",
                    "test_group": "mixed",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        # 2. Shift → ALU (OK)
        for shift in ["sll"]:
            for alu in ["add"]:
                chain = [
                    (shift, f"{shift} {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}"),
                    (alu, f"{alu} {RISCVRegisters.T1}, {RISCVRegisters.T0}, {RISCVRegisters.T3}"),
                ]
                
                tests.append({
                    "name": f"MIXED_SHIFT_ALU_{shift}_{alu}",
                    "safe_name": f"MIXED_SHIFT_ALU_{shift}_{alu}",
                    "instructions": chain,
                    "iterations": 300,
                    "category": "MIXED_CLASS2_SHIFT_ALU",
                    "instruction_count": 2,
                    "description": "Shift → ALU - dedicated shifter vs shared ALU",
                    "test_group": "mixed",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        # Load/Store Tests werden später aktiviert
        print("        Load/Store Tests werden später aktiviert")
        
        return tests

class MultiInstructionTestGenerator:
    """Multi-Instruction Tests - Lange RAW Chains."""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        print("\n      → Generating long RAW chains...")
        
        # Für lange Ketten: Nur ALU-Operationen, keine Load/Store
        for length in [10, 20, 30]:
            # ADD-Kette
            add_chain = LatencyRAWChainGenerator.create_raw_chain(
                "add", all_insn["add"], "CLASS1_ALU", length, "mixed"
            )
            if add_chain:
                tests.append({
                    "name": f"LONG_RAW_ADD_{length}",
                    "safe_name": f"LONG_RAW_ADD_{length}",
                    "instructions": add_chain,
                    "iterations": 150,
                    "category": "CLASS1_ALU_LONG",
                    "instruction_count": length,
                    "description": f"Long RAW chain of {length} add instructions",
                    "test_group": "long_chains",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
            
            # XOR-Kette
            xor_chain = LatencyRAWChainGenerator.create_raw_chain(
                "xor", all_insn["xor"], "CLASS1_ALU", length, "mixed"
            )
            if xor_chain:
                tests.append({
                    "name": f"LONG_RAW_XOR_{length}",
                    "safe_name": f"LONG_RAW_XOR_{length}",
                    "instructions": xor_chain,
                    "iterations": 150,
                    "category": "CLASS1_ALU_LONG",
                    "instruction_count": length,
                    "description": f"Long RAW chain of {length} xor instructions",
                    "test_group": "long_chains",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        return tests
# Alias für Kompatibilität
LatencyMultiGenerator = MultiInstructionTestGenerator