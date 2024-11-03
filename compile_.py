from parse import parse_file
from arm_codegen import arm_codegen

def compile_(file):
  tree = parse_file(file)
  print(tree)
  asm = arm_codegen(tree)
  return asm
  