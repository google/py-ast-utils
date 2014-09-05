"""Util functions for traversing the ast node tree."""


import _ast
import ast
import collections
import copy


# TODO: Handle TryExcept better
TYPE_TO_INDENT_FIELD = {
    _ast.ClassDef: ['body'],
    _ast.ExceptHandler: ['body'],
    _ast.For: ['body'],
    _ast.FunctionDef: ['body'],
    _ast.If: ['body', 'orelse'],
    _ast.TryExcept: ['body', 'orelse'],
    _ast.TryFinally: ['finalbody'],
    _ast.While: ['body'],
    _ast.With: ['body'],
}


class IndentLevelVisitor(ast.NodeVisitor):
  """Tracks the indent level of the current node."""

  def __init__(self, node_to_check):
    self.current_indent = 0
    self.node_to_check = node_to_check
    self.final_indent = None

  def generic_visit(self, node):
    """Called if no explicit visitor function exists for a node."""
    if node == self.node_to_check:
      self.final_indent = self.current_indent
    for field, value in ast.iter_fields(node):
      if (isinstance(node, tuple(TYPE_TO_INDENT_FIELD.keys())) and
          field in TYPE_TO_INDENT_FIELD[node.__class__]):
        self.current_indent += 1
      if isinstance(value, list):
        for item in value:
          if isinstance(item, _ast.AST):
            self.visit(item)
      elif isinstance(value, _ast.AST):
        self.visit(value)
      if (isinstance(node, tuple(TYPE_TO_INDENT_FIELD.keys())) and
          field in TYPE_TO_INDENT_FIELD[node.__class__]):
        self.current_indent -= 1
    return node

  def visit_With(self, node):
    if hasattr(node, 'matcher') and node.matcher.is_compound_with:
      self.current_indent -= 1
    self.generic_visit(node)
    return node


def GetIndentLevel(module_node, node_to_check):
  visitor = IndentLevelVisitor(node_to_check)
  visitor.visit(module_node)
  if visitor.final_indent is None:
    raise ValueError('node is not in module.')
  return visitor.final_indent


class _WrappingStmtVisitor(ast.NodeVisitor):

  def __init__(self, node_to_check):
    self.node_to_check = node_to_check
    self.current_stmt = None
    self.correct_stmt = None

  def generic_visit(self, node):
    """Called if no explicit visitor function exists for a node."""
    if isinstance(node, _ast.stmt):
      self.current_stmt = node
    if node == self.node_to_check:
      self.correct_stmt = self.current_stmt
    return super(_WrappingStmtVisitor, self).generic_visit(node)


def GetWrappingStmtNode(module_node, node_in_stmt):
  visitor = _WrappingStmtVisitor(node_in_stmt)
  visitor.visit(module_node)
  return visitor.correct_stmt


class _ParentVisitor(ast.NodeVisitor):

  def __init__(self, node_to_check):
    self.node_to_check = node_to_check
    self.parent_stack = []
    self.correct_parent = None

  def generic_visit(self, node):
    """Called if no explicit visitor function exists for a node."""
    if self.correct_parent:
      return node
    if node == self.node_to_check:
      self.correct_parent = self.parent_stack.pop()
    self.parent_stack.append(node)
    super(_ParentVisitor, self).generic_visit(node)
    self.parent_stack.pop()


def GetParentNode(module_node, node_in_stmt):
  visitor = _ParentVisitor(node_in_stmt)
  visitor.visit(module_node)
  return visitor.correct_parent


def NodeCopy(node_to_copy):
  """Copies the node by recursively copying its fields."""
  if not isinstance(node_to_copy, _ast.AST):
    if isinstance(node_to_copy, list):
      new_list = []
      for child in node_to_copy:
        new_list.append(NodeCopy(child))
      return new_list
    elif isinstance(node_to_copy, str):
      return node_to_copy
    elif isinstance(node_to_copy, collections.Iterable):
      raise NotImplementedError(
          'Unrecognized iterable {}. Please add support'.format(node_to_copy))
    else:
      return copy.copy(node_to_copy)
  new_node = type(node_to_copy)()
  for field_name in node_to_copy._fields:
    setattr(new_node, field_name, NodeCopy(getattr(node_to_copy, field_name)))
  return new_node

