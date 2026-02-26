#!/usr/bin/env python3
# scripts/generators/throughput_generator.py - Durchsatz-spezifische Generatoren

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class ThroughputBaseGenerator:
    """Basis-Throughput-Tests (unabhängige Instruktionen)."""
    
    @staticmethod
    def _get_throughput_category(insn_name: str) -> str:
        """Bestimmt die Durchsatz-Kategorie einer Instruktion."""
        if insn_name in ["lw", "lh", "lb", "lbu", "lhu", "sw", "sb", "sh"]:
            return "THROUGHPUT_MEMORY"
        elif insn_name in ["mul", "mulh", "mulhu", "div", "divu", "rem", "remu"]:
            return "THROUGHPUT_MULTI_CYCLE"
        else:
            return "THROUGHPUT_SINGLE_ISSUE"
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        for insn_name, template in all_insn.items():
            if insn_name == "div":
                continue
                
            for count in [4, 8, 16]:
                registers = RISCVRegisters.get_independent_registers(count)
                instructions = []
                
                for i in range(count):
                    dst = registers[i % len(registers)]
                    
                    if insn_name in ["lw", "lh", "lb", "lbu", "lhu"]:
                        base = RISCVRegisters.S0
                        instr = template.format(dst=dst, base=base)
                    
                    elif insn_name in ["sw", "sb", "sh"]:
                        base = RISCVRegisters.S0
                        instr = template.format(src=dst, base=base)
                    
                    elif insn_name in ["addi", "xori", "ori", "andi", "slli", "srli", "srai", "slti", "sltiu"]:
                        src1 = registers[(i + 1) % len(registers)]
                        instr = template.format(dst=dst, src1=src1, imm=1)
                    
                    elif insn_name in ["mul", "mulh", "mulhu", "div", "divu", "rem", "remu"]:
                        src1 = registers[(i + 1) % len(registers)]
                        src2 = registers[(i + 2) % len(registers)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                    
                    else:
                        src1 = registers[(i + 1) % len(registers)]
                        src2 = registers[(i + 2) % len(registers)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                    
                    instructions.append((insn_name, instr))
                
                # Verwende die lokale Methode statt RISCVInstructions
                category = ThroughputBaseGenerator._get_throughput_category(insn_name)
                
                tests.append({
                    "name": f"THROUGHPUT_{insn_name}_{count}",
                    "safe_name": f"THROUGHPUT_{insn_name}_{count}",
                    "instructions": instructions,
                    "iterations": max(1, 3000 // count),
                    "category": category,
                    "instruction_count": count,
                    "group": "throughput_base",
                    "test_value": -1,
                    "value_type": "NONE",
                    "type": "throughput"
                })
        
        return tests


class ThroughputDividerGenerator:
    """Divider-Tests mit verschiedenen Werten."""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        template = all_insn.get("div")
        if not template:
            print("WARNUNG: 'div' Instruktion nicht gefunden!")
            return tests
        
        for count in [4, 8, 16]:
            # HIGH Throughput
            for value in TestValueRegistry.HIGH_THROUGHPUT_VALUES:
                test = ThroughputDividerGenerator._create_test(
                    template, count, value, "HIGH"
                )
                tests.append(test)
            
            # LOW Throughput
            for value in TestValueRegistry.LOW_THROUGHPUT_VALUES:
                test = ThroughputDividerGenerator._create_test(
                    template, count, value, "LOW"
                )
                tests.append(test)
            
            # EDGE Cases
            for value in TestValueRegistry.EDGE_CASE_VALUES:
                test = ThroughputDividerGenerator._create_test(
                    template, count, value, "EDGE"
                )
                tests.append(test)
        
        return tests
    
    @staticmethod
    def _create_test(template, count, value, value_type):
        registers = RISCVRegisters.get_independent_registers(count)
        instructions = []
        
        for i in range(count):
            dst = registers[i % len(registers)]
            src1 = registers[(i + 1) % len(registers)]
            src2 = registers[(i + 2) % len(registers)]
            instr = template.format(dst=dst, src1=src1, src2=src2)
            instructions.append(("div", instr))
        
        return {
            "name": f"DIV_{value_type}_{value}_{count}",
            "safe_name": f"DIV_{value_type}_{value}_{count}",
            "instructions": instructions,
            "iterations": max(1, 2000 // count),
            "category": f"THROUGHPUT_DIVIDER_{value_type}",
            "instruction_count": count,
            "group": "throughput_divider",
            "test_value": value,
            "value_type": value_type,
            "type": "throughput"
        }


class ThroughputComparisonGenerator:
    """Vergleich: Dependency-Free vs Dependent."""
    
    @staticmethod
    def generate_all():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        template = all_insn.get("div")
        if not template:
            print("WARNUNG: 'div' Instruktion nicht gefunden!")
            return tests
        
        values = (TestValueRegistry.HIGH_THROUGHPUT_VALUES[:3] + 
                 TestValueRegistry.LOW_THROUGHPUT_VALUES[:3])
        
        for value in values:
            value_type = TestValueRegistry.get_value_category(value)
            
            # Dependency-Free (Throughput)
            free_test = ThroughputComparisonGenerator._create_test(
                template, value, value_type, free=True
            )
            tests.append(free_test)
            
            # Dependent (Latency - gleicher Wert!)
            dep_test = ThroughputComparisonGenerator._create_test(
                template, value, value_type, free=False
            )
            tests.append(dep_test)
        
        return tests
    
    @staticmethod
    def _create_test(template, value, value_type, free=True):
        count = 8
        instructions = []
        
        if free:
            # Dependency-Free
            registers = RISCVRegisters.get_independent_registers(count)
            for i in range(count):
                dst = registers[i % len(registers)]
                src1 = registers[(i + 1) % len(registers)]
                src2 = registers[(i + 2) % len(registers)]
                instr = template.format(dst=dst, src1=src1, src2=src2)
                instructions.append(("div", instr))
            
            name_suffix = "FREE"
            group = "throughput_compare_free"
            category = "THROUGHPUT_COMPARE_FREE"
        else:
            # Dependent (RAW chain)
            last_dst = RISCVRegisters.T0
            for i in range(count):
                dst = RISCVRegisters.CHAIN_REGS[i % len(RISCVRegisters.CHAIN_REGS)]
                src1 = last_dst
                src2 = RISCVRegisters.CHAIN_REGS[(i + 2) % len(RISCVRegisters.CHAIN_REGS)]
                instr = template.format(dst=dst, src1=src1, src2=src2)
                instructions.append(("div", instr))
                last_dst = dst
            
            name_suffix = "DEP"
            group = "throughput_compare_dep"
            category = "THROUGHPUT_COMPARE_DEP"
        
        return {
            "name": f"COMPARE_DIV_{name_suffix}_{value_type}_{value}",
            "safe_name": f"COMPARE_DIV_{name_suffix}_{value_type}_{value}",
            "instructions": instructions,
            "iterations": 1000,
            "category": category,
            "instruction_count": count,
            "group": group,
            "test_value": value,
            "value_type": value_type,
            "type": "throughput"
        }