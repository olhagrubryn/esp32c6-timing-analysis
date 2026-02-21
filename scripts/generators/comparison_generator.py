#!/usr/bin/env python3
# scripts/generators/comparison_generator.py - Vergleichs-Tests Latenz vs Durchsatz

import random
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class ComparisonTestGenerator:
    @staticmethod
    def generate_latency_for_divider_values():
        tests = []
        
        # ALLE Werte aus TestValueRegistry verwenden
        all_values = (TestValueRegistry.HIGH_THROUGHPUT_VALUES + 
                     TestValueRegistry.LOW_THROUGHPUT_VALUES + 
                     TestValueRegistry.EDGE_CASE_VALUES)
        
        for value in all_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            instructions = [("div", "div a2, a4, a5")]
            
            test = {
                "name": f"LATENCY_COMPARE_DIV_{value_type}_{value}",
                "safe_name": f"latency_compare_div_{value_type}_{value}",
                "instructions": instructions,
                "iterations": 100,
                "instruction_count": 1,
                "description": f"Latenz DIV mit Wert {value} ({value_type})",
                "category": "COMPARE_LATENCY",
                "group": "compare_latency",
                "test_value": value,           # WICHTIG
                "value_type": value_type,      # WICHTIG
                "type": "latency_compare"      # Für Erkennung
            }
            tests.append(test)
        
        return tests
    
    @staticmethod
    def generate_latency_for_throughput_comparison():
        """Generiert Latenz-Tests für FREE vs DEP Vergleich (wie in Durchsatz)."""
        tests = []
        
        # Gleiche Werte wie in ThroughputComparisonGenerator
        all_values = (TestValueRegistry.HIGH_THROUGHPUT_VALUES[:3] + 
                     TestValueRegistry.LOW_THROUGHPUT_VALUES[:3])
        
        for value in all_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            # 1. FREE Variante (unabhängige Register)
            instructions_free = []
            registers = RISCVRegisters.get_independent_registers(4)
            for i in range(4):
                dst = registers[i % len(registers)]
                src1 = registers[(i + 1) % len(registers)]
                src2 = registers[(i + 2) % len(registers)]
                instructions_free.append(("div", f"div {dst}, {src1}, {src2}"))
            
            test_free = {
                "name": f"LATENCY_COMPARE_FREE_{value_type}_{value}",
                "safe_name": f"latency_compare_free_{value_type}_{value}",
                "instructions": instructions_free,
                "iterations": 50,
                "instruction_count": 4,
                "description": f"Latenz FREE DIV {value} ({value_type})",
                "category": "COMPARE_LATENCY_FREE",
                "group": "compare_latency_free",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test_free)
            
            # 2. DEP Variante (RAW-Kette)
            instructions_dep = []
            last_dst = "a2"
            for i in range(4):
                dst = RISCVRegisters.TEMP_REGS[i % len(RISCVRegisters.TEMP_REGS)]
                src1 = last_dst
                src2 = RISCVRegisters.TEMP_REGS[(i + 2) % len(RISCVRegisters.TEMP_REGS)]
                instructions_dep.append(("div", f"div {dst}, {src1}, {src2}"))
                last_dst = dst
            
            test_dep = {
                "name": f"LATENCY_COMPARE_DEP_{value_type}_{value}",
                "safe_name": f"latency_compare_dep_{value_type}_{value}",
                "instructions": instructions_dep,
                "iterations": 50,
                "instruction_count": 4,
                "description": f"Latenz DEP DIV {value} ({value_type})",
                "category": "COMPARE_LATENCY_DEP",
                "group": "compare_latency_dep",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test_dep)
        
        return tests