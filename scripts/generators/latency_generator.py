#!/usr/bin/env python3
# scripts/generators/latency_generator.py - Latenz-spezifische Generatoren
# FIXED: Vollständige Implementierung aller Testtypen

import random
import sys
import os

# Absolute Imports statt relative
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions

# ============================================================================
# 1. SINGLE INSTRUCTION TESTS (1 Instruktion)
# ============================================================================

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
                            "description": f"Single {insn_name} to {dst}",
                            "test_group": "single"
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
                            "description": f"Single {insn_name} from {src}",
                            "test_group": "single"
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
                        "description": f"Single {insn_name} imm={imm}",
                        "test_group": "single"
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
                        "description": f"Single {insn_name} {comb_name}",
                        "test_group": "single"
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

# ============================================================================
# 2. SEQUENCE TESTS (2-6 Instruktionen)
# ============================================================================

class SequenceTestGenerator:
    """Kurze Sequenz-Tests (2-6 Instruktionen)."""
    
    @staticmethod
    def generate_all():
        tests = []
        
        print("\n      → Generating dependency chains...")
        tests.extend(SequenceTestGenerator._generate_dependency_chains())
        
        print("      → Generating instruction mixes...")
        tests.extend(SequenceTestGenerator._generate_instruction_mixes())
        
        print("      → Generating random sequences...")
        tests.extend(SequenceTestGenerator._generate_random_sequences())
        
        print("      → Generating register stress tests...")
        tests.extend(SequenceTestGenerator._generate_register_stress())
        
        print("      → Generating memory access patterns...")
        tests.extend(SequenceTestGenerator._generate_memory_patterns())
        
        return tests
    
    @staticmethod
    def _generate_dependency_chains():
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
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
                            "description": f"Dependency chain of {length} {insn_name}",
                            "test_group": "chains"
                        })
        return tests
    
    @staticmethod
    def _generate_instruction_mixes():
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        for category, insn_set in categories.items():
            insn_list = sorted(list(insn_set))
            for length in [2, 3, 4]:
                if len(insn_list) >= length:
                    test = SequenceTestGenerator._create_mix_test(
                        insn_list[:length], category, f"{category}_mix{length}"
                    )
                    if test:
                        tests.append(test)
        return tests
    
    @staticmethod
    def _generate_random_sequences():
        tests = []
        categories = RISCVInstructions.get_instructions_by_category()
        
        for category in categories.keys():
            num_random = 5 if category in ["LOAD", "STORE"] else 10
            for i in range(num_random):
                seq = SequenceTestGenerator._generate_random(category)
                if seq:
                    tests.append({
                        "name": f"RAND_{category}_{i+1:03d}",
                        "safe_name": f"RAND_{category}_{i+1:03d}",
                        "instructions": seq,
                        "iterations": 200 if category == "DIV_MUL" else 300,
                        "category": category,
                        "instruction_count": len(seq),
                        "description": f"Random sequence #{i+1} of {len(seq)} {category} instr",
                        "test_group": "random"
                    })
        return tests
    
    @staticmethod
    def _generate_register_stress():
        tests = []
        
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
                    tests.append({
                        "name": f"STRESS_{category}_reg{reg_count}",
                        "safe_name": f"STRESS_{category}_reg{reg_count}",
                        "instructions": instructions,
                        "iterations": 200,
                        "category": category,
                        "instruction_count": len(instructions),
                        "description": f"Register stress test with {reg_count} registers",
                        "test_group": "stress"
                    })
        return tests
    
    @staticmethod
    def _generate_memory_patterns():
        tests = []
        
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
                    tests.append({
                        "name": f"MEM_{pattern}_{count}",
                        "safe_name": f"MEM_{pattern}_{count}",
                        "instructions": instructions,
                        "iterations": 200,
                        "category": "LOAD",
                        "instruction_count": len(instructions),
                        "description": f"{pattern} memory access ({count} loads)",
                        "test_group": "memory"
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
    
    @staticmethod
    def _create_mix_test(insn_list, category, name_suffix):
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
                    else:
                        dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                        src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                        src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                        instructions.append((insn_name, instr))
                except:
                    continue
        
        if not instructions:
            return None
            
        iterations = 200 if category in ["LOAD", "STORE"] else (100 if category == "DIV_MUL" else 300)
        
        return {
            "name": f"SEQ_{name_suffix}",
            "safe_name": f"SEQ_{name_suffix}",
            "instructions": instructions,
            "iterations": iterations,
            "category": category,
            "instruction_count": len(instructions),
            "description": f"Sequence mix of {len(instructions)} {category} instr",
            "test_group": "sequences"
        }

# ============================================================================
# 3. MULTI-INSTRUCTION TESTS (10-30 Instruktionen)
# ============================================================================

class MultiInstructionTestGenerator:
    """Multi-Instruction Tests (10-30 Instruktionen)."""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        categories = RISCVInstructions.get_instructions_by_category()
        counts = [10, 20, 30]
        
        print("\n      → Generating LOAD multi tests...")
        tests.extend(MultiInstructionTestGenerator._generate_load_tests(counts))
        
        print("      → Generating STORE multi tests...")
        tests.extend(MultiInstructionTestGenerator._generate_store_tests(counts))
        
        print("      → Generating IMMEDIATE multi tests...")
        tests.extend(MultiInstructionTestGenerator._generate_immediate_tests(all_insn, counts))
        
        print("      → Generating REG2REG multi tests...")
        tests.extend(MultiInstructionTestGenerator._generate_reg2reg_tests(all_insn, counts))
        
        print("      → Generating DIV_MUL multi tests...")
        tests.extend(MultiInstructionTestGenerator._generate_divmul_tests(all_insn, [10, 20]))
        
        return tests
    
    @staticmethod
    def _generate_load_tests(counts):
        tests = []
        load_insns = ["lw", "lh", "lb", "lbu", "lhu"]
        
        for insn_name in load_insns[:2]:  # lw, lh
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
                        "category": "LOAD_MULTI",
                        "instruction_count": count,
                        "description": f"Multi {count}x {insn_name} loads",
                        "test_group": "multi"
                    })
        return tests
    
    @staticmethod
    def _generate_store_tests(counts):
        tests = []
        store_insns = ["sw", "sh", "sb"]
        
        for insn_name in store_insns[:2]:  # sw, sh
            for src in RISCVRegisters.DST_REGS[:1]:
                for count in counts:
                    instrs = []
                    for i in range(count):
                        offset = (i * 4) % 32
                        instr = f"{insn_name} {src}, {offset}({RISCVRegisters.BASE_REG})"
                        instrs.append((insn_name, instr))
                    
                    tests.append({
                        "name": f"{insn_name}_multi{count}",
                        "safe_name": f"{insn_name}_multi{count}",
                        "instructions": instrs,
                        "iterations": 200,
                        "category": "STORE_MULTI",
                        "instruction_count": count,
                        "description": f"Multi {count}x {insn_name} stores",
                        "test_group": "multi"
                    })
        return tests
    
    @staticmethod
    def _generate_immediate_tests(all_insn, counts):
        tests = []
        imm_insns = ["addi", "xori", "ori", "andi"]
        
        for insn_name in imm_insns[:2]:  # addi, xori
            template = all_insn.get(insn_name, "")
            if not template:
                continue
                
            for count in counts:
                instrs = []
                for i in range(count):
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                    imm = (i * 2) % 256
                    instr = template.format(dst=dst, src1=src1, imm=imm)
                    instrs.append((insn_name, instr))
                
                tests.append({
                    "name": f"{insn_name}_multi{count}",
                    "safe_name": f"{insn_name}_multi{count}",
                    "instructions": instrs,
                    "iterations": 200,
                    "category": "IMMEDIATE_MULTI",
                    "instruction_count": count,
                    "description": f"Multi {count}x {insn_name}",
                    "test_group": "multi"
                })
        return tests
    
    @staticmethod
    def _generate_reg2reg_tests(all_insn, counts):
        tests = []
        reg_insns = ["add", "xor", "or", "and"]
        
        for insn_name in reg_insns[:2]:  # add, xor
            template = all_insn.get(insn_name, "")
            if not template:
                continue
                
            for count in counts:
                instrs = []
                for i in range(count):
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                    src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                    instrs.append((insn_name, instr))
                
                tests.append({
                    "name": f"{insn_name}_multi{count}",
                    "safe_name": f"{insn_name}_multi{count}",
                    "instructions": instrs,
                    "iterations": 200,
                    "category": "REG2REG_MULTI",
                    "instruction_count": count,
                    "description": f"Multi {count}x {insn_name}",
                    "test_group": "multi"
                })
        return tests
    
    @staticmethod
    def _generate_divmul_tests(all_insn, counts):
        tests = []
        divmul_insns = ["mul", "div"]
        
        for insn_name in divmul_insns:
            template = all_insn.get(insn_name, "")
            if not template:
                continue
                
            for count in counts:
                instrs = []
                for i in range(count):
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                    src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                    instr = template.format(dst=dst, src1=src1, src2=src2)
                    instrs.append((insn_name, instr))
                
                tests.append({
                    "name": f"{insn_name}_multi{count}",
                    "safe_name": f"{insn_name}_multi{count}",
                    "instructions": instrs,
                    "iterations": 100,
                    "category": "DIV_MUL_MULTI",
                    "instruction_count": count,
                    "description": f"Multi {count}x {insn_name}",
                    "test_group": "multi"
                })
        return tests

# ============================================================================
# 4. LONG SEQUENCE TESTS (20-50 Instruktionen)
# ============================================================================

class LongSequenceTestGenerator:
    """Lange Sequenz-Tests (20-50 Instruktionen)."""
    
    @staticmethod
    def generate_all():
        tests = []
        
        print("\n      → Generating LONG dependency chains...")
        tests.extend(LongSequenceTestGenerator._generate_long_chains())
        
        print("      → Generating LONG random sequences...")
        tests.extend(LongSequenceTestGenerator._generate_long_random())
        
        print("      → Generating MEMORY stress tests...")
        tests.extend(LongSequenceTestGenerator._generate_memory_stress())
        
        return tests
    
    @staticmethod
    def _generate_long_chains():
        tests = []
        
        for length in [20, 30, 40]:
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
                "category": "REG2REG_LONG",
                "instruction_count": length,
                "description": f"Long chain of {length} ALU ops",
                "test_group": "multi"
            })
        return tests
    
    @staticmethod
    def _generate_long_random():
        tests = []
        
        for length in [25, 35, 45]:
            chain = []
            for i in range(length):
                dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                src1 = RISCVRegisters.SRC_REGS[i % len(RISCVRegisters.SRC_REGS)]
                src2 = RISCVRegisters.SRC_REGS[(i+1) % len(RISCVRegisters.SRC_REGS)]
                op = random.choice(["add", "xor", "or", "and"])
                instr = f"{op} {dst}, {src1}, {src2}"
                chain.append((op, instr))
            
            tests.append({
                "name": f"LONG_RAND_{length}",
                "safe_name": f"LONG_RAND_{length}",
                "instructions": chain,
                "iterations": 150,
                "category": "REG2REG_LONG_RAND",
                "instruction_count": length,
                "description": f"Long random sequence of {length} ALU ops",
                "test_group": "multi"
            })
        return tests
    
    @staticmethod
    def _generate_memory_stress():
        tests = []
        
        patterns = ["sequential", "strided", "random"]
        for pattern in patterns:
            for count in [20, 30, 40]:
                instrs = []
                for i in range(count):
                    dst = RISCVRegisters.DST_REGS[i % len(RISCVRegisters.DST_REGS)]
                    
                    if pattern == "sequential":
                        offset = (i * 4) % 64
                    elif pattern == "strided":
                        offset = (i * 8) % 64
                    else:  # random
                        offset = random.choice([0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60])
                    
                    if i % 3 == 0:
                        instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    elif i % 3 == 1:
                        instr = f"lh {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    else:
                        instr = f"lb {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    
                    instrs.append(("load", instr))
                
                tests.append({
                    "name": f"MEM_STRESS_{pattern}_{count}",
                    "safe_name": f"MEM_STRESS_{pattern}_{count}",
                    "instructions": instrs,
                    "iterations": 150,
                    "category": "LOAD_STRESS",
                    "instruction_count": count,
                    "description": f"Memory stress {pattern} pattern with {count} accesses",
                    "test_group": "stress"
                })
        return tests