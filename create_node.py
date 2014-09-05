"""Copyright 2014 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Module containing methods to create nodes.

This provides useful defaults and validation logic.

Note that there are many things that are currently unsupported. Please
add to this module as needed.
"""

import _ast
import ast
import re


class Error(Exception):
  pass


class InvalidCtx(Error):
  pass


def Enum(**enums):
  return type('Enum', (), enums)


CtxEnum = Enum(
    LOAD='load',
    STORE='store',
    DEL='delete',
    PARAM='param')


def _ToArgsDefaults(args=(), keys=(), values=()):
  args = list(args)
  defaults = []
  for arg, default in zip(keys, values):
    args.append(arg)
    defaults.append(default)
  args = [_WrapWithName(arg, ctx_type=CtxEnum.PARAM) for arg in args]
  return args, defaults


def _WrapWithName(to_wrap, ctx_type=CtxEnum.PARAM):
  if isinstance(to_wrap, _ast.AST):
    return to_wrap
  return Name(to_wrap, ctx_type=ctx_type)


def _LeftmostNodeInDotVar(node):
  while not hasattr(node, 'id'):
    if not hasattr(node, 'value'):
      return node
    node = node.value
  return node


def FormatAndValidateBody(body):
  if body is None:
    body = [Pass()]
  for child in body:
    if not isinstance(child, _ast.stmt):
      raise ValueError(
          'All body nodes must be stmt nodes, and {} is not. '
          'Try wrapping your node in an Expr node.'
          .format(child))
  return body


class ChangeCtxTransform(ast.NodeTransformer):

  def __init__(self, new_ctx_type):
    super(ChangeCtxTransform, self).__init__()
    self._new_ctx_type = new_ctx_type

  def generic_visit(self, node):
    node = super(ChangeCtxTransform, self).generic_visit(node)
    if hasattr(node, 'ctx'):
      node.ctx = GetCtx(self._new_ctx_type)
    return node


def ChangeCtx(node, new_ctx_type):
  transform = ChangeCtxTransform(new_ctx_type)
  transform.visit(node)


###############################################################################
# Node Creators
###############################################################################


def arguments(
    args=(), keys=(), values=(), vararg_name=None, kwarg_name=None):
  """Creates an _ast.FunctionDef node.

  Args:
    args: A list of args.
    keys: A list of keys, must be the same length as values.
    values: A list of values, correspond to keys.
    vararg_name: The name of the vararg variable, or None.
    kwarg_name: The name of the kwargs variable, or None.

  Raises:
    ValueError: If len(keys) != len(values).

  Returns:
    An _ast.FunctionDef node.
  """
  args, defaults = _ToArgsDefaults(args=args, keys=keys, values=values)
  return _ast.arguments(
      args=args,
      defaults=defaults,
      vararg=vararg_name,
      kwarg=kwarg_name)


def Add():
  return _ast.Add()


def And():
  return _ast.And()


def Assert(check, message=None):
  return _ast.Assert(test=check, msg=message)


def Assign(left, right):
  """Creates an _ast.Assign node.

  Args:
    left: The node on the left side of the equal sign.
      May either be a node, or a string, which will automatically get
      converted to a name node.
    right: The node on the right side of the equal sign.

  Returns:
    An _ast.Assign node.
  """
  if not isinstance(left, (list, tuple)):
    targets = [left]
  else:
    targets = left
  new_targets = []
  for target in targets:
    if isinstance(target, str):
      new_targets.append(_WrapWithName(target, ctx_type=CtxEnum.STORE))
    else:
      new_targets.append(target)
  return _ast.Assign(
      targets=new_targets,
      value=right)


def AugAssign(left, op, right):
  """Creates an _ast.AugAssign node.

  Args:
    left: The node on the left side of the equal sign.
      May either be a node, or a string, which will automatically get
      converted to a name node.
    op: Operator
    right: The node on the right side of the equal sign.

  Returns:
    An _ast.Assign node.
  """
  left = _WrapWithName(left)
  return _ast.AugAssign(
      target=left,
      op=op,
      value=right)


def BinOp(left, op, right):
  """Creates an _ast.BinOp node.

  Args:
    left: The node on the left side of the equal sign.
    op: The operator. Literal values as strings also accepted:
    right: The node on the right side of the equal sign.

  Returns:
    An _ast.BinOp node.
  """
  if not isinstance(op, _ast.AST):
    op = BinOpMap(op)

  return _ast.BinOp(
      left=left,
      op=op,
      right=right)


def BoolOp(left, *alternating_ops_values):
  """Creates an _ast.BoolOp node.

  Args:
    left: The node on the left side of the equal sign.
    *alternating_ops_values: An alternating list of ops and expressions.
      Note that _ast.Not is not a valid boolean operator, it is considered
      a unary operator.
      For example: (_ast.Or, _ast.Name('a'))

  Returns:
    An _ast.BoolOp node.
  """
  values = [left]
  op = None
  op_next = True
  alternating_ops_values = list(alternating_ops_values)
  while alternating_ops_values:
    op_or_value = alternating_ops_values.pop(0)
    if op_next:
      if not isinstance(op_or_value, _ast.AST):
        op_or_value = BoolOpMap(op_or_value)
      if not op:
        op = op_or_value
      elif op and op == op_or_value:
        continue
      else:
        # Or's take priority over And's
        if isinstance(op, _ast.And):
          return BoolOp(_ast.BoolOp(op=op, values=values),
                        op_or_value,
                        *alternating_ops_values)
        else:
          last_value = values.pop()
          values.append(BoolOp(last_value,
                               op_or_value,
                               *alternating_ops_values))
          return _ast.BoolOp(
              op=_ast.Or(),
              values=values)
    else:
      values.append(op_or_value)
    op_next = not op_next

  return _ast.BoolOp(op=op, values=values)


def BitAnd():
  return _ast.BitAnd()


def BitOr():
  return _ast.BitOr()


def BitXor():
  return _ast.BitXor()


def Call(caller, args=(), keys=(), values=(), starargs=None,
         kwargs=None):
  """Creates an _ast.Call node.

  Args:
    caller: Either a node of the appropriate type
      (_ast.Str, _ast.Name, or _ast.Attribute), or a dot-separated string.
    args: A list of args.
    keys: A list of keys, must be the same length as values.
    values: A list of values, correspond to keys.
    starargs: A node with a star in front of it. Passing a string will be
      interpreted as a VarReference.
    kwargs: A node with two stars in front of it. Passing a string will be
      interpreted as a VarReference.

  Raises:
    ValueError: If len(keys) != len(values) or caller is not the right type.

  Returns:
    An _ast.Call object.
  """
  if len(keys) != len(values):
    raise ValueError(
        'len(keys)={} != len(values)={}'.format(len(keys), len(values)))
  if isinstance(caller, str):
    caller = VarReference(*caller.split('.'))
  if not isinstance(caller, (_ast.Str, _ast.Name, _ast.Attribute)):
    raise ValueError(
        'caller must be a: \n'
        '1. string\n'
        '2. _ast.Str node\n'
        '3. _ast.Name node\n'
        '4. _ast.Attr node\n'
        'not {}'.format(caller))
  keywords = [_ast.keyword(arg=key, value=val)
              for key, val in zip(keys, values)]
  args = [_WrapWithName(arg, ctx_type=CtxEnum.LOAD) for arg in args]
  if isinstance(starargs, str):
    starargs = VarReference(*starargs.split('.'))
  if isinstance(kwargs, str):
    kwargs = VarReference(*kwargs.split('.'))
  return _ast.Call(
      func=caller,
      args=args,
      keywords=keywords,
      starargs=starargs,
      kwargs=kwargs)


def ClassDef(
    name, bases=(), body=None, decorator_list=()):
  """Creates an _ast.ClassDef node.

  Args:
    name: The name of the class.
    bases: The base classes of the class
    body: A list of _ast.stmt nodes that go in the body of the class.
    decorator_list: A list of decorator nodes.

  Raises:
    ValueError: If some body element is not an _ast.stmt node.

  Returns:
    An _ast.ClassDef node.
  """
  body = FormatAndValidateBody(body)
  bases = [_WrapWithName(base, ctx_type=CtxEnum.LOAD) for base in bases]
  return _ast.ClassDef(
      name=name,
      bases=bases,
      body=body,
      decorator_list=list(decorator_list))


def Compare(*args):
  """Creates an _ast.Compare node.

  Args:
    *args: List which should alternate between regular nodes and _ast.cmpop.

  Raises:
    ValueError: If less than 3 args, or odd args are not valid comparison
      operators.

  Returns:
    An _ast.Compare node.
  """
  if len(args) < 3:
    raise ValueError('Must have at least 3 args')
  ops = []
  comparators = []
  for index, arg in enumerate(args):
    if index % 2 == 1:
      if not isinstance(arg, _ast.AST):
        arg = CompareOpMap(arg)
      if not isinstance(arg, _ast.cmpop):
        raise ValueError('Odd args must be instances of _ast.cmpop')
      ops.append(arg)
    else:
      if index != 0:
        comparators.append(_WrapWithName(arg, ctx_type=CtxEnum.LOAD))
  return _ast.Compare(left=_WrapWithName(args[0], ctx_type=CtxEnum.LOAD),
                      ops=ops,
                      comparators=comparators)


def comprehension(for_part, in_part, *ifs):
  """Create an _ast.comprehension node, used in _ast.ListComprehension.

  Args:
    for_part: The part after "for "
    in_part: The part after "for [for_part] in "
    *ifs: {_ast.Compare}

  Returns:
    {_ast.comprehension}
  """
  for_part = _WrapWithName(for_part, ctx_type=CtxEnum.STORE)
  in_part = _WrapWithName(in_part, ctx_type=CtxEnum.LOAD)
  return _ast.comprehension(target=for_part,
                            iter=in_part,
                            ifs=list(ifs))


def Dict(keys=(), values=()):
  """Creates an _ast.Dict node. This represents a dict literal.

  Args:
    keys: A list of keys as nodes. Must be the same length as values.
    values: A list of values as nodes. Must be the same length as values.

  Raises:
    ValueError: If len(keys) != len(values).

  Returns:
    An _ast.Dict node.
  """
  if len(keys) != len(values):
    raise ValueError(
        'len(keys)={} != len(values)={}'.format(len(keys), len(values)))
  return _ast.Dict(list(keys), list(values))


def DictComp(left_side_key, left_side_value, for_part, in_part, *ifs):
  """Creates _ast.DictComp nodes.

  'left_side', 'left_side_value' for 'for_part' in 'in_part' if 'ifs'

  Args:
    left_side_key: key in leftmost side of the expression.
    left_side_value: value in leftmost side of the expression.
    for_part: The part after '[left_side] for '
    in_part: The part after '[left_side] for [for_part] in '
    *ifs: Any if statements that come at the end.

  Returns:
    {_ast.DictComp}
  """
  left_side_key = _WrapWithName(left_side_key, ctx_type=CtxEnum.LOAD)
  left_side_value = _WrapWithName(left_side_value, ctx_type=CtxEnum.LOAD)
  for_part = _WrapWithName(for_part, ctx_type=CtxEnum.STORE)
  in_part = _WrapWithName(in_part, ctx_type=CtxEnum.LOAD)
  return _ast.DictComp(
      key=left_side_key,
      value=left_side_value,
      generators=[comprehension(for_part, in_part, *ifs)])


def Div():
  return _ast.Div()


def Eq():
  return _ast.Eq()


def ExceptHandler(exception_type=None, name=None, body=None):
  body = FormatAndValidateBody(body)
  return _ast.ExceptHandler(type=exception_type, name=name, body=body)


def Expr(value):
  """Creates an _ast.Expr node.

  Note that this node is mostly used to wrap other nodes so they're treated
  as whole-line statements.

  Args:
    value: The value stored in the node.

  Raises:
    ValueError: If value is an _ast.stmt node.

  Returns:
    An _ast.Expr node.
  """
  if isinstance(value, _ast.stmt):
    raise ValueError(
        'value must not be an _ast.stmt node, because those nodes don\'t need '
        'to be wrapped in an Expr node. Value passed: {}'.format(value))
  return _ast.Expr(value)


def FloorDiv():
  return _ast.FloorDiv()


def FunctionDef(
    name, args=(), keys=(), values=(), body=None, vararg_name=None,
    kwarg_name=None, decorator_list=()):
  """Creates an _ast.FunctionDef node.

  Args:
    name: The name of the function.
    args: A list of args.
    keys: A list of keys, must be the same length as values.
    values: A list of values, correspond to keys.
    body: A list of _ast.stmt nodes that go in the body of the function.
    vararg_name: The name of the vararg variable, or None.
    kwarg_name: The name of the kwargs variable, or None.
    decorator_list: A list of decorator nodes.
  Raises:
    ValueError: If len(keys) != len(values).

  Returns:
    An _ast.FunctionDef node.
  """
  body = FormatAndValidateBody(body)
  args = arguments(
      args=args, keys=keys, values=values,
      vararg_name=vararg_name, kwarg_name=kwarg_name)
  return _ast.FunctionDef(
      name=name,
      args=args,
      body=body,
      decorator_list=list(decorator_list))


def GeneratorExp(left_side, for_part, in_part, *ifs):
  """Creates _ast.GeneratorExp nodes.

  'left_side' for 'for_part' in 'in_part' if 'ifs'

  Args:
    left_side: leftmost side of the expression.
    for_part: The part after '[left_side] for '
    in_part: The part after '[left_side] for [for_part] in '
    *ifs: Any if statements that come at the end.

  Returns:
    {_ast.GeneratorExp}
  """
  left_side = _WrapWithName(left_side, ctx_type=CtxEnum.LOAD)
  for_part = _WrapWithName(for_part, ctx_type=CtxEnum.STORE)
  in_part = _WrapWithName(in_part, ctx_type=CtxEnum.LOAD)
  return _ast.GeneratorExp(
      elt=left_side,
      generators=[comprehension(for_part, in_part, *ifs)])


def Gt():
  return _ast.Gt()


def GtE():
  return _ast.GtE()


def If(conditional, body=None, orelse=None):
  """Creates an _ast.If node.

  Args:
    conditional: The expression we evaluate for its truthiness.
    body: The list of nodes that make up the body of the if statement.
      Executed if True.
    orelse: {[_ast.If]|[_ast.stmt]|None} Either another If statement as the
      only element in a list, (in which case this becomes an elif), a list of
      stmt nodes (in which case this is an else), or None (in which case, there
      is only the if)

  Raises:
    ValueError: If the body or orelse are lists which contain elements not
      inheriting from _ast.stmt.

  Returns:
    An _ast.If node.
  """
  body = FormatAndValidateBody(body)
  if orelse is None:
    orelse = []
  if isinstance(orelse, (list, tuple)):
    for child in body:
      if not isinstance(child, _ast.stmt):
        raise ValueError(
            'All body nodes must be stmt nodes, and {} is not. '
            'Try wrapping your node in an Expr node.'
            .format(child))
  return _ast.If(test=conditional, body=body, orelse=orelse)


def IfExp(conditional, true_case, false_case):
  """Creates an _ast.IfExp node.

  Note that this is python's ternary operator, not to be confused with _ast.If.

  Args:
    conditional: The expression we evaluate for its truthiness.
    true_case: What to do if conditional is True.
    false_case: What to do if conditional is False.

  Returns:
    An _ast.IfExp node.
  """
  return _ast.IfExp(body=true_case, test=conditional, orelse=false_case)


def Import(import_part='', from_part='', asname=None):
  """Creates either an _ast.Import node or an _ast.ImportFrom node.

  Args:
    import_part: The text that follows "import".
    from_part: The text that follows "from". Optional. Determines if we will
      return an _ast.Import or _ast.ImportFrom node.
    asname: Text that follows "as". Optional.

  Returns:
    An _ast.Import or _ast.ImportFrom node.
  """
  names = [_ast.alias(name=import_part,
                      asname=asname)]
  if from_part:
    return _ast.ImportFrom(
        level=0,
        module=from_part,
        names=names)
  else:
    return _ast.Import(names=names)


def In():
  return _ast.In()


def Index(value):
  return _ast.Index(value)


def Invert():
  return _ast.Invert()


def Is():
  return _ast.Is()


def IsNot():
  return _ast.IsNot()


def Lambda(body, args=None):
  """Creates an _ast.Lambda object.

  Args:
    body: {_ast.AST}
    args: {_ast.arguments}

  Raises:
    ValueError: If body is a list or tuple.

  Returns:
    {_ast.Lambda}
  """
  if isinstance(args, (list, tuple)):
    raise ValueError('Body should be a single element, not a list or tuple')
  if not args:
    args = arguments()
  return _ast.Lambda(args=args, body=body)


def List(*items, **kwargs):
  """Creates an _ast.List node.

  Automatically adjusts inner ctx attrs.

  Args:
    *items: The items in the list.
    **kwargs: Only recognized kwarg is 'ctx_type', which controls the
      ctx type of the list. See CtxEnum.

  Returns:
    An _ast.List node.
  """
  ctx_type = kwargs.pop('ctx_type', CtxEnum.LOAD)

  for item in items:
    if isinstance(item, _ast.Name):
      item.ctx = GetCtx(ctx_type)
    elif isinstance(item, _ast.Attribute):
      name_node = _LeftmostNodeInDotVar(item)
      name_node.ctx = GetCtx(ctx_type)
  ctx = GetCtx(ctx_type)
  return _ast.List(elts=list(items),
                   ctx=ctx)


def ListComp(left_side, for_part, in_part, *ifs):
  """Creates _ast.ListComp nodes.

  'left_side' for 'for_part' in 'in_part' if 'ifs'

  Args:
    left_side: leftmost side of the expression.
    for_part: The part after '[left_side] for '
    in_part: The part after '[left_side] for [for_part] in '
    *ifs: Any if statements that come at the end.

  Returns:
    {_ast.ListComp}
  """
  left_side = _WrapWithName(left_side, ctx_type=CtxEnum.LOAD)
  for_part = _WrapWithName(for_part, ctx_type=CtxEnum.STORE)
  in_part = _WrapWithName(in_part, ctx_type=CtxEnum.LOAD)
  return _ast.ListComp(
      elt=left_side,
      generators=[comprehension(for_part, in_part, *ifs)])


def LShift():
  return _ast.LShift()


def Lt():
  return _ast.Lt()


def LtE():
  return _ast.LtE()


def Mod():
  return _ast.Mod()


def Module(*body_items):
  if not body_items:
    raise ValueError('Must have at least one argument in the body')
  return _ast.Module(body=list(body_items))


def Mult():
  return _ast.Mult()


def Name(name_id, ctx_type=CtxEnum.LOAD):
  """Creates an _ast.Name node.

  Args:
    name_id: Name of the node.
    ctx_type: See CtxEnum for options.

  Returns:
    An _ast.Name node.
  """
  ctx = GetCtx(ctx_type)
  return _ast.Name(id=name_id,
                   ctx=ctx)


def Not():
  return _ast.Not()


def NotEq():
  return _ast.NotEq()


def NotIn():
  return _ast.NotIn()


def Num(number):
  """Creates an _ast.Num node."""
  return _ast.Num(number)


def Or():
  return _ast.Or()


def Pass():
  """Creates an _ast.Pass node."""
  return _ast.Pass()


def Pow():
  return _ast.Pow()


def Return(value):
  return _ast.Return(value=value)


def RShift():
  return _ast.RShift()


def Set(*items):
  """Creates an _ast.Set node.

  Args:
    *items: The items in the set.

  Returns:
    An _ast.Set node.
  """
  return _ast.Set(elts=list(items))


def SetComp(left_side, for_part, in_part, *ifs):
  """Creates _ast.SetComp nodes.

  'left_side' for 'for_part' in 'in_part' if 'ifs'

  Args:
    left_side: leftmost side of the expression.
    for_part: The part after '[left_side] for '
    in_part: The part after '[left_side] for [for_part] in '
    *ifs: Any if statements that come at the end.

  Returns:
    {_ast.SetComp}
  """
  left_side = _WrapWithName(left_side, ctx_type=CtxEnum.LOAD)
  for_part = _WrapWithName(for_part, ctx_type=CtxEnum.STORE)
  in_part = _WrapWithName(in_part, ctx_type=CtxEnum.LOAD)
  return _ast.SetComp(
      elt=left_side,
      generators=[comprehension(for_part, in_part, *ifs)])


def Slice(lower=None, upper=None, step=None):
  return _ast.Slice(lower=lower, upper=upper, step=step)


def Str(s):
  """Creates an _ast.Str node."""
  return _ast.Str(s=s)


def Sub():
  return _ast.Sub()


def Subscript(value, upper=None, lower=None, step=None, ctx=CtxEnum.STORE):
  value = _WrapWithName(value)
  return _ast.Subscript(
      value=value, slice=Slice(upper, lower, step), ctx=GetCtx(ctx))


class SyntaxFreeLine(_ast.stmt):
  """Class defining a new node that has no syntax (only optional comments)."""

  def __init__(self, comment=None, col_offset=0, comment_indent=1):
    super(SyntaxFreeLine, self).__init__()
    self.col_offset = col_offset
    self._fields = ['full_line']
    self.comment = comment
    self.comment_indent = comment_indent

  @property
  def full_line(self):
    if self.comment is not None:
      return '{}#{}{}'.format(' '*self.col_offset,
                              ' '*self.comment_indent,
                              self.comment)
    return ''

  @classmethod
  def MatchesStart(cls, text):
    return re.match('^([ \t]*)(?:|(#)([ \t]*)(.*))\n', text)

  def SetFromSrcLine(self, line):
    match = self.MatchesStart(line)
    if not match:
      raise ValueError('line {} is not a valid SyntaxFreeLine'.format(line))
    self.col_offset = len(match.group(1))
    self.comment_indent = 0
    self.comment = None
    if match.group(2):
      self.comment = ''
      if match.group(3):
        self.comment_indent = len(match.group(3))
      if match.group(4):
        self.comment = match.group(4)


def Tuple(*items, **kwargs):
  """Creates an _ast.Tuple node.

  Automatically adjusts inner ctx attrs.

  Args:
    *items: The items in the list.
    **kwargs: Only recognized kwarg is 'ctx_type', which controls the
      ctx type of the list. See CtxEnum.

  Returns:
    An _ast.Tuple node.
  """
  ctx_type = kwargs.pop('ctx_type', CtxEnum.LOAD)

  new_items = []
  for item in items:
    if isinstance(item, str):
      new_items.append(_WrapWithName(item))
    else:
      new_items.append(item)

  for item in new_items:
    if isinstance(item, _ast.Name):
      item.ctx = GetCtx(ctx_type)
    elif isinstance(item, _ast.Attribute):
      name_node = _LeftmostNodeInDotVar(item)
      name_node.ctx = GetCtx(ctx_type)
  ctx = GetCtx(ctx_type)
  return _ast.Tuple(elts=new_items,
                    ctx=ctx)


def TryExcept(body, except_handlers, orelse=None):
  return _ast.TryExcept(body=body, handlers=except_handlers, orelse=orelse)


def TryFinally(body, finalbody=None):
  finalbody = FormatAndValidateBody(finalbody)
  return _ast.TryFinally(body=body, finalbody=finalbody)


def UAdd():
  return _ast.UAdd()


def UnaryOp(operator, operand):
  """Operator literals ('not') also accepted."""
  if not isinstance(operator, _ast.AST):
    operator = UnaryOpMap(operator)
  return _ast.UnaryOp(op=operator, operand=operand)


def USub():
  return _ast.USub()


def With(with_part, as_part=None, body=None):
  """Creates an _ast.With node.

  Args:
    with_part: The part after "with ".
    as_part: The part after "with [with_part] as ".
    body: The body of the with statement.

  Returns:
    An _ast.With node.
  """
  body = FormatAndValidateBody(body)
  if as_part:
    ChangeCtx(as_part, CtxEnum.STORE)

  return _ast.With(context_expr=with_part,
                   optional_vars=as_part,
                   body=body)


###############################################################################
# Other Creators
###############################################################################


def GetCtx(ctx_type):
  """Creates Load, Store, Del, and Param, used in the ctx kwarg."""
  if ctx_type == CtxEnum.LOAD:
    return _ast.Load()
  elif ctx_type == CtxEnum.STORE:
    return _ast.Store()
  elif ctx_type == CtxEnum.DEL:
    return _ast.Del()
  elif ctx_type == CtxEnum.PARAM:
    return _ast.Param()
  raise InvalidCtx('ctx_type {} isn\'t a valid type'.format(ctx_type))


def UnaryOpMap(operator):
  """Maps operator strings for unary operations to their _ast node."""
  op_dict = {
      '+': _ast.UAdd,
      '-': _ast.USub,
      'not': _ast.Not,
      '~': _ast.Invert,
  }

  return op_dict[operator]()


def BinOpMap(operator):
  """Maps operator strings for binary operations to their _ast node."""
  op_dict = {
      '+': _ast.Add,
      '-': _ast.Sub,
      '*': _ast.Mult,
      '**': _ast.Pow,
      '/': _ast.Div,
      '//': _ast.FloorDiv,
      '%': _ast.Mod,
      '<<': _ast.LShift,
      '>>': _ast.RShift,
      '|': _ast.BitOr,
      '&': _ast.BitAnd,
      '^': _ast.BitXor,
  }

  return op_dict[operator]()


def BoolOpMap(operator):
  """Maps operator strings for boolean operations to their _ast node."""
  op_dict = {
      'and': _ast.And,
      'or': _ast.Or,
  }

  return op_dict[operator]()


def CompareOpMap(operator):
  """Maps operator strings for boolean operations to their _ast node."""
  op_dict = {
      '==': _ast.Eq,
      '!=': _ast.NotEq,
      '<': _ast.Lt,
      '<=': _ast.LtE,
      '>': _ast.Gt,
      '>=': _ast.GtE,
      'is': _ast.Is,
      'is not': _ast.IsNot,
      'in': _ast.In,
      'not in': _ast.NotIn,
  }

  return op_dict[operator]()


def VarReference(*parts, **kwargs):
  """By this we mean either a single name string or one or more Attr nodes.

  This is used whenever we have things like 'a' or 'a.b' or 'a.b.c'.

  Args:
    *parts: The parts that should be dot-separated.
    **kwargs: Only recognized kwarg is 'ctx_type', which controls the
      ctx type of the list. See CtxEnum.

  Raises:
    ValueError: When no parts are specified.

  Returns:
    An _ast.Name node or _ast.Attribute node
  """
  ctx_type = kwargs.pop('ctx_type', CtxEnum.LOAD)

  if not parts:
    raise ValueError('Must have at least one part specified')
  if len(parts) == 1:
    if isinstance(parts[0], str):
      return _ast.Name(id=parts[0], ctx=GetCtx(ctx_type))
    return parts[0]
  return _ast.Attribute(
      value=VarReference(*parts[:-1], **kwargs),
      attr=parts[-1],
      ctx=GetCtx(ctx_type))
