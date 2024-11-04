#!/usr/bin/env python3
import os
import sys
import cmd
import subprocess
import signal
import time
from arm_debugger import ARMDebugger, print_registers

class SimpleDebuggerCLI(cmd.Cmd):
    intro = 'Simple ARM Debugger. Type help or ? to list commands.\n'
    prompt = '(debug) '

    def __init__(self, program_path):
        super().__init__()
        self.debugger = None
        self.program_path = program_path
        self.child_process = None
        self.setup_debugging()

    def setup_debugging(self):
        """Launch the target program and attach debugger"""
        try:
            print(f"Launching program: {self.program_path}")
            
            # Create a temporary launcher script that will make the program wait for debugger
            launcher_script = """#!/usr/bin/env python3
import os
import sys
import ctypes
import time

def main():
    # Load ptrace from libc
    libc = ctypes.CDLL("libc.dylib")
    
    # Request debugging for self (PTRACE_TRACEME)
    result = libc.ptrace(0, 0, 0, 0)
    if result < 0:
        sys.exit(1)
        
    # Print PID so parent can attach
    print(f"CHILD_PID:{os.getpid()}", flush=True)
    
    # Execute the target program
    os.execv(sys.argv[1], [sys.argv[1]])

if __name__ == '__main__':
    main()
"""
            # Write launcher script
            launcher_path = "/tmp/debug_launcher.py"
            with open(launcher_path, "w") as f:
                f.write(launcher_script)
            os.chmod(launcher_path, 0o755)

            # Launch program using the launcher
            abs_path = os.path.abspath(self.program_path)
            self.child_process = subprocess.Popen(
                ["/usr/bin/env", "python3", launcher_path, abs_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Wait for child PID from launcher
            pid = None
            while True:
                line = self.child_process.stdout.readline()
                if line.startswith("CHILD_PID:"):
                    pid = int(line.split(":")[1])
                    break
                if self.child_process.poll() is not None:
                    stdout, stderr = self.child_process.communicate()
                    raise Exception(f"Launcher failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}")

            if not pid:
                raise Exception("Failed to get child PID")

            print(f"Target process started with PID: {pid}")
            
            # Attach debugger
            print(f"Attaching debugger...")
            self.debugger = ARMDebugger()
            self.debugger.attach(pid)
            print("Debugger attached successfully")
            
            # Show initial state
            self.do_regs("")

        except Exception as e:
            print(f"Failed to start debugging: {str(e)}")
            self.cleanup()
            raise
        finally:
            # Clean up launcher script
            try:
                os.unlink(launcher_path)
            except:
                pass

    def cleanup(self):
        """Clean up processes and debugger"""
        if self.debugger:
            try:
                self.debugger.detach()
                print("Debugger detached")
            except Exception as e:
                print(f"Warning: Failed to detach debugger: {e}")

        if self.child_process:
            try:
                if self.child_process.poll() is None:
                    self.child_process.terminate()
                    time.sleep(0.1)
                    if self.child_process.poll() is None:
                        self.child_process.kill()
                print("Child process terminated")
            except Exception as e:
                print(f"Warning: Failed to terminate child process: {e}")

    def do_regs(self, arg):
        """Show register values"""
        try:
            regs = self.debugger.get_registers()
            print_registers(regs)
        except Exception as e:
            print(f"Error reading registers: {e}")

    def do_step(self, arg):
        """Step one instruction"""
        try:
            self.debugger.single_step()
            self.do_regs("")
        except Exception as e:
            print(f"Error stepping: {e}")

    def do_mem(self, arg):
        """Read memory: mem <address> [length=16]"""
        try:
            args = arg.split()
            if not args:
                print("Error: Address required")
                return
                
            addr = int(args[0], 16) if args[0].startswith("0x") else int(args[0])
            length = int(args[1]) if len(args) > 1 else 16
            
            data = self.debugger.read_memory(addr, length)
            print("\nMemory dump:")
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_dump = ' '.join(f'{b:02x}' for b in chunk)
                ascii_dump = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                print(f"{hex(addr + i):12x}:  {hex_dump:48s}  {ascii_dump}")
                
        except Exception as e:
            print(f"Error reading memory: {e}")

    def do_continue(self, arg):
        """Continue execution"""
        try:
            self.debugger.continue_execution()
            print("Continuing...")
        except Exception as e:
            print(f"Error continuing: {e}")

    def do_quit(self, arg):
        """Exit debugger"""
        print("Cleaning up...")
        self.cleanup()
        return True

    def do_break(self, arg):
        """Set breakpoint: break <address>"""
        try:
            if not arg:
                print("Error: Address required")
                return
                
            addr = int(arg, 16) if arg.startswith("0x") else int(arg)
            self.debugger.set_breakpoint(addr)
            print(f"Breakpoint set at {hex(addr)}")
        except Exception as e:
            print(f"Error setting breakpoint: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: sudo python debugger_cli.py <program>")
        sys.exit(1)

    program_path = sys.argv[1]
    if not os.path.exists(program_path):
        print(f"Error: Program '{program_path}' not found")
        sys.exit(1)

    if os.geteuid() != 0:
        print("Error: This debugger requires root privileges.")
        print("Please run with sudo:")
        print(f"    sudo python {sys.argv[0]} {program_path}")
        sys.exit(1)

    try:
        cli = SimpleDebuggerCLI(program_path)
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\nReceived interrupt, cleaning up...")
        cli.cleanup()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()