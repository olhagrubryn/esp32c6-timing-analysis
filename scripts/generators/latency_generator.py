#!/usr/bin/env python3
# scripts/generators/latency_generator.py - Latenz-spezifische Generatoren

import random
import sys
import os

# Absolute Imports statt relative
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions

class SingleInstructionTestGenerator:
    """Single-Instruction Tests (1 Instruktion)."""
    
    @staticmethod
    def generate_test_variations(insn_name, insn_template, category):
        tests = []
        
        if category in ["LOAD", "STORE"]:
            iterations = 500
            if category == "LOAD":
                for dst in RISCVRegisters.DST_REGS:
                    try:
                        instr = insn_template.format(dst=dst, base=RISCVRegisters.BASE_REG)
                        tests.append({
                            "name": f"{insn_name}_{dst}",
                            "safe_name": f"{insn_name}_{dst}",
                            "instructions": [(insn_name, instr)],
                            "iterations": iterations,
                            "category": category,
                            "instruction_count": 1,
                        })
                    except:
                        continue
            else:  # STORE
                for src in RISCVRegisters.DST_REGS:
                    try:
                        instr = insn_template.format(src=src, base=RISCVRegisters.BASE_REG)
                        tests.append({
                            "name": f"{insn_name}_{src}",
                            "safe_name": f"{insn_name}_{src}",
                            "instructions": [(insn_name, instr)],
                            "iterations": iterations,
                            "category": category,
                            "instruction_count": 1,
                        })
                    except:
                        continue
        
        elif category == "IMMEDIATE":
            iterations = 1000
            valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
            for imm in valid_imms[:6]:
                try:
                    instr = insn_template.format(dst="a2", src1="a4", imm=imm)
                    tests.append({
                        "name": f"{insn_name}_imm{imm}",
                        "safe_name": f"{insn_name}_imm{imm}",
                        "instructions": [(insn_name, instr)],
                        "iterations": iterations,
                        "category": category,
                        "instruction_count": 1,
                    })
                except:
                    pass
        
        elif category in ["REG2REG", "DIV_MUL"]:
            iterations = 1000 if category == "REG2REG" else 200
            reg_combs = RISCVRegisters.get_register_combinations()
            for comb_name, regs in reg_combs.items():
                dst, src1, src2 = regs
                try:
                    instr = insn_template.format(dst=dst, src1=src1, src2=src2)
                    tests.append({
                        "name": f"{insn_name}_{comb_name}",
                        "safe_name": f"{insn_name}_{comb_name}",
                        "instructions": [(insn_name, instr)],
                        "iterations": iterations,
                        "category": category,
                        "instruction_count": 1,
                    })
                except:
                    pass
        
        return tests
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        
        for category, insn_set in categories.items():
            for insn_name in sorted(insn_set):
                if insn_name in all_insn:
                    tests.extend(
                        SingleInstructionTestGenerator.generate_test_variations(
                            insn_name, all_insn[insn_name], category
                        )
                    )
        return tests


class SequenceTestGenerator:
    """Kurze Sequenz-Tests (2-6 Instruktionen)."""
    
    @staticmethod
    def generate_all():
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        # Dependency Chains
        for category, insn_set in categories.items():
            if category in ["LOAD", "STORE"]:
                continue
            for insn_name in sorted(insn_set)[:2]:
                for length in [3, 4]:
                    chain = SequenceTestGenerator._generate_chain(insn_name, category, length)
                    if chain:
                        tests.append({
                            "name": f"CHAIN_{insn_name}_{length}",
                            "safe_name": f"CHAIN_{insn_name}_{length}",
                            "instructions": chain,
                            "iterations": 200 if category == "DIV_MUL" else 300,
                            "category": category,
                            "instruction_count": len(chain),
                        })
        
        # Random Sequences
        for category in categories:
            for i in range(5 if category in ["LOAD", "STORE"] else 10):
                seq = SequenceTestGenerator._generate_random(category)
                if seq:
                    tests.append({
                        "name": f"RAND_{category}_{i+1:03d}",
                        "safe_name": f"RAND_{category}_{i+1:03d}",
                        "instructions": seq,
                        "iterations": 200 if category == "DIV_MUL" else 300,
                        "category": category,
                        "instruction_count": len(seq),
                    })
        
        return tests
    
    @staticmethod
    def _generate_chain(insn_name, category, length):
        instructions = []
        all_insn = RISCVInstructions.get_all_instructions()
        template = all_insn[insn_name]
        
        for i in range(length):
            if category in ["LOAD", "STORE"]:
                if category == "LOAD":
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    instr = template.format(dst=dst, base=RISCVRegisters.BASE_REG)
                else:
                    src = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    instr = template.format(src=src, base=RISCVRegisters.BASE_REG)
            elif category == "IMMEDIATE":
                dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                src1 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                valid_imms = RISCVInstructions.get_valid_immediate_range(insn_name)
                imm = valid_imms[i % len(valid_imms)]
                instr = template.format(dst=dst, src1=src1, imm=imm)
            else:
                if i == 0:
                    dst, src1, src2 = "a2", "a4", "a5"
                else:
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.DST_REGS[(i-1) % len(RISCVRegisters.DST_REGS)]
                    src2 = RISCVRegisters.SRC_REGS[(i+2) % len(RISCVRegisters.SRC_REGS)]
                instr = template.format(dst=dst, src1=src1, src2=src2)
            instructions.append((insn_name, instr))
        
        return instructions
    
    @staticmethod
    def _generate_random(category):
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        
        if category not in categories:
            return None
            
        insn_list = sorted(list(categories[category]))
        length = random.randint(3, 6)
        selected = random.sample(insn_list, min(length, len(insn_list)))
        instructions = []
        
        for i, insn_name in enumerate(selected):
            if insn_name in all_insn:
                template = all_insn[insn_name]
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
                else:
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                    src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                instructions.append((insn_name, instr))
        
        return instructions


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
                            tests.append({
                                "name": f"{insn_name}_multi{count}",
                                "safe_name": f"{insn_name}_multi{count}",
                                "instructions": instrs,
                                "iterations": 200,
                                "category": category,
                                "instruction_count": count,
                            })
        return tests


class LongSequenceTestGenerator:
    """Lange Sequenz-Tests (20-50 Instruktionen)."""
    
    @staticmethod
    def generate_all():
        tests = []
        
        for length in [20, 30, 40]:
            # Lange Dependency Chain
            chain = []
            for i in range(length):
                dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                if i == 0:
                    src1, src2 = "a4", "a5"
                else:
                    src1 = chain[-1][1].split()[1].rstrip(',')
                    src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                op = random.choice(["add", "xor"])
                instr = f"{op} {dst}, {src1}, {src2}"
                chain.append((op, instr))
            
            tests.append({
                "name": f"LONG_CHAIN_{length}",
                "safe_name": f"LONG_CHAIN_{length}",
                "instructions": chain,
                "iterations": 150,
                "category": "REG2REG",
                "instruction_count": length,
            })
        
        return tests