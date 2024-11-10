from compile_ import compile_

def shell(cmd, **kw):
  import subprocess
  subprocess.check_call(cmd, shell=True, **kw)

def write_asm(asm, filename):
  with open(filename, 'w') as f:
    f.write(asm)

def gen_intermediates(example):
  example_folder, example_filename = example.rsplit('/', 1)
  example_name = example_filename.split('.')[0]
  shell(f'clang -std=c89 -fno-asynchronous-unwind-tables -fno-exceptions -fno-rtti -fverbose-asm -O0 -S {example} -o asm/{example_name}-readable.S')
  shell(f'clang -o ref/{example_name} asm/{example_name}-readable.S')

def test(example_name):
    gen_intermediates(f'examples/{example_name}.c')
    asm = compile_(f'examples/{example_name}.py')
    write_asm(asm, f'output/{example_name}.S')
    shell(f'clang -o bin/{example_name} output/{example_name}.S')
    # shell(f'clang output/{example_name}.S -o bin/{example_name}')

if __name__ == '__main__':
  test('03_return_argc')
  test('04_return_vars')
  test('05_return_sum')
  test('06_return_if')
  test('07_return_while')
  
