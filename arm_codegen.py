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

def push_register(register):
  return [
    f"\tsub sp, sp, #16  ; push {register}",
    f"\tstr {register}, [sp]"
  ]

def push_immediate(value):
  return [
    f"\tsub sp, sp, #16  ; push immediate {value}",
    f"\tmov x18, #{value}",
    f"\tstr x18, [sp]"
  ]

def pop_to_register(register):
  return [
    f"\tldr {register}, [sp]  ; pop to {register}",
    f"\tadd sp, sp, #16"
  ]

def asm_function(func):
  # TODO handle that the first argument is w0, not x0 by doing a stur [#-4] or something

  global current_function
  current_function = func
  preamble = f"""
\t.globl	_{func.name}                           ; -- Begin function {func.name}
\t.p2align	2
_{func.name}:                                  ; @{func.name}
\tsub\tsp, sp, #16
\tstp\tx29, x30, [sp]             ; 16-byte Folded Spill
"""
  epilogue = """
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
  
  assert found_return, f"Function {func.name} has no return statement"

  current_function = None

  return preamble + "\n".join(assembled)

def lookup(name):
  result = current_function.params.index(name)
  if result == -1:
    raise Exception(f"Unknown variable: {name}")
  return "x" + str(result)

def asm_expr(expr) -> list:
  if expr.type == 'int':
    return push_immediate(expr.value)
  elif expr.type == 'variable':
    register = lookup(expr.name)
    return push_register(register)
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