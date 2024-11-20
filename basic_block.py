from tree import Tree

def basic_blockify(program): 
  funcs = []
  for func in program.funcs:
    funcs.append(basic_blockify_func(func))
  return Tree('program', funcs=funcs)

def add_block(stmts):
  """return the block, index of the new block"""
  global basic_blocks
  basic_blocks.append(Tree('basic_block', stmts=stmts, after=[], id=len(basic_blocks)))
  return basic_blocks[-1]

def add_stmt(stmt):
  global basic_blocks
  basic_blocks[-1].stmts.append(stmt)

def peek():
  global basic_blocks
  return basic_blocks[-1]

def basic_blockify_func(func):
  global basic_blocks
  basic_blocks = [Tree('basic_block', stmts=[], after=[], id=0)]  # entry block
  basic_blockify_block(func.stmts)
  return Tree('func', name=func.name, params=func.params, block=basic_blocks)

def basic_blockify_block(block: "list of stmts"):
  for i, stmt in enumerate(block):
    if stmt.type == 'assign':
      add_stmt(stmt)
    elif stmt.type == 'return':
      add_stmt(stmt)

    elif stmt.type == 'if':
      prior = peek()
      basic_blockify_if(stmt, prior)

    elif stmt.type == 'ifelse':
      prior = peek()
      basic_blockify_ifelse(stmt, prior)

    elif stmt.type == 'while':
      prior = peek()
      basic_blockify_while(stmt, prior)
    
    else:
      raise Exception(f"Unknown stmt type: {stmt.type}")
  return basic_blocks[-1]

# post-condition: peek() is an empty basic block after the if
def basic_blockify_if(stmt, prior):

  # the prior goes to the condition

  # TODO this isn't a statement, but an expression.  we need to deal with that somehow
  condition_block = add_block([stmt.condition])
  then_block = add_block([])
  final_block = basic_blockify_block(stmt.block)
  end_block = add_block([])  # both the content of the if_block and the condition skipping the block meet in the end_block

  prior.stmts.append(Tree('br', block=condition_block.id))
  prior.after.append(condition_block.id)

  condition_block.stmts.append(Tree('cbr', condition=stmt.condition, yes=then_block.id, no=end_block.id))
  condition_block.after.append(then_block.id)
  condition_block.after.append(end_block.id)

  final_block.stmts.append(Tree('br', block=end_block.id))
  final_block.after.append(end_block.id)

  return end_block


# post-condition: peek() is an empty basic block after the if
def basic_blockify_ifelse(stmt, prior):

  # the prior goes to the condition

  # TODO this isn't a statement, but an expression.  we need to deal with that somehow
  condition_block = add_block([stmt.condition])
  then_block = add_block([])
  then_final_block = basic_blockify_block(stmt.if_block)
  else_block = add_block([])
  else_final_block = basic_blockify_block(stmt.else_block)
  end_block = add_block([])  # both the content of the if_block and the condition skipping the block meet in the end_block

  prior.after.append(condition_block.id)

  condition_block.stmts.append(Tree('cbr', condition=stmt.condition, yes=then_block.id, no=else_block.id))
  condition_block.after.append(then_block.id)
  condition_block.after.append(else_block.id)

  then_final_block.stmts.append(Tree('br', block=end_block.id))
  then_final_block.after.append(end_block.id)

  else_final_block.stmts.append(Tree('br', block=end_block.id))
  else_final_block.after.append(end_block.id)

  return end_block

def basic_blockify_while(stmt, prior):
  # the prior goes to the condition

  # TODO this isn't a statement, but an expression.  we need to deal with that somehow
  condition_block = add_block([])
  then_block = add_block([])
  final_block = basic_blockify_block(stmt.block)
  end_block = add_block([])

  prior.stmts.append(Tree('br', block=condition_block.id))
  prior.after.append(condition_block.id)

  final_block.stmts.append(Tree('br', block=condition_block.id))
  final_block.after.append(condition_block.id)

  condition_block.stmts.append(Tree('cbr', condition=stmt.condition, yes=then_block.id, no=end_block.id))
  condition_block.after.append(then_block.id)
  condition_block.after.append(end_block.id)

  return end_block