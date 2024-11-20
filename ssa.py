from tree import Tree

def ssa(block_tree):
  funcs = []
  for func in block_tree.funcs:
    funcs.append(ssa_func(func))
  return Tree('program', funcs=funcs)

def ssa_func(func):
  # look at variables within a block and dedupe their names and uses
  # if a variable is used from another block, we need to create a phi node that tracks what blocks they can come from
  # JOURNAL maybe i need to make use-def chains for this?
  param_vars = {param: param for param in func.params}

  for block in func.block:
    variables = param_vars  # variables is a mapping from variable name to the latest version of that variable
    for stmt in block.stmts:
      print(stmt)
      if stmt.type == 'assign':
        stmt.expr = ssa_expr(stmt.expr, variables)
        if stmt.var in variables:
          old_var = variables[stmt.var]
          new_var = old_var + "'"
          stmt.var = new_var
          variables[old_var] = new_var
        else:
          variables[stmt.var] = stmt.var
        print(f'modified:\n{stmt}')
      print(variables)
      
  return func

def ssa_expr(expr, variables):
  # we want to replace any instances of a variable with the latest version of that variable
  if isinstance(expr, Tree):
    if expr.type == 'binop':
      expr.left = ssa_expr(expr.left, variables)
      expr.right = ssa_expr(expr.right, variables)
      return expr
    elif expr.type == 'variable':
      expr.name = variables[expr.name]
      return expr
    elif expr.type == 'int':
      return expr
    else:
      raise Exception(f"Unknown expr type: {expr.type}")
  raise Exception(f"ssa for expr not implemented: {expr}")

