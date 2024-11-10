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

def try_lookup(name):
  if name in current_function.variables or name in current_function.func.params:
    return lookup(name)
  return None

def lookup(name):
  assert name in current_function.func.params or name in current_function.variables, f"Unknown variable: {name}"
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
  # TODO handle that the first argument of main is w0, not x0 by doing a stur [#-4] or something.  check o0 for reference.
  # push arguments to stack and remember them like normal variables
  epilogue_label = f".{func.name}_epilogue"
  epilogue = f"""
{epilogue_label}:
\tmov\tsp, x29
\tldp\tx29, x30, [sp]             ; 16-byte Folded Reload
\tadd\tsp, sp, #16
\tret
"""

  global current_function
  current_function = Tree(type='current_function', func=func, epilogue_label=epilogue_label, found_return=False, stack_size=0, variables={}, block_count=0)
  preamble = f"""
\t.globl	_{func.name}                           ; -- Begin function {func.name}
\t.p2align	2
_{func.name}:                                  ; @{func.name}
\tsub\tsp, sp, #16
\tstp\tx29, x30, [sp]             ; 16-byte Folded Spill
\tmov\tx29, sp
"""
  assembled = []
  for stmt in func.stmts:
    assembled.extend(asm_stmt(stmt))
  
  assert current_function.found_return, f"Function {func.name} has no return statement"

  current_function = None

  return preamble + "\n".join(assembled) + epilogue

def asm_stmt(stmt):
  if stmt.type == 'assign':
    return asm_assign(stmt)
  elif stmt.type == 'if':
    return asm_if(stmt)
  elif stmt.type == 'ifelse':
    return asm_ifelse(stmt)
  elif stmt.type == 'while':
    return asm_while(stmt)
  elif stmt.type == 'return':
    current_function.found_return = True
    return asm_expr(stmt.expr) + pop_to_register("x0") + ["\tb " + current_function.epilogue_label]
  else:
    raise Exception(f"Unknown stmt type: {stmt.type}")

def asm_if(stmt):
  condition = asm_expr(stmt.condition)
  block, block_id = asm_block(stmt.block)
  end_block_id = current_function.block_count
  current_function.block_count += 1
  return condition + ["\tcmp x0, #0", f"\tbeq {block_id}f"] + block + [f"{end_block_id}:"]

def asm_ifelse(stmt):
  condition = asm_expr(stmt.condition)
  if_block, if_block_id = asm_block(stmt.if_block)
  else_block, else_block_id = asm_block(stmt.else_block)
  end_block_id = current_function.block_count
  current_function.block_count += 1
  return condition + ["\tcmp x0, #0", f"\tbeq {else_block_id}f"] + if_block + [f"\tb {end_block_id}f"] + else_block + [f"{end_block_id}:",]

def asm_while(stmt):
  condition = asm_expr(stmt.condition)
  condition_block_id = current_function.block_count
  current_function.block_count += 1
  block, block_id = asm_block(stmt.block)
  end_block_id = current_function.block_count
  current_function.block_count += 1
  return ['\t; while condition', f"{condition_block_id}:",] + condition + ["\tcmp x0, #0", f"\tbeq {end_block_id}f", '\t; while block'] + block + [f"\tb {condition_block_id}b", '\t; end while', f"{end_block_id}:"]

def asm_block(block):
  block_id = current_function.block_count
  current_function.block_count += 1
  assembled = [f'{block_id}:']
  for stmt in block:
    assembled.extend(asm_stmt(stmt))
  return assembled, block_id

def asm_assign(asgn):
  result = asm_expr(asgn.expr)
  if asgn.var in current_function.func.params:
    reg_slot = current_function.func.params.index(asgn.var)
    return [f'\t; write to param in reg'] + result + pop_to_register("x" + str(reg_slot))
  elif asgn.var in current_function.variables:
    stack_slot = current_function.variables[asgn.var]
    return [f'\t; write to var in stack'] + result + pop_to_register("x17") + [f"\tstr x17, [x29, #{(-stack_slot * 8)}]"]
  else:
    stack_slot = remember_var(asgn.var)
  return [f'\t; init + alloc {asgn.var}'] + result + [f'\t; {asgn.var} at {(stack_slot)*-8}']

def asm_expr(expr) -> list:
  if expr.type == 'int':
    return push_immediate(expr.value)
  elif expr.type == 'variable':
    return lookup(expr.name)
  elif expr.type == 'binop':
    left = asm_expr(expr.left)
    right = asm_expr(expr.right)
    if expr.op == '+':
      return left + right + pop_to_register("x0") + pop_to_register("x1") + ["\tadd x0, x0, x1"] + push_register("x0")
    elif expr.op == '-':
      return left + right + pop_to_register("x0") + pop_to_register("x1") + ["\tsub x0, x0, x1"] + push_register("x0")
    elif expr.op == '>':
      return left + right + pop_to_register("x1") + pop_to_register("x0") + ["\tcmp x0, x1", "\tmov x0, #0", "\tcset x0, gt"] + push_register("x0")
    elif expr.op == '<':
      return left + right + pop_to_register("x1") + pop_to_register("x0") + ["\tcmp x0, x1", "\tmov x0, #0", "\tcset x0, lt"] + push_register("x0")
    else:
      raise Exception(f"Unknown binop: {expr.op}")
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