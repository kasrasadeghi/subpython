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
        if not self.process:
            return []
            
        if self.process.GetState() != lldb.eStateStopped:
            return []
        
        thread = self.process.GetSelectedThread()
        if not thread:
            return []
        
        frame = thread.GetFrameAtIndex(0)
        if not frame:
            return []
        
        registers = []
        regs_to_show = ['x0', 'x1', 'x18', 'x29', 'sp', 'pc']
        
        for reg_name in regs_to_show:
            reg = frame.FindRegister(reg_name)
            if reg:
                try:
                    value = reg.GetValue()
                    if value:
                        if value.startswith('0x'):
                            registers.append((reg_name, int(value, 16)))
                        else:
                            registers.append((reg_name, int(value)))
                except (ValueError, TypeError, AttributeError):
                    continue
        
        return registers

    def get_stack_values(self):
        if not self.process or self.process.GetState() != lldb.eStateStopped:
            return []
            
        thread = self.process.GetSelectedThread()
        if not thread:
            return []
            
        frame = thread.GetFrameAtIndex(0)
        if not frame:
            return []
            
        # Get FP and SP values
        fp_reg = frame.FindRegister('x29')
        sp_reg = frame.FindRegister('sp')
        
        if not fp_reg or not sp_reg:
            return []
            
        try:
            fp = int(fp_reg.GetValue(), 16) if fp_reg.GetValue().startswith('0x') else int(fp_reg.GetValue())
            sp = int(sp_reg.GetValue(), 16) if sp_reg.GetValue().startswith('0x') else int(sp_reg.GetValue())
        except (ValueError, AttributeError):
            return []
        
        error = lldb.SBError()
        stack_values = []
        
        # Read all values from FP down to SP
        current_addr = fp
        while current_addr >= sp:
            value = self.process.ReadPointerFromMemory(current_addr, error)
            if error.Success():
                stack_values.append((current_addr, value))
            current_addr -= 8
            
        return stack_values

    def draw_side_panel(self):
        registers = self.get_register_values()
        stack_values = self.get_stack_values()
        
        # Clear the entire right side
        for i in range(20):
            print(f"\033[{i+1};{self.main_width+1}H\033[K\n", end='')
        
        # Draw box border - top
        title = "═" * (self.side_panel_width-2)
        print(f"\033[1;{self.main_width+1}H╔{title}╗\n", end='')
        
        # Register section
        current_line = 2
        reg_title = "Registers:"
        padding = self.side_panel_width - len(reg_title) - 3
        print(f"\033[{current_line};{self.main_width+1}H║ {reg_title}{' ' * padding}║\n", end='')
        current_line += 1
        
        for reg_name, value in registers:
            name_display = 'fp' if reg_name == 'x29' else reg_name
            row = f"{name_display:>3} = 0x{value:016x}"
            padding = self.side_panel_width - len(row) - 3
            print(f"\033[{current_line};{self.main_width+1}H║ {row}{' ' * padding}║\n", end='')
            current_line += 1
        
        # Stack section
        print(f"\033[{current_line};{self.main_width+1}H║{' ' * (self.side_panel_width-2)}║\n", end='')
        current_line += 1
        
        stack_title = "Stack (FP → SP):"
        padding = self.side_panel_width - len(stack_title) - 3
        print(f"\033[{current_line};{self.main_width+1}H║ {stack_title}{' ' * padding}║\n", end='')
        current_line += 1
        
        # Show stack values
        if registers and len(registers) > 3:  # Make sure we have FP register
            fp_value = registers[3][1]  # FP is the fourth register (x29)
            for addr, value in stack_values:
                if current_line >= 18:  # Leave room for bottom border
                    break
                offset = addr - fp_value  # Offset from FP
                row = f"[{offset:4}] 0x{value:016x}"
                padding = self.side_panel_width - len(row) - 3
                print(f"\033[{current_line};{self.main_width+1}H║ {row}{' ' * padding}║\n", end='')
                current_line += 1
        
        # Fill any remaining space
        while current_line < 19:
            print(f"\033[{current_line};{self.main_width+1}H║{' ' * (self.side_panel_width-2)}║\n", end='')
            current_line += 1
        
        # Draw box border - bottom
        print(f"\033[{current_line};{self.main_width+1}H╚{title}╝\n", end='')
        
        # Reset cursor position for main display
        print("\033[H", end='')
        sys.stdout.flush()

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
            
        # Special handling for 'r' command to ensure clean restart
        if command in ['r', 'run']:
            # Kill existing process if it exists
            if self.process:
                self.process.Kill()
                self.process = None
            # Create new process and run
            error = lldb.SBError()
            self.process = self.target.Launch(
                self.debugger.GetListener(),
                None,  # argv
                None,  # envp
                None,  # stdin_path
                None,  # stdout_path
                None,  # stderr_path
                None,  # working_directory
                0,    # launch_flags
                True, # stop_at_entry
                error
            )
            if not error.Success():
                print(f'\r\033[KError launching process: {error.GetCString()}')
                return True
        else:
            # Handle all other commands normally
            result = lldb.SBCommandReturnObject()
            self.debugger.GetCommandInterpreter().HandleCommand(command, result)
            
            if result.Succeeded():
                output = result.GetOutput()
                if output:
                    for line in output.rstrip().split('\n'):
                        print(f'\r\033[K{line[:self.main_width]}')
                    if not suppress_prompt:
                        print()
                    
                    # Update process reference after relevant commands
                    if command in ['n', 'next', 's', 'step', 'c', 'continue']:
                        self.process = self.target.GetProcess()
            else:
                print(f'\r\033[KError: {result.GetError()[:self.main_width]}')
                if not suppress_prompt:
                    print()
        
        # Always update the side panel
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