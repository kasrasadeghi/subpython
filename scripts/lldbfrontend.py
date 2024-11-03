import os
import sys
import termios
import tty
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
        
        if program_path:
            self.load_program(program_path)
    
    def load_program(self, program_path):
        error = lldb.SBError()
        self.target = self.debugger.CreateTarget(program_path, None, None, True, error)
        if not error.Success():
            print(f"\r\033[KError loading program: {error.GetCString()}")
        else:
            print(f"\r\033[KLoaded program: {program_path}")
            # Automatically set breakpoint at main
            self.handle_command("b main", suppress_prompt=True)
    
    def cleanup_ui(self):
        if self.original_terminal_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_terminal_settings)
    
    def init_ui(self):
        # Save original terminal settings
        self.original_terminal_settings = termios.tcgetattr(sys.stdin)
        # Set terminal to raw mode
        tty.setraw(sys.stdin)
        # Clear screen
        print('\033[2J\033[H', end='', flush=True)
    
    def show_prompt(self, command=""):
        # Clear line and show prompt
        print('\r\033[K' + "lldb> " + command, end='', flush=True)
    
    def handle_command(self, command, suppress_prompt=False):
        if not command:
            return True
        
        if command in ['quit', 'q']:
            return False
        
        # Handle LLDB commands
        result = lldb.SBCommandReturnObject()
        self.debugger.GetCommandInterpreter().HandleCommand(command, result)
        
        if result.Succeeded():
            output = result.GetOutput()
            if output:
                for line in output.rstrip().split('\n'):
                    print(f'\r\033[K{line}')
                if not suppress_prompt:
                    # Only print a newline if there was output
                    print()
        else:
            print(f'\r\033[KError: {result.GetError()}')
            if not suppress_prompt:
                print()
        
        sys.stdout.flush()
        return True
    
    def run(self):
        try:
            self.init_ui()
            running = True
            
            print('\r\033[KSimple LLDB Frontend - Type "help" for commands')
            print('\r\033[KCommon commands: run (r), next (n), step (s), continue (c)')
            print()
            
            current_command = ""
            self.show_prompt()
            
            while running:
                char = sys.stdin.read(1)
                
                if char == '\r':  # Enter
                    if current_command:
                        print()  # New line
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
            print()  # Ensure we end on a new line
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