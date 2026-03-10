#!/usr/bin/env python3
# scripts/generators/branch_generator.py
# KORRIGIERT: Alle Instruktionen in einem __asm__ Block

from base.registers import RISCVRegisters

class BranchTestGenerator:
    @staticmethod
    def generate_all():
        tests = []
        print("\n      → Generating branch tests...")

        # ------------------------------------------------------------
        # 1. jal - Unconditional jump and link
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_JAL",
            "safe_name": "BRANCH_JAL",
            "instructions": [
                ("jal", "jal ra, 1f\n1: nop")
            ],
            "iterations": 1000,
            "category": "BRANCH_UNCOND",
            "instruction_count": 2,
            "description": "Unconditional jump and link (jal)",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 2. jalr - Jump and link register
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_JALR",
            "safe_name": "BRANCH_JALR",
            "instructions": [
                ("la", f"la {RISCVRegisters.T0}, 1f\njalr ra, {RISCVRegisters.T0}, 0\n1: nop")
            ],
            "iterations": 1000,
            "category": "BRANCH_UNCOND",
            "instruction_count": 3,
            "description": "Jump and link register (jalr)",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 3. Branch never taken (beq mit unterschiedlichen Werten)
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_BEQ_NOT_TAKEN",
            "safe_name": "BRANCH_BEQ_NOT_TAKEN",
            "instructions": [
                ("li", f"li {RISCVRegisters.T0}, 1\nli {RISCVRegisters.T1}, 2\nbeq {RISCVRegisters.T0}, {RISCVRegisters.T1}, 1f\nnop\n1: nop")
            ],
            "iterations": 1000,
            "category": "BRANCH_COND_NOT_TAKEN",
            "instruction_count": 5,
            "description": "Conditional branch never taken",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 4. Branch always taken (beq mit gleichen Werten)
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_BEQ_TAKEN",
            "safe_name": "BRANCH_BEQ_TAKEN",
            "instructions": [
                ("li", f"li {RISCVRegisters.T0}, 1\nbeq {RISCVRegisters.T0}, {RISCVRegisters.T0}, 1f\nnop\n1: nop")
            ],
            "iterations": 1000,
            "category": "BRANCH_COND_TAKEN",
            "instruction_count": 4,
            "description": "Conditional branch always taken",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 5. Einfache Schleife (backward branch)
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_LOOP_SIMPLE",
            "safe_name": "BRANCH_LOOP_SIMPLE",
            "instructions": [
                ("li", f"li {RISCVRegisters.T0}, 10\n1: addi {RISCVRegisters.T0}, {RISCVRegisters.T0}, -1\nbne {RISCVRegisters.T0}, {RISCVRegisters.ZERO}, 1b")
            ],
            "iterations": 100,
            "category": "BRANCH_LOOP",
            "instruction_count": 3,
            "description": "Simple loop with backward branch",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 6. Forward branch (immer nicht genommen)
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_FORWARD",
            "safe_name": "BRANCH_FORWARD",
            "instructions": [
                ("li", f"li {RISCVRegisters.T0}, 1\nli {RISCVRegisters.T1}, 2\nbne {RISCVRegisters.T0}, {RISCVRegisters.T1}, 1f\nnop\nnop\n1: nop")
            ],
            "iterations": 1000,
            "category": "BRANCH_FORWARD",
            "instruction_count": 6,
            "description": "Forward branch (not taken)",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 7. Branch mit NOPs im Delay-Slot
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_WITH_NOPS",
            "safe_name": "BRANCH_WITH_NOPS",
            "instructions": [
                ("li", f"li {RISCVRegisters.T0}, 1\nbeq {RISCVRegisters.T0}, {RISCVRegisters.T0}, 1f\nnop\nnop\nnop\n1: nop")
            ],
            "iterations": 1000,
            "category": "BRANCH_NOPS",
            "instruction_count": 6,
            "description": "Branch with NOPs in delay slot",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        # ------------------------------------------------------------
        # 8. Mixed Pattern (um Prädiktion zu stressen)
        # ------------------------------------------------------------
        tests.append({
            "name": "BRANCH_MIXED_PATTERN",
            "safe_name": "BRANCH_MIXED_PATTERN",
            "instructions": [
                ("li", f"li {RISCVRegisters.T0}, 100\nli {RISCVRegisters.T1}, 1\n1: addi {RISCVRegisters.T0}, {RISCVRegisters.T0}, -1\nand {RISCVRegisters.T2}, {RISCVRegisters.T0}, {RISCVRegisters.T1}\nbeq {RISCVRegisters.T2}, {RISCVRegisters.T1}, 2f\nj 3f\n2: nop\n3: bne {RISCVRegisters.T0}, {RISCVRegisters.ZERO}, 1b")
            ],
            "iterations": 10,
            "category": "BRANCH_MIXED",
            "instruction_count": 8,
            "description": "Mixed taken/not-taken pattern to stress predictor",
            "test_group": "branch",
            "type": "latency",
            "test_value": -1,
            "value_type": "NONE"
        })

        return tests