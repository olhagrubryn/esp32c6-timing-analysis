#!/usr/bin/env python3
# scripts/base/instructions.py - Gemeinsame Instruktionen-Datenbank

from typing import Dict, Set, List

class RISCVInstructions:
    """Zentrale Datenbank aller RISC-V Instruktionen."""
    
    @staticmethod
    def get_all_instructions() -> Dict[str, str]:
        """Alle verfügbaren Instruktionen."""
        return {
            # ALU Register-zu-Register
            "add":  "add {dst}, {src1}, {src2}",
            "sub":  "sub {dst}, {src1}, {src2}",
            "xor":  "xor {dst}, {src1}, {src2}",
            "or":   "or {dst}, {src1}, {src2}",
            "and":  "and {dst}, {src1}, {src2}",
            "sll":  "sll {dst}, {src1}, {src2}",
            "srl":  "srl {dst}, {src1}, {src2}",
            "sra":  "sra {dst}, {src1}, {src2}",
            "slt":  "slt {dst}, {src1}, {src2}",
            "sltu": "sltu {dst}, {src1}, {src2}",
            
            # ALU Immediate
            "addi":  "addi {dst}, {src1}, {imm}",
            "xori":  "xori {dst}, {src1}, {imm}",
            "ori":   "ori {dst}, {src1}, {imm}",
            "andi":  "andi {dst}, {src1}, {imm}",
            "slli":  "slli {dst}, {src1}, {imm}",
            "srli":  "srli {dst}, {src1}, {imm}",
            "srai":  "srai {dst}, {src1}, {imm}",
            "slti":  "slti {dst}, {src1}, {imm}",
            "sltiu": "sltiu {dst}, {src1}, {imm}",
            
            # Load/Store
            "lb":   "lb {dst}, 0({base})",
            "lh":   "lh {dst}, 0({base})",
            "lw":   "lw {dst}, 0({base})",
            "lbu":  "lbu {dst}, 0({base})",
            "lhu":  "lhu {dst}, 0({base})",
            "sb":   "sb {src}, 0({base})",
            "sh":   "sh {src}, 0({base})",
            "sw":   "sw {src}, 0({base})",
            
            # Multiplikation/Division
            "mul":   "mul {dst}, {src1}, {src2}",
            "mulh":  "mulh {dst}, {src1}, {src2}",
            "mulhu": "mulhu {dst}, {src1}, {src2}",
            "div":   "div {dst}, {src1}, {src2}",
            "divu":  "divu {dst}, {src1}, {src2}",
            "rem":   "rem {dst}, {src1}, {src2}",
            "remu":  "remu {dst}, {src1}, {src2}",
        }
    
    @staticmethod
    def get_instructions_by_category() -> Dict[str, Set[str]]:
        """Instruktionen nach Kategorien gruppiert."""
        all_insn = RISCVInstructions.get_all_instructions()
        return {
            "REG2REG": {name for name in all_insn if name in 
                       ["add", "sub", "xor", "or", "and", "sll", "srl", "sra", "slt", "sltu"]},
            "IMMEDIATE": {name for name in all_insn if name in 
                         ["addi", "xori", "ori", "andi", "slli", "srli", "srai", "slti", "sltiu"]},
            "LOAD": {name for name in all_insn if name in ["lb", "lh", "lw", "lbu", "lhu"]},
            "STORE": {name for name in all_insn if name in ["sb", "sh", "sw"]},
            "DIV_MUL": {name for name in all_insn if name in 
                       ["mul", "mulh", "mulhu", "div", "divu", "rem", "remu"]}
        }
    
    @staticmethod
    def get_valid_immediate_range(insn_name: str) -> List[int]:
        """Gültige Immediate-Werte für eine Instruktion."""
        if insn_name in ["slli", "srli", "srai"]:
            return [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 15, 16, 24, 31]
        elif insn_name in ["addi", "xori", "ori", "andi", "slti", "sltiu"]:
            return [0, 1, 2, 4, 8, 16, 32, 64, 128, 255, 256, 511, 1023, 2047]
        return [0, 1, 2, 4, 8, 16, 32, 64]