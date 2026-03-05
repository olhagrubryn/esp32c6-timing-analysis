#!/usr/bin/env python3
# scripts/generators/comparison_generator.py

import random
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class ComparisonTestGenerator:
    @staticmethod
    def generate_latency_for_divider_values():
        tests = []
        
        test_values = [2, 3, 7, 16, 32, 0x7FFFFFFF]
        
        for value in test_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            instructions = [("div", f"div {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}")]
            
            test = {
                "name": f"LATENCY_COMPARE_DIV_{value_type}_{value}",
                "safe_name": f"latency_compare_div_{value_type}_{value}",
                "instructions": instructions,
                "iterations": 5,
                "instruction_count": 1,
                "description": f"Latenz DIV mit Wert {value}",
                "category": "CLASS4_DIV_COMPARE",
                "test_group": "compare_latency",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test)
        
        return tests
    
    @staticmethod
    def generate_latency_for_throughput_comparison():
        tests = []
        
        test_values = [2, 7]
        
        for value in test_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            instructions_free = [("div", f"div {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}")]
            
            test_free = {
                "name": f"LATENCY_COMPARE_FREE_{value_type}_{value}",
                "safe_name": f"latency_compare_free_{value_type}_{value}",
                "instructions": instructions_free,
                "iterations": 5,
                "instruction_count": 1,
                "description": f"FREE DIV {value}",
                "category": "CLASS4_DIV_FREE",
                "test_group": "compare_latency_free",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test_free)
            
            instructions_dep = [
                ("div", f"div {RISCVRegisters.T0}, {RISCVRegisters.T1}, {RISCVRegisters.T2}"),
                ("div", f"div {RISCVRegisters.T1}, {RISCVRegisters.T0}, {RISCVRegisters.T3}")
            ]
            
            test_dep = {
                "name": f"LATENCY_COMPARE_DEP_{value_type}_{value}",
                "safe_name": f"latency_compare_dep_{value_type}_{value}",
                "instructions": instructions_dep,
                "iterations": 5,
                "instruction_count": 2,
                "description": f"DEP DIV {value}",
                "category": "CLASS4_DIV_DEP",
                "test_group": "compare_latency_dep",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test_dep)
        
        return tests