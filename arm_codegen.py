from tree import Tree

def arm_codegen(tree):
  funcs = []
  for func in tree.funcs:
    funcs.append(asm_function(func))
  text_preamble = """
\t.section	__TEXT,__text,regular,pure_instructions
\t.build_version macos, 14, 0\tsdk_version 14, 2
"""

  symbols_postamble = """

.subsections_via_symbols
"""
  return text_preamble + "\n".join(funcs) + symbols_postamble

current_function = None

def lookup(name):
  if name in current_function.func.params:
    result = current_function.func.params.index(name)
    return push_register("x" + str(result))
  else:
    result = current_function.variables.get(name, None)
    if result is None:
      raise Exception(f"Unknown variable: {name}")
    return [f"\tldr x17, [x29, #{(-result * 8)}]  ; lookup {name}"] + push_register('x17')

def remember_var(name):
  assert name not in current_function.func.params, f"Variable {name} already exists as a parameter"
  assert name not in current_function.variables, f"Variable {name} already exists in this scope"
  current_function.variables[name] = current_function.stack_size
  return current_function.stack_size

def push_register(register):
  current_function.stack_size += 2
  return [
    f"\tsub sp, sp, #16  ; push {register}",
    f"\tstr {register}, [sp]"
  ]

def push_immediate(value):
  current_function.stack_size += 2
  return [
    f"\tsub sp, sp, #16  ; push immediate {value}",
    f"\tmov x17, #{value}",
    f"\tstr x17, [sp]"
  ]

def pop_to_register(register):
  current_function.stack_size -= 2
  return [
    f"\tldr {register}, [sp]  ; pop to {register}",
    f"\tadd sp, sp, #16"
  ]

def asm_function(func):
  # TODO handle that the first argument is w0, not x0 by doing a stur [#-4] or something

  global current_function
  current_function = Tree(type='current_function', func=func, stack_size=0, variables={})
  preamble = f"""
\t.globl	_{func.name}                           ; -- Begin function {func.name}
\t.p2align	2
_{func.name}:                                  ; @{func.name}
\tsub\tsp, sp, #16
\tstp\tx29, x30, [sp]             ; 16-byte Folded Spill
\tmov\tx29, sp
"""
  epilogue = """
\tmov\tsp, x29
\tldp\tx29, x30, [sp]             ; 16-byte Folded Reload
\tadd\tsp, sp, #16
"""
  assembled = []
  found_return = False
  for stmt in func.stmts:
    if stmt.type == 'return':
      found_return = True
      assembled.extend(asm_expr(stmt.expr))
      assembled.extend(pop_to_register("x0"))
      assembled.append(epilogue)
      assembled.append("	ret")
    else:
      assembled.extend(asm_stmt(stmt))
  
  assert found_return, f"Function {func.name} has no return statement"

  current_function = None

  return preamble + "\n".join(assembled)

def asm_stmt(stmt):
  if stmt.type == 'assign':
    return asm_assign(stmt)
  # elif stmt.type == 'print':
    # return asm_print(stmt)
  else:
    raise Exception(f"Unknown stmt type: {stmt.type}")

def asm_assign(stmt):
  result = asm_expr(stmt.expr)
  stack_slot = remember_var(stmt.var)
  return [f'\t; alloc {stmt.var}'] + result + [f'\t; {stmt.var} at {(stack_slot)*-8}']

def asm_expr(expr) -> list:
  if expr.type == 'int':
    return push_immediate(expr.value)
  elif expr.type == 'variable':
    return lookup(expr.name)
  elif expr.type == 'binop':
    left = asm_expr(expr.left)
    right = asm_expr(expr.right)
    if expr.op == '+':
      return left + right + pop_to_register("x0") + pop_to_register("x1") + ["  add x0, x0, x1"] + push_register("x0")
    elif expr.op == '-':
      return left + right + pop_to_register("x0") + pop_to_register("x1") + ["  sub x0, x0, x1"] + push_register("x0")
  elif expr.type == 'call':
    # {type=call, name, args}
    asm = []
    if len(expr.args) > 4:
      raise Exception(f"can't handle more than 4 arguments, given: {len(expr.args)}")
    for i, arg in enumerate(expr.args):
      asm.extend(asm_expr(arg))
      asm.extend(pop_to_register("x" + str(i)))
    asm.append(f"\tbl _{expr.name}")
    return asm + push_register("x0")
  else:
    raise Exception(f"Unknown expr type: {expr.type}")