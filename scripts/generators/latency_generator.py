#!/usr/bin/env python3
# scripts/generators/latency_generator.py - OPTIMIERT FÜR GRÖßE (OHNE ITERATIONEN)

import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry


class LatencyRAWChainGenerator:
    """Korrekte RAW Dependency Chains laut Methodik-Kapitel."""
    
    @staticmethod
    def create_raw_chain(insn_name: str, insn_template: str, 
                        class_name: str, chain_length: int,
                        register_set: str = "mixed") -> list:
        """
        Erstellt eine echte RAW-Abhängigkeitskette:
        dest_i = f(src1_i, src2_i) mit src1_i = dest_{i-1}
        """
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
        
        # Erste Instruktion: unabhängige Quellregister
        if class_name in ["CLASS5_LOAD"]:
            base_reg = RISCVRegisters.BASE_REG
            dst = regs[0]
            offset = 0
            instr = insn_template.format(dst=dst, base=base_reg, offset=offset)
            instructions.append((insn_name, instr))
            last_dest = dst
            
        elif class_name in ["CLASS6_STORE"]:
            base_reg = RISCVRegisters.BASE_REG
            store_dst = regs[0]
            load_dst = regs[1]
            
            store_instr = insn_template.format(src=store_dst, base=base_reg, offset=0)
            instructions.append((insn_name, store_instr))
            instructions.append(("lw", f"lw {load_dst}, 0({base_reg})"))
            last_dest = load_dst
            
        elif class_name == "CLASS2_SHIFT":
            if chain_length < 2:
                return []
                
            shamt_reg = RISCVRegisters.T1
            instructions.append(("li", f"li {shamt_reg}, 1"))
            
            dst = regs[0]
            src = regs[1]
            instr = insn_template.format(dst=dst, src1=src, src2=shamt_reg)
            instructions.append((insn_name, instr))
            last_dest = dst
            
            for i in range(1, chain_length):
                dst = regs[i % len(regs)]
                instr = insn_template.format(dst=dst, src1=last_dest, src2=shamt_reg)
                instructions.append((insn_name, instr))
                last_dest = dst
                
        elif class_name in ["CLASS3_MUL", "CLASS4_DIV"]:
            for i in range(chain_length):
                if i == 0:
                    dst = regs[0]
                    src1 = regs[1]
                    src2 = regs[2]
                else:
                    dst = regs[i % len(regs)]
                    src1 = last_dest
                    src2 = regs[(i+2) % len(regs)]
                
                instr = insn_template.format(dst=dst, src1=src1, src2=src2)
                instructions.append((insn_name, instr))
                last_dest = dst
                
        else:  # CLASS1_ALU, CLASS7_IMMEDIATE
            for i in range(chain_length):
                if i == 0:
                    dst = regs[0]
                    src1 = regs[1]
                    src2 = regs[2]
                else:
                    dst = regs[i % len(regs)]
                    src1 = last_dest
                    src2 = regs[(i+2) % len(regs)]
                
                if class_name == "CLASS7_IMMEDIATE":
                    instr = insn_template.format(dst=dst, src1=src1, imm=1)
                else:
                    instr = insn_template.format(dst=dst, src1=src1, src2=src2)
                
                instructions.append((insn_name, instr))
                last_dest = dst
        
        return instructions


class Class1_ALU_Generator:
    """Klasse 1: ALU Operationen - REDUZIERTE SINGLES, MEHR RAW"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        alu_insns = ["add", "sub", "xor", "or", "and", "slt", "sltu"]
        
        print("\n      → Klasse 1: ALU Operationen...")
        
        for insn_name in alu_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            # ===== REDUZIERTE SINGLE TESTS =====
            # Nur 2 wichtigste Register-Kombinationen
            for comb_name in ["same_reg", "diff_reg"]:
                regs = RISCVRegisters.get_register_combinations()[comb_name]
                dst, src1, src2 = regs
                instr = tmpl.format(dst=dst, src1=src1, src2=src2)
                tests.append({
                    "name": f"CLASS1_{insn_name}_SINGLE_{comb_name}",
                    "safe_name": f"CLASS1_{insn_name}_SINGLE_{comb_name}",
                    "instructions": [(insn_name, instr)],
                    "category": "CLASS1_ALU_SINGLE",
                    "instruction_count": 1,
                    "description": f"Single {insn_name} {comb_name}",
                    "test_group": "single",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
            
            # ===== MEHR RAW CHAIN TESTS =====
            for length in [5, 8, 12, 15]:  # Längere Ketten
                for reg_set in ["mixed"]:  # Nur mixed für weniger Tests
                    chain = LatencyRAWChainGenerator.create_raw_chain(
                        insn_name, tmpl, "CLASS1_ALU", length, reg_set
                    )
                    if chain:
                        tests.append({
                            "name": f"CLASS1_{insn_name}_RAW{length}",
                            "safe_name": f"CLASS1_{insn_name}_RAW{length}",
                            "instructions": chain,
                            "category": "CLASS1_ALU_RAW",
                            "instruction_count": length,
                            "description": f"{insn_name} RAW chain length {length}",
                            "test_group": "raw_chains",
                            "type": "latency",
                            "test_value": -1,
                            "value_type": "NONE"
                        })
            
            # ===== ZERO IDIOM (nur ein Test pro insn) =====
            if insn_name in ["sub", "xor"]:
                instr = tmpl.format(dst=RISCVRegisters.T0, src1=RISCVRegisters.T0, src2=RISCVRegisters.T0)
                tests.append({
                    "name": f"CLASS1_{insn_name}_ZEROIDIOM",
                    "safe_name": f"CLASS1_{insn_name}_ZEROIDIOM",
                    "instructions": [(insn_name, instr)],
                    "category": "CLASS1_ALU_ZERO",
                    "instruction_count": 1,
                    "description": f"Zero idiom: {insn_name}",
                    "test_group": "zero_idioms",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        return tests


class Class2_Shift_Generator:
    """Klasse 2: Shift Operationen - REDUZIERT"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        shift_insns = ["sll", "srl", "sra"]
        shift_amounts = [1, 4, 16, 31]  # Weniger Shift-Beträge
        
        print("\n      → Klasse 2: Shift Operationen...")
        
        for insn_name in shift_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            for shamt in shift_amounts:
                # ===== EIN SINGLE TEST pro Shift =====
                instr = tmpl.format(dst=RISCVRegisters.T0, src1=RISCVRegisters.T1, src2=RISCVRegisters.T2)
                tests.append({
                    "name": f"CLASS2_{insn_name}_SHAMT{shamt}_SINGLE",
                    "safe_name": f"CLASS2_{insn_name}_SHAMT{shamt}_SINGLE",
                    "instructions": [
                        ("li", f"li {RISCVRegisters.T2}, {shamt}"),
                        (insn_name, instr)
                    ],
                    "category": "CLASS2_SHIFT_SINGLE",
                    "instruction_count": 2,
                    "description": f"Single {insn_name} shamt={shamt}",
                    "test_group": "single",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
                
                # ===== LÄNGERE RAW CHAINS =====
                for length in [4, 8]:  # Längere Ketten
                    instructions = [
                        ("li", f"li {RISCVRegisters.T1}, {shamt}"),
                    ]
                    
                    last_dest = RISCVRegisters.T0
                    for i in range(length):
                        dst = RISCVRegisters.T3 if i % 2 == 0 else RISCVRegisters.T4
                        if i == 0:
                            src1 = RISCVRegisters.T2
                        else:
                            src1 = last_dest
                        instr = tmpl.format(dst=dst, src1=src1, src2=RISCVRegisters.T1)
                        instructions.append((insn_name, instr))
                        last_dest = dst
                    
                    tests.append({
                        "name": f"CLASS2_{insn_name}_SHAMT{shamt}_RAW{length}",
                        "safe_name": f"CLASS2_{insn_name}_SHAMT{shamt}_RAW{length}",
                        "instructions": instructions,
                        "category": "CLASS2_SHIFT_RAW",
                        "instruction_count": length + 1,
                        "description": f"{insn_name} shamt={shamt} RAW{length}",
                        "test_group": "shift",
                        "type": "latency",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        return tests


class Class3_Mul_Generator:
    """Klasse 3: Multiplikation - REDUZIERTE SINGLES, MEHR RAW"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        mul_insns = ["mul", "mulh", "mulhu", "mulhsu"]
        
        print("\n      → Klasse 3: Multiplikation...")
        
        for insn_name in mul_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            # ===== EIN SINGLE TEST =====
            instr = tmpl.format(dst=RISCVRegisters.T0, src1=RISCVRegisters.T1, src2=RISCVRegisters.T2)
            tests.append({
                "name": f"CLASS3_{insn_name}_SINGLE",
                "safe_name": f"CLASS3_{insn_name}_SINGLE",
                "instructions": [(insn_name, instr)],
                "category": "CLASS3_MUL_SINGLE",
                "instruction_count": 1,
                "description": f"Single {insn_name}",
                "test_group": "single",
                "type": "latency",
                "test_value": -1,
                "value_type": "NONE"
            })
            
            # ===== LÄNGERE RAW CHAINS =====
            for length in [4, 6, 8]:
                chain = LatencyRAWChainGenerator.create_raw_chain(
                    insn_name, tmpl, "CLASS3_MUL", length, "mixed"
                )
                if chain:
                    tests.append({
                        "name": f"CLASS3_{insn_name}_RAW{length}",
                        "safe_name": f"CLASS3_{insn_name}_RAW{length}",
                        "instructions": chain,
                        "category": "CLASS3_MUL_RAW",
                        "instruction_count": length,
                        "description": f"{insn_name} RAW chain length {length}",
                        "test_group": "mul",
                        "type": "latency",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        return tests


class Class4_Div_Generator:
    """Klasse 4: Division - WERTABHÄNGIGKEIT BEIBEHALTEN"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        div_insns = ["div", "divu", "rem", "remu"]
        
        print("\n      → Klasse 4: Division/Remainder...")
        
        # Repräsentative Werte (weniger als vorher)
        test_values = [
            (2, "HIGH"), (8, "HIGH"),
            (7, "LOW"), (13, "LOW"),
            (0, "EDGE"), (0x7FFFFFFF, "EDGE")
        ]
        
        for insn_name in div_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            for val, vtype in test_values:
                # ===== EIN SINGLE TEST pro Wert =====
                instr = tmpl.format(dst=RISCVRegisters.T0, src1=RISCVRegisters.T1, src2=RISCVRegisters.T2)
                tests.append({
                    "name": f"CLASS4_{insn_name}_{vtype}_{val}_SINGLE",
                    "safe_name": f"CLASS4_{insn_name}_{vtype}_{val}_SINGLE",
                    "instructions": [
                        ("li", f"li {RISCVRegisters.T1}, {val}"),
                        ("li", f"li {RISCVRegisters.T2}, 2"),
                        (insn_name, instr)
                    ],
                    "category": "CLASS4_DIV_SINGLE",
                    "instruction_count": 3,
                    "description": f"{insn_name} val={val}",
                    "test_group": "single",
                    "type": "latency",
                    "test_value": val,
                    "value_type": vtype
                })
                
                # ===== RAW CHAIN mit Wert =====
                instructions = [
                    ("li", f"li {RISCVRegisters.T1}, {val}"),
                    ("li", f"li {RISCVRegisters.T2}, 2"),
                    (insn_name, tmpl.format(dst=RISCVRegisters.T0, src1=RISCVRegisters.T1, src2=RISCVRegisters.T2)),
                    (insn_name, tmpl.format(dst=RISCVRegisters.T3, src1=RISCVRegisters.T0, src2=RISCVRegisters.T2)),
                    (insn_name, tmpl.format(dst=RISCVRegisters.T4, src1=RISCVRegisters.T3, src2=RISCVRegisters.T2)),
                ]
                
                tests.append({
                    "name": f"CLASS4_{insn_name}_{vtype}_{val}_RAW3",
                    "safe_name": f"CLASS4_{insn_name}_{vtype}_{val}_RAW3",
                    "instructions": instructions,
                    "category": "CLASS4_DIV_RAW",
                    "instruction_count": 5,
                    "description": f"{insn_name} val={val} RAW3",
                    "test_group": "div",
                    "type": "latency",
                    "test_value": val,
                    "value_type": vtype
                })
        
        return tests


class Class5_Load_Generator:
    """Klasse 5: Load Operationen - REDUZIERTE SINGLES, MEHR RAW"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        load_insns = ["lb", "lh", "lw", "lbu", "lhu"]
        offsets = [0, 8, 16, 24, 32, 60]  # Weniger offsets
        
        print("\n      → Klasse 5: Load Operationen...")
        
        for insn_name in load_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            for offset in offsets:
                # ===== EIN SINGLE TEST =====
                instr = tmpl.format(dst=RISCVRegisters.A2, base=RISCVRegisters.BASE_REG, offset=offset)
                tests.append({
                    "name": f"CLASS5_{insn_name}_OFF{offset}_SINGLE",
                    "safe_name": f"CLASS5_{insn_name}_OFF{offset}_SINGLE",
                    "instructions": [(insn_name, instr)],
                    "category": "CLASS5_LOAD_SINGLE",
                    "instruction_count": 1,
                    "description": f"Single {insn_name} offset {offset}",
                    "test_group": "single",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
                
                # ===== LÄNGERE LOAD CHAINS =====
                # Load-to-Use mit verschiedenen ALU-Ops
                for use_op in ["add", "xor"]:
                    instructions = [
                        (insn_name, tmpl.format(dst=RISCVRegisters.A2, base=RISCVRegisters.BASE_REG, offset=offset)),
                        (use_op, f"{use_op} {RISCVRegisters.A4}, {RISCVRegisters.A2}, {RISCVRegisters.A5}"),
                        (insn_name, tmpl.format(dst=RISCVRegisters.A6, base=RISCVRegisters.BASE_REG, offset=offset+4)),
                    ]
                    tests.append({
                        "name": f"CLASS5_{insn_name}_OFF{offset}_TO_{use_op}",
                        "safe_name": f"CLASS5_{insn_name}_OFF{offset}_TO_{use_op}",
                        "instructions": instructions,
                        "category": "CLASS5_LOAD_RAW",
                        "instruction_count": 3,
                        "description": f"{insn_name} → {use_op}",
                        "test_group": "load",
                        "type": "latency",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        return tests


class Class6_Store_Generator:
    """Klasse 6: Store Operationen - REDUZIERT"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        store_insns = ["sb", "sh", "sw"]
        offsets = [0, 8, 16, 24]  # Weniger offsets
        
        print("\n      → Klasse 6: Store Operationen...")
        
        for insn_name in store_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            for offset in offsets:
                # ===== EIN SINGLE TEST =====
                instr = tmpl.format(src=RISCVRegisters.A2, base=RISCVRegisters.BASE_REG, offset=offset)
                tests.append({
                    "name": f"CLASS6_{insn_name}_OFF{offset}_SINGLE",
                    "safe_name": f"CLASS6_{insn_name}_OFF{offset}_SINGLE",
                    "instructions": [
                        ("li", f"li {RISCVRegisters.A2}, 0x12345678"),
                        (insn_name, instr)
                    ],
                    "category": "CLASS6_STORE_SINGLE",
                    "instruction_count": 2,
                    "description": f"Single {insn_name} offset {offset}",
                    "test_group": "single",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
                
                # ===== STORE-LOAD FORWARDING =====
                instructions = [
                    ("li", f"li {RISCVRegisters.A2}, 0x12345678"),
                    (insn_name, tmpl.format(src=RISCVRegisters.A2, base=RISCVRegisters.BASE_REG, offset=offset)),
                    ("lw", f"lw {RISCVRegisters.A4}, {offset}({RISCVRegisters.BASE_REG})"),
                    ("add", f"add {RISCVRegisters.A5}, {RISCVRegisters.A4}, {RISCVRegisters.A6}"),
                ]
                tests.append({
                    "name": f"CLASS6_{insn_name}_OFF{offset}_FORWARD",
                    "safe_name": f"CLASS6_{insn_name}_OFF{offset}_FORWARD",
                    "instructions": instructions,
                    "category": "CLASS6_STORE_RAW",
                    "instruction_count": 4,
                    "description": f"{insn_name} forward",
                    "test_group": "store",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        return tests


class Class7_Immediate_Generator:
    """Klasse 7: Immediate Operationen - REDUZIERT"""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        imm_insns = ["addi", "xori", "ori", "andi", "slli", "srli", "srai", "slti", "sltiu"]
        
        print("\n      → Klasse 7: Immediate Operationen...")
        
        for insn_name in imm_insns:
            if insn_name not in all_insn:
                continue
                
            tmpl = all_insn[insn_name]
            
            # Representative Immediate-Werte
            if insn_name in ["slli", "srli", "srai"]:
                test_imms = [1, 8, 31]
            else:
                test_imms = [1, 16, 255, 2047]
            
            for imm in test_imms:
                # ===== EIN SINGLE TEST =====
                instr = tmpl.format(dst=RISCVRegisters.T0, src1=RISCVRegisters.T1, imm=imm)
                tests.append({
                    "name": f"CLASS7_{insn_name}_IMM{imm}_SINGLE",
                    "safe_name": f"CLASS7_{insn_name}_IMM{imm}_SINGLE",
                    "instructions": [(insn_name, instr)],
                    "category": "CLASS7_IMMEDIATE_SINGLE",
                    "instruction_count": 1,
                    "description": f"Single {insn_name} imm={imm}",
                    "test_group": "single",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
                
                # ===== LÄNGERE RAW CHAINS =====
                for length in [4, 6]:
                    instructions = []
                    last_dest = RISCVRegisters.T1
                    
                    for i in range(length):
                        dst = RISCVRegisters.T2 if i % 2 == 0 else RISCVRegisters.T3
                        if i == 0:
                            src = RISCVRegisters.T4
                        else:
                            src = last_dest
                        instr = tmpl.format(dst=dst, src1=src, imm=imm)
                        instructions.append((insn_name, instr))
                        last_dest = dst
                    
                    tests.append({
                        "name": f"CLASS7_{insn_name}_IMM{imm}_RAW{length}",
                        "safe_name": f"CLASS7_{insn_name}_IMM{imm}_RAW{length}",
                        "instructions": instructions,
                        "category": "CLASS7_IMMEDIATE_RAW",
                        "instruction_count": length,
                        "description": f"{insn_name} imm={imm} RAW{length}",
                        "test_group": "immediate",
                        "type": "latency",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        return tests


class Class9_Mixed_Per_Class_Generator:
    """
    Klasse 9: Mixed Operation Tests pro Klasse
    WENIGER VARIANTEN, LÄNGERE KETTEN
    """
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        print("\n      → Klasse 9: Mixed Operations (Lange Ketten)...")
        
        # ===== 1. ALU Mixed - LANGE KETTEN =====
        alu_ops = ["add", "xor", "or", "and", "sub"]
        for length in [8, 12, 16]:  # Längere Ketten
            ops = [alu_ops[i % len(alu_ops)] for i in range(length)]
            chain = Class9_Mixed_Per_Class_Generator._create_mixed_raw_chain(
                ops, all_insn, "CLASS1_ALU", length, "mixed"
            )
            if chain:
                tests.append({
                    "name": f"CLASS9_ALU_MIXED_L{length}",
                    "safe_name": f"CLASS9_ALU_MIXED_L{length}",
                    "instructions": chain,
                    "category": "CLASS9_MIXED_ALU",
                    "instruction_count": length,
                    "description": f"Mixed ALU RAW length {length}",
                    "test_group": "mixed_per_class",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        # ===== 2. Shift Mixed - LANGE KETTEN =====
        shift_ops = ["sll", "srl", "sra"]
        for shamt in [1, 8]:
            for length in [6, 10]:
                ops = [shift_ops[i % 3] for i in range(length)]
                chain = Class9_Mixed_Per_Class_Generator._create_mixed_raw_chain(
                    ops, all_insn, "CLASS2_SHIFT", length, "mixed", shamt=shamt
                )
                if chain:
                    tests.append({
                        "name": f"CLASS9_SHIFT_S{shamt}_L{length}",
                        "safe_name": f"CLASS9_SHIFT_S{shamt}_L{length}",
                        "instructions": chain,
                        "category": "CLASS9_MIXED_SHIFT",
                        "instruction_count": length,
                        "description": f"Mixed Shift RAW shamt={shamt} len={length}",
                        "test_group": "mixed_per_class",
                        "type": "latency",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        # ===== 3. Mul Mixed - LANGE KETTEN =====
        mul_ops = ["mul", "mulh", "mulhu"]
        for length in [5, 8]:
            ops = [mul_ops[i % 3] for i in range(length)]
            chain = Class9_Mixed_Per_Class_Generator._create_mixed_raw_chain(
                ops, all_insn, "CLASS3_MUL", length, "mixed"
            )
            if chain:
                tests.append({
                    "name": f"CLASS9_MUL_MIXED_L{length}",
                    "safe_name": f"CLASS9_MUL_MIXED_L{length}",
                    "instructions": chain,
                    "category": "CLASS9_MIXED_MUL",
                    "instruction_count": length,
                    "description": f"Mixed Mul RAW length {length}",
                    "test_group": "mixed_per_class",
                    "type": "latency",
                    "test_value": -1,
                    "value_type": "NONE"
                })
        
        # ===== 4. Div Mixed - REPRÄSENTATIVE WERTE =====
        div_ops = ["div", "divu", "rem", "remu"]
        for val, vtype in [(2, "HIGH"), (7, "LOW"), (0, "EDGE")]:
            for length in [4, 6]:
                ops = [div_ops[i % 4] for i in range(length)]
                chain = Class9_Mixed_Per_Class_Generator._create_mixed_raw_chain(
                    ops, all_insn, "CLASS4_DIV", length, "mixed", value=val
                )
                if chain:
                    tests.append({
                        "name": f"CLASS9_DIV_{vtype}_{val}_L{length}",
                        "safe_name": f"CLASS9_DIV_{vtype}_{val}_L{length}",
                        "instructions": chain,
                        "category": "CLASS9_MIXED_DIV",
                        "instruction_count": length,
                        "description": f"Mixed Div val={val} len={length}",
                        "test_group": "mixed_per_class",
                        "type": "latency",
                        "test_value": val,
                        "value_type": vtype
                    })
        
        # ===== 5. Load Mixed - LANGE KETTEN =====
        load_ops = ["lw", "lh", "lb"]
        for length in [6, 10]:
            chain = []
            for i in range(length):
                op = load_ops[i % 3]
                dst = RISCVRegisters.A2 if i % 2 == 0 else RISCVRegisters.A4
                offset = (i * 4) % 64
                instr = all_insn[op].format(dst=dst, base=RISCVRegisters.BASE_REG, offset=offset)
                chain.append((op, instr))
            tests.append({
                "name": f"CLASS9_LOAD_MIXED_L{length}",
                "safe_name": f"CLASS9_LOAD_MIXED_L{length}",
                "instructions": chain,
                "category": "CLASS9_MIXED_LOAD",
                "instruction_count": length,
                "description": f"Mixed Load length {length}",
                "test_group": "mixed_per_class",
                "type": "latency",
                "test_value": -1,
                "value_type": "NONE"
            })
        
        # ===== 6. Store Mixed - LANGE KETTEN =====
        store_ops = ["sw", "sh", "sb"]
        for length in [5, 8]:
            chain = [("li", f"li {RISCVRegisters.A2}, 0x12345678")]
            for i in range(length):
                op = store_ops[i % 3]
                offset = (i * 4) % 64
                instr = all_insn[op].format(src=RISCVRegisters.A2, base=RISCVRegisters.BASE_REG, offset=offset)
                chain.append((op, instr))
            tests.append({
                "name": f"CLASS9_STORE_MIXED_L{length}",
                "safe_name": f"CLASS9_STORE_MIXED_L{length}",
                "instructions": chain,
                "category": "CLASS9_MIXED_STORE",
                "instruction_count": length + 1,
                "description": f"Mixed Store length {length}",
                "test_group": "mixed_per_class",
                "type": "latency",
                "test_value": -1,
                "value_type": "NONE"
            })
        
        # ===== 7. Immediate Mixed - LANGE KETTEN =====
        imm_ops = ["addi", "xori", "ori", "andi"]
        for imm in [1, 127, 2047]:
            for length in [6, 10]:
                ops = [imm_ops[i % 4] for i in range(length)]
                chain = Class9_Mixed_Per_Class_Generator._create_mixed_raw_chain(
                    ops, all_insn, "CLASS7_IMMEDIATE", length, "mixed", imm=imm
                )
                if chain:
                    tests.append({
                        "name": f"CLASS9_IMM_{imm}_L{length}",
                        "safe_name": f"CLASS9_IMM_{imm}_L{length}",
                        "instructions": chain,
                        "category": "CLASS9_MIXED_IMMEDIATE",
                        "instruction_count": length,
                        "description": f"Mixed Immediate imm={imm} len={length}",
                        "test_group": "mixed_per_class",
                        "type": "latency",
                        "test_value": -1,
                        "value_type": "NONE"
                    })
        
        return tests
    
    @staticmethod
    def _create_mixed_raw_chain(ops, all_insn, class_name, length, reg_set, value=None, imm=None, shamt=None):
        """Erstellt eine RAW-Kette mit verschiedenen Operationen"""
        
        regs = [RISCVRegisters.T0, RISCVRegisters.T1, RISCVRegisters.T2,
                RISCVRegisters.T3, RISCVRegisters.T4, RISCVRegisters.T5]
        
        instructions = []
        last_dest = None
        shamt_reg = RISCVRegisters.T6
        
        # Für Division: Werte setzen
        if class_name in ["CLASS4_DIV"] and value is not None:
            src1_val = regs[1]
            src2_val = regs[2]
            instructions.append(("li", f"li {src1_val}, {value}"))
            instructions.append(("li", f"li {src2_val}, 2"))
        
        # Für Shift: Shift-Betrag setzen
        if class_name in ["CLASS2_SHIFT"] and shamt is not None:
            instructions.append(("li", f"li {shamt_reg}, {shamt}"))
        
        for i in range(length):
            op = ops[i % len(ops)]
            tmpl = all_insn[op]
            dst = regs[i % len(regs)]
            
            if class_name in ["CLASS4_DIV"] and value is not None:
                if i == 0:
                    src1 = src1_val
                    src2 = src2_val
                else:
                    src1 = last_dest
                    src2 = regs[(i+2) % len(regs)]
                instr = tmpl.format(dst=dst, src1=src1, src2=src2)
                
            elif class_name in ["CLASS7_IMMEDIATE"] and imm is not None:
                if i == 0:
                    src1 = regs[(i+1) % len(regs)]
                else:
                    src1 = last_dest
                instr = tmpl.format(dst=dst, src1=src1, imm=imm)
                
            elif class_name in ["CLASS2_SHIFT"] and shamt is not None:
                if i == 0:
                    src1 = regs[(i+1) % len(regs)]
                    src2 = shamt_reg
                else:
                    src1 = last_dest
                    src2 = shamt_reg
                instr = tmpl.format(dst=dst, src1=src1, src2=src2)
                
            else:
                if i == 0:
                    src1 = regs[(i+1) % len(regs)]
                    src2 = regs[(i+2) % len(regs)]
                else:
                    src1 = last_dest
                    src2 = regs[(i+2) % len(regs)]
                instr = tmpl.format(dst=dst, src1=src1, src2=src2)
            
            instructions.append((op, instr))
            last_dest = dst
        
        return instructions