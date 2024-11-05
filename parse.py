# def main():
#   a = 1
#   while a < 10:
#     a += 1
#     if a % 2 == 0:
#       print(a)
#   print("Done")

from line_reader import LineReader
from tree import Tree

reader = None

def parse_file(file):
  with open(file) as f:
    content = f.read()

  return parse_content(file, content)

def parse_content(filename, content):
  global reader
  reader = LineReader(content)

  funcs = []

  while reader.has_next():
    line = reader.peek()
    if line.startswith('def'):
      funcs.append(parse_func())
    else:
      print(f'Unknown line: {line}')
      reader.pop()
  
  return Tree(type='file', filename=filename, funcs=funcs)

def parse_func():
  def_line = reader.pop()
  assert def_line.startswith('def ')
  def_line = def_line.removeprefix('def ')
  name = def_line.split('(')[0]
  params = def_line.split('(')[1].removesuffix('):').split(', ')
  stmts = parse_block(indent = 1)
  return Tree(type="def", name=name, params=params, stmts=stmts)

def parse_block(indent):
  stmts = []
  while reader.has_next():
    line = reader.peek()
    if line.startswith('  ' * indent):
      stmts.append(parse_stmt())
    else:
      break
  return stmts

def parse_stmt():
  line = reader.pop()
  line = line.strip()
  if line.startswith('return '):
    return Tree(type='return', expr=parse_expr(line.removeprefix('return ')))
  elif line.startswith('print('):
    return Tree(type='print', value=parse_expr(line.removeprefix('print(').removesuffix(')')))
  elif ' = ' in line:
    var, expr = line.split(' = ')
    return Tree(type='assign', var=var, expr=parse_expr(expr))
  else:
    assert False, f'Unknown statement: {line}'

def parse_expr(expr):
  if ' ' in expr.strip() and len(expr.split(' ')) == 3:
    parts = expr.split(' ')
    left, op, right = parts
    return Tree(type='binop', left=parse_expr(left), op=op, right=parse_expr(right))
  elif '(' in expr and expr.endswith(')'):
    if expr[0] == '(':
      return parse_expr(expr[1:-1])
    else:
      function_name = expr.split('(')[0]
      args = expr.removeprefix(function_name + '(').removesuffix(')').split(', ')
      return Tree(type='call', name=function_name, args=[parse_expr(x.strip()) for x in args])
  elif expr.isnumeric():
    return Tree(type='int', value=int(expr))
  else:
    return Tree(type='variable', name=expr)