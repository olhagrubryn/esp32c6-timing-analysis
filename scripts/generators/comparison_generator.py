#!/usr/bin/env python3
# scripts/generators/comparison_generator.py

from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class ComparisonTestGenerator:
    @staticmethod
    def generate_latency_for_divider_values():
        tests = []
        for value in [2,3,7,16,32,0x7FFFFFFF]:
            vtype = TestValueRegistry.get_value_category(value)
            tests.append({
                "name": f"LATENCY_COMPARE_DIV_{vtype}_{value}",
                "safe_name": f"latency_compare_div_{vtype}_{value}",
                "instructions": [("div", f"div {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}")],
                "iterations": 5, "instruction_count": 1, "description": f"Latenz DIV mit Wert {value}",
                "category": "CLASS4_DIV_COMPARE", "test_group": "compare_latency",
                "test_value": value, "value_type": vtype, "type": "latency_compare"
            })
        return tests
    
    @staticmethod
    def generate_latency_for_throughput_comparison():
        tests = []
        for value in [2,7]:
            vtype = TestValueRegistry.get_value_category(value)
            
            tests.append({
                "name": f"LATENCY_COMPARE_FREE_{vtype}_{value}",
                "safe_name": f"latency_compare_free_{vtype}_{value}",
                "instructions": [("div", f"div {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}")],
                "iterations": 5, "instruction_count": 1, "description": f"FREE DIV {value}",
                "category": "CLASS4_DIV_FREE", "test_group": "compare_latency_free",
                "test_value": value, "value_type": vtype, "type": "latency_compare"
            })
            
            tests.append({
                "name": f"LATENCY_COMPARE_DEP_{vtype}_{value}",
                "safe_name": f"latency_compare_dep_{vtype}_{value}",
                "instructions": [
                    ("div", f"div {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}"),
                    ("div", f"div {RISCVRegisters.T1}, {RISCVRegisters.T0}, {RISCVRegisters.T3}")
                ], "iterations": 5, "instruction_count": 2, "description": f"DEP DIV {value}",
                "category": "CLASS4_DIV_DEP", "test_group": "compare_latency_dep",
                "test_value": value, "value_type": vtype, "type": "latency_compare"
            })
        return tests