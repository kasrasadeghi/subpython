import ctypes
import struct
import sys
from enum import Enum
from typing import Dict, List

class PTraceCommands(Enum):
    PTRACE_TRACEME = 0
    PTRACE_PEEKTEXT = 1
    PTRACE_PEEKDATA = 2
    PTRACE_PEEKUSER = 3
    PTRACE_POKETEXT = 4
    PTRACE_CONT = 7
    PTRACE_SINGLESTEP = 9
    PTRACE_GETREGS = 12
    PTRACE_SETREGS = 13
    PTRACE_ATTACH = 16
    PTRACE_DETACH = 17

class ARMRegisters(ctypes.Structure):
    _fields_ = [
        ("x0", ctypes.c_uint64),
        ("x1", ctypes.c_uint64),
        ("x2", ctypes.c_uint64),
        ("x3", ctypes.c_uint64),
        ("x4", ctypes.c_uint64),
        ("x5", ctypes.c_uint64),
        ("x6", ctypes.c_uint64),
        ("x7", ctypes.c_uint64),
        ("x8", ctypes.c_uint64),
        ("x9", ctypes.c_uint64),
        ("x10", ctypes.c_uint64),
        ("x11", ctypes.c_uint64),
        ("x12", ctypes.c_uint64),
        ("x13", ctypes.c_uint64),
        ("x14", ctypes.c_uint64),
        ("x15", ctypes.c_uint64),
        ("x16", ctypes.c_uint64),
        ("x17", ctypes.c_uint64),
        ("x18", ctypes.c_uint64),
        ("x19", ctypes.c_uint64),
        ("x20", ctypes.c_uint64),
        ("x21", ctypes.c_uint64),
        ("x22", ctypes.c_uint64),
        ("x23", ctypes.c_uint64),
        ("x24", ctypes.c_uint64),
        ("x25", ctypes.c_uint64),
        ("x26", ctypes.c_uint64),
        ("x27", ctypes.c_uint64),
        ("x28", ctypes.c_uint64),
        ("fp", ctypes.c_uint64),  # x29
        ("lr", ctypes.c_uint64),  # x30
        ("sp", ctypes.c_uint64),
        ("pc", ctypes.c_uint64),
        ("cpsr", ctypes.c_uint32),
    ]

class ARMDebugger:
    def __init__(self):
        self.libc = ctypes.CDLL("libc.dylib")
        self.pid = None
        self.breakpoints: Dict[int, int] = {}

    def attach(self, pid: int) -> None:
        """Attach to a running process."""
        self.pid = pid
        result = self.libc.ptrace(PTraceCommands.PTRACE_ATTACH.value, pid, 0, 0)
        if result < 0:
            raise Exception(f"Failed to attach to process {pid}")
        
    def detach(self) -> None:
        """Detach from the debugged process."""
        if self.pid:
            self.libc.ptrace(PTraceCommands.PTRACE_DETACH.value, self.pid, 0, 0)
            self.pid = None

    def get_registers(self) -> ARMRegisters:
        """Read all CPU registers."""
        regs = ARMRegisters()
        result = self.libc.ptrace(PTraceCommands.PTRACE_GETREGS.value, self.pid, 0, ctypes.byref(regs))
        if result < 0:
            raise Exception("Failed to read registers")
        return regs

    def set_registers(self, regs: ARMRegisters) -> None:
        """Write CPU registers."""
        result = self.libc.ptrace(PTraceCommands.PTRACE_SETREGS.value, self.pid, 0, ctypes.byref(regs))
        if result < 0:
            raise Exception("Failed to write registers")

    def read_memory(self, address: int, size: int) -> bytes:
        """Read process memory."""
        data = bytearray()
        for i in range(0, size, 8):
            word = self.libc.ptrace(PTraceCommands.PTRACE_PEEKTEXT.value, self.pid, address + i, 0)
            data.extend(word.to_bytes(8, sys.byteorder))
        return bytes(data[:size])

    def write_memory(self, address: int, data: bytes) -> None:
        """Write to process memory."""
        for i in range(0, len(data), 8):
            chunk = data[i:i+8].ljust(8, b'\x00')
            word = int.from_bytes(chunk, sys.byteorder)
            result = self.libc.ptrace(PTraceCommands.PTRACE_POKETEXT.value, self.pid, address + i, word)
            if result < 0:
                raise Exception(f"Failed to write memory at address {hex(address + i)}")

    def set_breakpoint(self, address: int) -> None:
        """Set a breakpoint at the specified address."""
        # Save original instruction
        original = self.read_memory(address, 4)
        self.breakpoints[address] = int.from_bytes(original, sys.byteorder)
        
        # Replace with breakpoint instruction (ARM64 BRK #1)
        self.write_memory(address, b'\x00\x00\x20\xd4')

    def remove_breakpoint(self, address: int) -> None:
        """Remove a breakpoint."""
        if address in self.breakpoints:
            original = self.breakpoints[address].to_bytes(4, sys.byteorder)
            self.write_memory(address, original)
            del self.breakpoints[address]

    def single_step(self) -> None:
        """Execute a single instruction."""
        result = self.libc.ptrace(PTraceCommands.PTRACE_SINGLESTEP.value, self.pid, 0, 0)
        if result < 0:
            raise Exception("Failed to single step")

    def continue_execution(self) -> None:
        """Continue process execution."""
        result = self.libc.ptrace(PTraceCommands.PTRACE_CONT.value, self.pid, 0, 0)
        if result < 0:
            raise Exception("Failed to continue execution")

def print_registers(regs: ARMRegisters) -> None:
    """Pretty print the CPU registers."""
    print("\nRegister State:")
    print(f"PC: {hex(regs.pc)}   SP: {hex(regs.sp)}   FP: {hex(regs.fp)}   LR: {hex(regs.lr)}")
    print(f"CPSR: {hex(regs.cpsr)}")
    
    for i in range(0, 29, 4):
        regs_line = []
        for j in range(4):
            if i + j < 29:
                reg_name = f"x{i+j}"
                reg_value = getattr(regs, reg_name)
                regs_line.append(f"{reg_name}: {hex(reg_value)}")
        print("   ".join(regs_line))