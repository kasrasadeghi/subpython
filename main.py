from compile_ import compile_

def shell(cmd, **kw):
  import subprocess
  subprocess.check_call(cmd, shell=True, **kw)

def write_asm(asm, filename):
  with open(filename, 'w') as f:
    f.write(asm)

def gen_intermediates(example):
  example_name = example.split('/')[-1].split('.')[0]
  shell(f'clang -std=c89 -fno-asynchronous-unwind-tables -fno-exceptions -fno-rtti -fverbose-asm -O0 -S {example} -o asm/{example_name}-readable.S')

def test(example_name):
    gen_intermediates(f'examples/{example_name}.c')
    asm = compile_(f'examples/{example_name}.py')
    write_asm(asm, f'output/{example_name}.S')
    shell(f'clang -o bin/{example_name} output/{example_name}.S')
    shell(f'clang output/{example_name}.S -o bin/{example_name}')

if __name__ == '__main__':
  test('return_argc')
  test('return_sum')
  test('return_vars')
  
