from parse import parse_file
from arm_codegen import arm_codegen
from basic_block import basic_blockify
from ssa import ssa

def compile_(file):
  tree = parse_file(file)
  print(tree)
  asm = arm_codegen(tree)
  return asm

def compile_v2(file):
  tree = parse_file(file)
  print('parsed', tree)
  block_tree = basic_blockify(tree)
  print('basic blocks\n', block_tree)
  ssa_tree = ssa(block_tree)
  print('ssa\n', ssa_tree)
  # quad_tree = quads(ssa_tree)
  # instr_tree = register_allocation(quad_tree)
  return block_tree