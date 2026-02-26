#!/usr/bin/env python3
# scripts/base/instructions.py - Gemeinsame Instruktionen-Datenbank mit 8 Klassen

from typing import Dict, Set, List, Tuple

class RISCVInstructions:
    """Zentrale Datenbank aller RISC-V Instruktionen - 8 Klassen nach Methodik."""
    
    @staticmethod
    def get_all_instructions() -> Dict[str, str]:
        """Alle verfügbaren Instruktionen."""
        return {
            # === Class 1: ALU Operations (Arithmetic Logic Unit) ===
            "add":  "add {dst}, {src1}, {src2}",
            "sub":  "sub {dst}, {src1}, {src2}",
            "xor":  "xor {dst}, {src1}, {src2}",
            "or":   "or {dst}, {src1}, {src2}",
            "and":  "and {dst}, {src1}, {src2}",
            "slt":  "slt {dst}, {src1}, {src2}",
            "sltu": "sltu {dst}, {src1}, {src2}",
            
            # === Class 2: Shift Operations (Barrel Shifter) ===
            "sll":  "sll {dst}, {src1}, {src2}",
            "srl":  "srl {dst}, {src1}, {src2}",
            "sra":  "sra {dst}, {src1}, {src2}",
            
            # === Class 3: Multiplication (M-Extension) ===
            "mul":   "mul {dst}, {src1}, {src2}",
            "mulh":  "mulh {dst}, {src1}, {src2}",
            "mulhu": "mulhu {dst}, {src1}, {src2}",
            "mulhsu": "mulhsu {dst}, {src1}, {src2}",
            
            # === Class 4: Division (M-Extension) ===
            "div":   "div {dst}, {src1}, {src2}",
            "divu":  "divu {dst}, {src1}, {src2}",
            "rem":   "rem {dst}, {src1}, {src2}",
            "remu":  "remu {dst}, {src1}, {src2}",
            
            # === Class 5: Load Operations (Memory → Register) ===
            "lb":   "lb {dst}, 0({base})",
            "lh":   "lh {dst}, 0({base})",
            "lw":   "lw {dst}, 0({base})",
            "lbu":  "lbu {dst}, 0({base})",
            "lhu":  "lhu {dst}, 0({base})",
            
            # === Class 6: Store Operations (Register → Memory) ===
            "sb":   "sb {src}, 0({base})",
            "sh":   "sh {src}, 0({base})",
            "sw":   "sw {src}, 0({base})",
            
            # === Class 7: Immediate Operations (I-Type) ===
            "addi":  "addi {dst}, {src1}, {imm}",
            "xori":  "xori {dst}, {src1}, {imm}",
            "ori":   "ori {dst}, {src1}, {imm}",
            "andi":  "andi {dst}, {src1}, {imm}",
            "slli":  "slli {dst}, {src1}, {imm}",
            "srli":  "srli {dst}, {src1}, {imm}",
            "srai":  "srai {dst}, {src1}, {imm}",
            "slti":  "slti {dst}, {src1}, {imm}",
            "sltiu": "sltiu {dst}, {src1}, {imm}",
        }
    
    @staticmethod
    def get_instructions_by_class() -> Dict[str, Set[str]]:
        """Instruktionen nach den 8 Klassen aus der Methodik gruppiert."""
        all_insn = RISCVInstructions.get_all_instructions()
        return {
            "CLASS1_ALU": {"add", "sub", "xor", "or", "and", "slt", "sltu"},
            "CLASS2_SHIFT": {"sll", "srl", "sra"},
            "CLASS3_MUL": {"mul", "mulh", "mulhu", "mulhsu"},
            "CLASS4_DIV": {"div", "divu", "rem", "remu"},
            "CLASS5_LOAD": {"lb", "lh", "lw", "lbu", "lhu"},
            "CLASS6_STORE": {"sb", "sh", "sw"},
            "CLASS7_IMMEDIATE": {"addi", "xori", "ori", "andi", "slli", "srli", "srai", "slti", "sltiu"},
        }
    
    @staticmethod
    def get_mixed_classes() -> List[Tuple[str, str, str]]:
        """Mixed Classes für Cross-Class Dependency Chains (Tabelle 4.1)."""
        return [
            ("CLASS1_ALU", "CLASS7_IMMEDIATE", "ALU vs Immediate - Einfluss der Operandenanzahl"),
            ("CLASS2_SHIFT", "CLASS1_ALU", "Shift → ALU - Dedizierter Shifter vs Shared ALU"),
            ("CLASS3_MUL", "CLASS4_DIV", "Multiply vs Divide - Multi-Cycle Vergleich"),
            ("CLASS5_LOAD", "CLASS1_ALU", "Load → ALU - Load-to-Use Latency"),
            ("CLASS5_LOAD", "CLASS1_ALU", "CLASS6_STORE", "Load → ALU → Store - Memory Update & Forwarding"),
            ("CLASS1_ALU", "CLASS8_BRANCH", "ALU + Branch - Compute/Control-Flow Interaktion"),
        ]
    
    @staticmethod
    def get_valid_immediate_range(insn_name: str) -> List[int]:
        """Gültige Immediate-Werte für eine Instruktion."""
        if insn_name in ["slli", "srli", "srai"]:
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 15, 16, 24, 31]
        elif insn_name in ["addi", "xori", "ori", "andi", "slti", "sltiu"]:
            return [0, 1, 2, 4, 8, 16, 32, 64, 128, 255, 256, 511, 1023, 2047]
        return [0, 1, 2, 4, 8, 16, 32, 64]