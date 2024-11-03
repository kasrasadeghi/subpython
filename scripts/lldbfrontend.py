import os
import sys
import termios
import tty
import shutil
from pathlib import Path

# Add LLDB Python path for macOS
LLDB_PYTHON_PATH = "/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python"
if LLDB_PYTHON_PATH not in sys.path:
    sys.path.append(LLDB_PYTHON_PATH)

import lldb

class SimpleLLDBFrontend:
    def __init__(self, program_path=None):
        self.debugger = lldb.SBDebugger.Create()
        self.debugger.SetAsync(False)
        self.target = None
        self.process = None
        self.original_terminal_settings = None
        self.term_width = shutil.get_terminal_size().columns
        self.side_panel_width = 35
        self.main_width = self.term_width - self.side_panel_width - 1
        
        if program_path:
            self.load_program(program_path)
    
    def load_program(self, program_path):
        error = lldb.SBError()
        self.target = self.debugger.CreateTarget(program_path, None, None, True, error)
        if not error.Success():
            print(f"\r\033[K Error loading program: {error.GetCString()}")
        else:
            print(f"\r\033[K Loaded program: {program_path}")
            self.handle_command("b main", suppress_prompt=True)
  
    def get_register_values(self):
        # Debug output
        with open("/tmp/lldb_frontend.log", "a") as f:
            f.write("Getting register values...\n")
            
        if not self.process:
            with open("/tmp/lldb_frontend.log", "a") as f:
                f.write("No process\n")
            return []
            
        if self.process.GetState() != lldb.eStateStopped:
            with open("/tmp/lldb_frontend.log", "a") as f:
                f.write(f"Process not stopped: {self.process.GetState()}\n")
            return []
        
        thread = self.process.GetSelectedThread()
        if not thread:
            with open("/tmp/lldb_frontend.log", "a") as f:
                f.write("No thread\n")
            return []
        
        frame = thread.GetFrameAtIndex(0)
        if not frame:
            with open("/tmp/lldb_frontend.log", "a") as f:
                f.write("No frame\n")
            return []
        
        registers = []
        regs_to_show = ['x0', 'x1', 'x18', 'x29', 'sp', 'pc']
        
        for reg_name in regs_to_show:
            reg = frame.FindRegister(reg_name)
            if reg:
                try:
                    value = reg.GetValue()
                    with open("/tmp/lldb_frontend.log", "a") as f:
                        f.write(f"Register {reg_name} = {value}\n")
                    
                    if value:
                        if value.startswith('0x'):
                            registers.append((reg_name, int(value, 16)))
                        else:
                            registers.append((reg_name, int(value)))
                except (ValueError, TypeError, AttributeError) as e:
                    with open("/tmp/lldb_frontend.log", "a") as f:
                        f.write(f"Error processing register {reg_name}: {e}\n")
                    continue
        
        return registers

    def get_stack_values(self):
        # Debug output
        with open("/tmp/lldb_frontend.log", "a") as f:
            f.write("Getting stack values...\n")
            
        if not self.process or self.process.GetState() != lldb.eStateStopped:
            return [], []
        
        thread = self.process.GetSelectedThread()
        if not thread:
            return [], []
        
        frame = thread.GetFrameAtIndex(0)
        if not frame:
            return [], []
        
        # Get FP and SP values
        fp_reg = frame.FindRegister('x29')
        sp_reg = frame.FindRegister('sp')
        
        with open("/tmp/lldb_frontend.log", "a") as f:
            f.write(f"FP reg: {fp_reg.GetValue() if fp_reg else 'None'}\n")
            f.write(f"SP reg: {sp_reg.GetValue() if sp_reg else 'None'}\n")
        
        if not fp_reg or not sp_reg:
            return [], []
        
        try:
            fp = int(fp_reg.GetValue(), 16) if fp_reg.GetValue().startswith('0x') else int(fp_reg.GetValue())
            sp = int(sp_reg.GetValue(), 16) if sp_reg.GetValue().startswith('0x') else int(sp_reg.GetValue())
            
            with open("/tmp/lldb_frontend.log", "a") as f:
                f.write(f"FP: {hex(fp)}, SP: {hex(sp)}\n")
        except (ValueError, AttributeError) as e:
            with open("/tmp/lldb_frontend.log", "a") as f:
                f.write(f"Error converting register values: {e}\n")
            return [], []
        
        error = lldb.SBError()
        stack_below = []
        stack_above = []
        
        # Read below FP
        current_addr = sp
        while current_addr < fp and len(stack_below) < 4:
            value = self.process.ReadPointerFromMemory(current_addr, error)
            if error.Success():
                stack_below.append((current_addr, value))
            current_addr += 8
        
        # Read above FP
        current_addr = fp
        for _ in range(4):
            value = self.process.ReadPointerFromMemory(current_addr, error)
            if error.Success():
                stack_above.append((current_addr, value))
            current_addr += 8
        
        with open("/tmp/lldb_frontend.log", "a") as f:
            f.write(f"Stack below: {stack_below}\n")
            f.write(f"Stack above: {stack_above}\n")
        
        return stack_below, stack_above

    def draw_side_panel(self):
        registers = self.get_register_values()
        stack_below, stack_above = self.get_stack_values()
        
        # Clear the entire right side
        for i in range(20):
            # End the line after clearing it to prevent wrapping
            print(f"\033[{i+1};{self.main_width+1}H\033[K\n", end='')
        
        # Draw box border - top
        print(f"\033[1;{self.main_width+1}H╔{'═' * (self.side_panel_width-2)}╗\n", end='')
        
        # Register section
        current_line = 2
        print(f"\033[{current_line};{self.main_width+1}H║ Registers:{' ' * (self.side_panel_width-12)}║\n", end='')
        current_line += 1
        
        for reg_name, value in registers:
            name_display = 'fp' if reg_name == 'x29' else reg_name
            row = f"{name_display:>3} = 0x{value:016x}"
            padding = self.side_panel_width - len(row) - 4
            print(f"\033[{current_line};{self.main_width+1}H║ {row} {' ' * padding}║\n", end='')
            current_line += 1
        
        # Stack section
        print(f"\033[{current_line};{self.main_width+1}H║{' ' * (self.side_panel_width-2)}║\n", end='')
        current_line += 1
        print(f"\033[{current_line};{self.main_width+1}H║ Stack above FP:{' ' * (self.side_panel_width-16)}║\n", end='')
        current_line += 1
        
        # Above FP
        for addr, value in reversed(stack_above):
            offset = addr - int(registers[3][1])  # Offset from FP
            print(f"\033[{current_line};{self.main_width+1}H║ [{offset:4}] 0x{value:016x} ║\n", end='')
            current_line += 1
        
        # FP marker
        print(f"\033[{current_line};{self.main_width+1}H║{'─' * (self.side_panel_width-2)}║\n", end='')
        current_line += 1
        
        print(f"\033[{current_line};{self.main_width+1}H║ Stack below FP:{' ' * (self.side_panel_width-16)}║\n", end='')
        current_line += 1
        
        # Below FP
        for addr, value in stack_below:
            offset = addr - int(registers[3][1])  # Offset from FP
            print(f"\033[{current_line};{self.main_width+1}H║ [{offset:4}] 0x{value:016x} ║\n", end='')
            current_line += 1
        
        # Fill any remaining space
        while current_line < 19:
            print(f"\033[{current_line};{self.main_width+1}H║{' ' * (self.side_panel_width-2)}║\n", end='')
            current_line += 1
        
        # Draw box border - bottom
        print(f"\033[{current_line};{self.main_width+1}H╚{'═' * (self.side_panel_width-2)}╝\n", end='')
        
        # Reset cursor position for main display
        print("\033[H", end='')
        sys.stdout.flush()

# [Rest of the code remains the same]
    def cleanup_ui(self):
        if self.original_terminal_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_terminal_settings)
    
    def init_ui(self):
        self.original_terminal_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)
        print('\033[2J\033[H', end='', flush=True)
    
    def show_prompt(self, command=""):
        print(f'\r\033[K{" " * self.main_width}', end='')
        print('\r\033[Klldb> ' + command, end='', flush=True)
    
    def handle_command(self, command, suppress_prompt=False):
        if not command:
            return True
        
        if command in ['quit', 'q']:
            return False
        
        result = lldb.SBCommandReturnObject()
        self.debugger.GetCommandInterpreter().HandleCommand(command, result)
        
        # Debug output
        with open("/tmp/lldb_frontend.log", "a") as f:
            f.write(f"\nCommand: {command}\n")
            if self.process:
                f.write(f"Process state: {self.process.GetState()}\n")
            
            # Get process after command if we don't have it
            if not self.process:
                self.process = self.target.GetProcess()
            
            # Try to get register values
            regs = self.get_register_values()
            f.write(f"Registers: {regs}\n")
            
            # Try to get stack values
            below, above = self.get_stack_values()
            f.write(f"Stack below: {below}\n")
            f.write(f"Stack above: {above}\n")
        
        if result.Succeeded():
            output = result.GetOutput()
            if output:
                for line in output.rstrip().split('\n'):
                    print(f'\r\033[K{line[:self.main_width]}')
                if not suppress_prompt:
                    print()
                
                # Ensure we update the panel after each command
                if command in ['r', 'run', 'n', 'next', 's', 'step', 'c', 'continue']:
                    self.process = self.target.GetProcess()
                    
                # Always try to draw the panel
                self.draw_side_panel()
        else:
            print(f'\r\033[KError: {result.GetError()[:self.main_width]}')
            if not suppress_prompt:
                print()
            self.draw_side_panel()
        
        sys.stdout.flush()
        return True


    
    def run(self):
        try:
            self.init_ui()
            running = True
            
            print('\r\033[KSimple LLDB Frontend - Type "help" for commands')
            print('\r\033[KCommon commands: run (r), next (n), step (s), continue (c)')
            print()
            
            self.draw_side_panel()
            current_command = ""
            self.show_prompt()
            
            while running:
                char = sys.stdin.read(1)
                
                if char == '\r':  # Enter
                    if current_command:
                        print()
                        running = self.handle_command(current_command)
                        current_command = ""
                        if running:
                            self.show_prompt()
                    else:
                        self.show_prompt()
                elif char in ('\x7f', '\x08'):  # Backspace
                    if current_command:
                        current_command = current_command[:-1]
                        self.show_prompt(current_command)
                elif ord(char) >= 32:  # Printable characters
                    current_command += char
                    self.show_prompt(current_command)
                elif char == '\x03':  # Ctrl+C
                    running = False
                
        finally:
            print()
            self.cleanup_ui()

def main():
    if len(sys.argv) < 2:
        print("Usage: python lldb_frontend.py <program>")
        sys.exit(1)
        
    program_path = sys.argv[1]
    if not os.path.exists(program_path):
        print(f"Error: Program '{program_path}' not found")
        sys.exit(1)
        
    frontend = SimpleLLDBFrontend(program_path)
    frontend.run()

if __name__ == "__main__":
    main()