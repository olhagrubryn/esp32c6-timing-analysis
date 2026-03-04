#!/usr/bin/env python3
# scripts/generators/throughput_generator.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class ThroughputBaseGenerator:
    """Basis-Throughput-Tests."""
    
    @staticmethod
    def _get_category(insn_name: str) -> str:
        if insn_name in ["lw","lh","lb","lbu","lhu","sw","sb","sh"]: return "THROUGHPUT_MEMORY"
        if insn_name in ["mul","mulh","mulhu","div","divu","rem","remu"]: return "THROUGHPUT_MULTI_CYCLE"
        return "THROUGHPUT_SINGLE_ISSUE"
    
    @staticmethod
    def generate_all():
        tests, all_insn = [], RISCVInstructions.get_all_instructions()
        
        for insn_name, tmpl in all_insn.items():
            if insn_name == "div": continue
            for count in [4,8,16]:
                regs = RISCVRegisters.get_independent_registers(count)
                instrs = []
                
                for i in range(count):
                    dst = regs[i % len(regs)]
                    if insn_name in ["lw","lh","lb","lbu","lhu"]:
                        instrs.append((insn_name, tmpl.format(dst=dst, base=RISCVRegisters.S0)))
                    elif insn_name in ["sw","sb","sh"]:
                        instrs.append((insn_name, tmpl.format(src=dst, base=RISCVRegisters.S0)))
                    elif insn_name in ["addi","xori","ori","andi","slli","srli","srai","slti","sltiu"]:
                        src1 = regs[(i+1)%len(regs)]
                        instrs.append((insn_name, tmpl.format(dst=dst, src1=src1, imm=1)))
                    else:
                        src1, src2 = regs[(i+1)%len(regs)], regs[(i+2)%len(regs)]
                        instrs.append((insn_name, tmpl.format(dst=dst, src1=src1, src2=src2)))
                
                tests.append({
                    "name": f"THROUGHPUT_{insn_name}_{count}",
                    "safe_name": f"THROUGHPUT_{insn_name}_{count}",
                    "instructions": instrs, "iterations": max(1,3000//count),
                    "category": ThroughputBaseGenerator._get_category(insn_name),
                    "instruction_count": count, "group": "throughput_base",
                    "test_value": -1, "value_type": "NONE", "type": "throughput"
                })
        return tests


class ThroughputDividerGenerator:
    """Divider-Tests mit verschiedenen Werten."""
    
    @staticmethod
    def generate_all():
        tests = []
        tmpl = RISCVInstructions.get_all_instructions().get("div")
        if not tmpl: return tests
        
        for count in [4,8,16]:
            for values, vtype in [(TestValueRegistry.HIGH_THROUGHPUT_VALUES, "HIGH"),
                                  (TestValueRegistry.LOW_THROUGHPUT_VALUES, "LOW"),
                                  (TestValueRegistry.EDGE_CASE_VALUES, "EDGE")]:
                for value in values:
                    regs = RISCVRegisters.get_independent_registers(count)
                    instrs = [("div", tmpl.format(dst=regs[i%len(regs)], 
                             src1=regs[(i+1)%len(regs)], src2=regs[(i+2)%len(regs)])) for i in range(count)]
                    
                    tests.append({
                        "name": f"DIV_{vtype}_{value}_{count}",
                        "safe_name": f"DIV_{vtype}_{value}_{count}",
                        "instructions": instrs, "iterations": max(1,2000//count),
                        "category": f"THROUGHPUT_DIVIDER_{vtype}",
                        "instruction_count": count, "group": "throughput_divider",
                        "test_value": value, "value_type": vtype, "type": "throughput"
                    })
        return tests


class ThroughputComparisonGenerator:
    """FREE vs DEP Comparison."""
    
    @staticmethod
    def generate_all():
        tests = []
        tmpl = RISCVInstructions.get_all_instructions().get("div")
        if not tmpl: return tests
        
        values = TestValueRegistry.HIGH_THROUGHPUT_VALUES[:3] + TestValueRegistry.LOW_THROUGHPUT_VALUES[:3]
        
        for value in values:
            vtype = TestValueRegistry.get_value_category(value)
            count = 8
            
            # FREE
            regs = RISCVRegisters.get_independent_registers(count)
            free_instrs = [("div", tmpl.format(dst=regs[i%len(regs)], 
                           src1=regs[(i+1)%len(regs)], src2=regs[(i+2)%len(regs)])) for i in range(count)]
            
            tests.append({
                "name": f"COMPARE_DIV_FREE_{vtype}_{value}",
                "safe_name": f"COMPARE_DIV_FREE_{vtype}_{value}",
                "instructions": free_instrs, "iterations": 1000,
                "category": "THROUGHPUT_COMPARE_FREE",
                "instruction_count": count, "group": "throughput_compare_free",
                "test_value": value, "value_type": vtype, "type": "throughput"
            })
            
            # DEP
            last_dst, dep_instrs = RISCVRegisters.T0, []
            for i in range(count):
                dst = RISCVRegisters.CHAIN_REGS[i % len(RISCVRegisters.CHAIN_REGS)]
                dep_instrs.append(("div", tmpl.format(dst=dst, src1=last_dst, 
                                  src2=RISCVRegisters.CHAIN_REGS[(i+2)%len(RISCVRegisters.CHAIN_REGS)])))
                last_dst = dst
            
            tests.append({
                "name": f"COMPARE_DIV_DEP_{vtype}_{value}",
                "safe_name": f"COMPARE_DIV_DEP_{vtype}_{value}",
                "instructions": dep_instrs, "iterations": 1000,
                "category": "THROUGHPUT_COMPARE_DEP",
                "instruction_count": count, "group": "throughput_compare_dep",
                "test_value": value, "value_type": vtype, "type": "throughput"
            })
        return tests