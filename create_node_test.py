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


Tests for google3.video.youtube.testing.tools.ast_refactor.create_node.
"""

import _ast
import ast
import unittest

import create_node


def GetNodeFromInput(string, body_index=0):
  return ast.parse(string).body[body_index]


def ExpandTree(node):
  node_fields = []
  to_expand = [node]
  while to_expand:
    current = to_expand.pop()
    if isinstance(current, ast.AST):
      node_fields.append(current.__class__)
      for field_name, child in ast.iter_fields(current):
        node_fields.append(field_name)
        if isinstance(child, (list, tuple)):
          for item in child:
            to_expand.append(item)
        else:
          to_expand.append(child)
    else:
      node_fields.append(current)
  print node_fields
  return node_fields


class CreateNodeTestBase(unittest.TestCase):

  def assertNodesEqual(self, node1, node2):
    node1_fields = ExpandTree(node1)
    node2_fields = ExpandTree(node2)
    self.assertEqual(node1_fields, node2_fields)

###############################################################################
# Node Creators
###############################################################################


class CreateArgumentsTest(CreateNodeTestBase):

  def testEmpty(self):
    expected_string = """def testFunc():
  pass"""
    expected_node = GetNodeFromInput(expected_string).args
    test_node = create_node.arguments()
    self.assertNodesEqual(expected_node, test_node)

  def testArgs(self):
    expected_string = """def testFunc(a, b):
  pass"""
    expected_node = GetNodeFromInput(expected_string).args
    test_node = create_node.arguments(args=('a', 'b'))
    self.assertNodesEqual(expected_node, test_node)

  def testStringKwargs(self):
    expected_string = """def testFunc(a='b', c='d'):
  pass"""
    expected_node = GetNodeFromInput(expected_string).args
    test_node = create_node.arguments(
        keys=['a', 'c'],
        values=[create_node.Str('b'), create_node.Str('d')])
    self.assertNodesEqual(expected_node, test_node)

  def testNameKwargs(self):
    expected_string = """def testFunc(a=b, c=d):
  pass"""
    expected_node = GetNodeFromInput(expected_string).args
    test_node = create_node.arguments(
        keys=['a', 'c'],
        values=[create_node.Name('b'), create_node.Name('d')])
    self.assertNodesEqual(expected_node, test_node)

  def testVararg(self):
    expected_string = """def testFunc(*args):
  pass"""
    expected_node = GetNodeFromInput(expected_string).args
    test_node = create_node.arguments(vararg_name='args')
    self.assertNodesEqual(expected_node, test_node)

  def testFunctionDefWithKwarg(self):
    expected_string = """def testFunc(**kwargs):
  pass"""
    expected_node = GetNodeFromInput(expected_string).args
    test_node = create_node.arguments(kwarg_name='kwargs')
    self.assertNodesEqual(expected_node, test_node)


class CreateAssertTest(CreateNodeTestBase):

  def testBasicAssert(self):
    expected_string = 'assert a'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Assert(
        create_node.Name('a'))
    self.assertNodesEqual(expected_node, test_node)

  def testAssertWithMessage(self):
    expected_string = 'assert a, "a failure"'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Assert(
        create_node.Name('a'),
        create_node.Str('a failure'))
    self.assertNodesEqual(expected_node, test_node)


class CreateAssignTest(CreateNodeTestBase):

  def testAssignWithSimpleString(self):
    expected_string = 'a = "b"'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Assign('a', create_node.Str('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testAssignWithNode(self):
    expected_string = 'a = "b"'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Assign(
        create_node.Name('a', ctx_type=create_node.CtxEnum.STORE),
        create_node.Str('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testAssignWithTuple(self):
    expected_string = '(a, c) = "b"'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Assign(
        create_node.Tuple('a', 'c', ctx_type=create_node.CtxEnum.STORE),
        create_node.Str('b'))
    self.assertNodesEqual(expected_node, test_node)


class CreateBinOpTest(CreateNodeTestBase):

  def testBinOpWithAdd(self):
    expected_string = 'a + b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '+',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithSub(self):
    expected_string = 'a - b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '-',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithMult(self):
    expected_string = 'a * b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '*',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithDiv(self):
    expected_string = 'a / b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '/',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithFloorDiv(self):
    expected_string = 'a // b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '//',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithMod(self):
    expected_string = 'a % b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '%',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithPow(self):
    expected_string = 'a ** b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '**',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithLShift(self):
    expected_string = 'a << b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '<<',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithRShift(self):
    expected_string = 'a >> b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '>>',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithBitOr(self):
    expected_string = 'a | b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '|',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithBitXor(self):
    expected_string = 'a ^ b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '^',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBinOpWithBitAnd(self):
    expected_string = 'a & b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BinOp(
        create_node.Name('a'),
        '&',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)


class CreateBoolOpTest(CreateNodeTestBase):

  def testBoolOpWithAnd(self):
    expected_string = 'a and b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BoolOp(
        create_node.Name('a'),
        'and',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBoolOpWithOr(self):
    expected_string = 'a or b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BoolOp(
        create_node.Name('a'),
        'or',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testBoolOpWithAndOr(self):
    expected_string = 'a and b or c'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BoolOp(
        create_node.Name('a'),
        'and',
        create_node.Name('b'),
        'or',
        create_node.Name('c'))
    self.assertNodesEqual(expected_node, test_node)

  def testBoolOpWithOrAnd(self):
    expected_string = 'a or b and c'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.BoolOp(
        create_node.Name('a'),
        'or',
        create_node.Name('b'),
        'and',
        create_node.Name('c'))
    self.assertNodesEqual(expected_node, test_node)


class CreateCallTest(CreateNodeTestBase):

  def testCallWithSimpleCaller(self):
    expected_string = 'a()'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call('a')
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithDotSeparatedCaller(self):
    expected_string = 'a.b()'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call('a.b')
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithAttributeNode(self):
    expected_string = 'a.b()'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call(create_node.VarReference('a', 'b'))
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithArgs(self):
    expected_string = 'a(b)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call('a', args=('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithKwargs(self):
    expected_string = 'a(b="c")'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call(
        'a', keys=('b',), values=(create_node.Str('c'),))
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithStarargsString(self):
    expected_string = 'a(*b)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call(
        'a', starargs='b')
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithStarargsNode(self):
    expected_string = 'a(*[b])'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call(
        'a', starargs=create_node.List(create_node.Name('b')))
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithKwargsString(self):
    expected_string = 'a(**b)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call(
        'a', kwargs='b')
    self.assertNodesEqual(expected_node, test_node)

  def testCallWithKwargsNode(self):
    expected_string = 'a(**{b:c})'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Call(
        'a',
        kwargs=create_node.Dict(
            keys=(create_node.Name('b'),),
            values=(create_node.Name('c'),)
        )
    )
    self.assertNodesEqual(expected_node, test_node)


class CreateClassDefTest(CreateNodeTestBase):

  def testBasicClass(self):
    expected_string = 'class TestClass():\n  pass'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.ClassDef('TestClass')
    self.assertNodesEqual(expected_node, test_node)

  def testBases(self):
    expected_string = 'class TestClass(Base1, Base2):\n  pass'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.ClassDef(
        'TestClass', bases=['Base1', 'Base2'])
    self.assertNodesEqual(expected_node, test_node)

  def testBody(self):
    expected_string = 'class TestClass(Base1, Base2):\n  a'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.ClassDef(
        'TestClass', bases=['Base1', 'Base2'],
        body=[create_node.Expr(create_node.Name('a'))])
    self.assertNodesEqual(expected_node, test_node)

  def testDecoratorList(self):
    expected_string = '@dec\n@dec2()\nclass TestClass():\n  pass\n'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.ClassDef(
        'TestClass',
        decorator_list=[create_node.Name('dec'),
                        create_node.Call('dec2')])
    self.assertNodesEqual(expected_node, test_node)


class CreateCompareTest(CreateNodeTestBase):

  def testBasicCompare(self):
    expected_string = 'a < b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        create_node.Lt(),
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testMultipleCompare(self):
    expected_string = 'a < b < c'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        create_node.Lt(),
        create_node.Name('b'),
        create_node.Lt(),
        create_node.Name('c'))
    self.assertNodesEqual(expected_node, test_node)

  def testEq(self):
    expected_string = 'a == b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        '==',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testNotEq(self):
    expected_string = 'a != b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        '!=',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testLt(self):
    expected_string = 'a < b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        '<',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testLtE(self):
    expected_string = 'a <= b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        '<=',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testGt(self):
    expected_string = 'a > b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        '>',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testGtE(self):
    expected_string = 'a >= b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        '>=',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testIs(self):
    expected_string = 'a is b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        'is',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testIsNot(self):
    expected_string = 'a is not b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        'is not',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testIn(self):
    expected_string = 'a in b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        'in',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testNotIn(self):
    expected_string = 'a not in b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Compare(
        create_node.Name('a'),
        'not in',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)


class CreateDictTest(CreateNodeTestBase):

  def testDictWithStringKeys(self):
    expected_string = '{"a": "b"}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Dict(
        [create_node.Str('a')],
        [create_node.Str('b')])
    self.assertNodesEqual(expected_node, test_node)

  def testDictWithNonStringKeys(self):
    expected_string = '{a: 1}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Dict(
        [create_node.Name('a')],
        [create_node.Num(1)])
    self.assertNodesEqual(expected_node, test_node)

  def testDictWithNoKeysOrVals(self):
    expected_string = '{}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Dict([], [])
    self.assertNodesEqual(expected_node, test_node)

  def testDictRaisesErrorIfNotMatchingLengths(self):
    with self.assertRaises(ValueError):
      unused_test_node = create_node.Dict(
          [create_node.Str('a')],
          [])


class CreateDictComprehensionTest(CreateNodeTestBase):

  def testBasicDictComprehension(self):
    expected_string = '{a: b for c in d}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.DictComp('a', 'b', 'c', 'd')
    self.assertNodesEqual(expected_node, test_node)

  def testBasicDictComprehensionWithIfs(self):
    expected_string = '{a: b for c in d if e < f}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.DictComp(
        'a', 'b', 'c', 'd',
        create_node.Compare('e', '<', 'f'))
    self.assertNodesEqual(expected_node, test_node)


class CreateFunctionDefTest(CreateNodeTestBase):

  def testFunctionDefWithArgs(self):
    expected_string = """def testFunc(a, b):
  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef('testFunc', args=('a', 'b'))
    self.assertNodesEqual(expected_node, test_node)

  def testFunctionDefWithStringKwargs(self):
    expected_string = """def testFunc(a='b', c='d'):
  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef(
        'testFunc', keys=['a', 'c'],
        values=[create_node.Str('b'), create_node.Str('d')])
    self.assertNodesEqual(expected_node, test_node)

  def testFunctionDefWithNameKwargs(self):
    expected_string = """def testFunc(a=b, c=d):
  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef(
        'testFunc', keys=['a', 'c'],
        values=[create_node.Name('b'), create_node.Name('d')])
    self.assertNodesEqual(expected_node, test_node)

  def testFunctionDefWithBody(self):
    expected_string = """def testFunc():
  a"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef(
        'testFunc', body=[create_node.Expr(create_node.Name('a'))])
    self.assertNodesEqual(expected_node, test_node)

  def testFunctionDefWithVararg(self):
    expected_string = """def testFunc(*args):
  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef(
        'testFunc', vararg_name='args')
    self.assertNodesEqual(expected_node, test_node)

  def testFunctionDefWithKwarg(self):
    expected_string = """def testFunc(**kwargs):
  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef(
        'testFunc', kwarg_name='kwargs')
    self.assertNodesEqual(expected_node, test_node)

  def testDecoratorList(self):
    expected_string = """@decorator
@other_decorator(arg)
def testFunc(**kwargs):
  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.FunctionDef(
        'testFunc', kwarg_name='kwargs',
        decorator_list=[
            create_node.Name('decorator'),
            create_node.Call('other_decorator', args=['arg'])
        ])
    self.assertNodesEqual(expected_node, test_node)


class CreateGeneratorExpTest(CreateNodeTestBase):

  def testBasicSetComprehension(self):
    expected_string = '(a for a in b)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.GeneratorExp('a', 'a', 'b')
    self.assertNodesEqual(expected_node, test_node)

  def testBasicGeneratorExpWithIfs(self):
    expected_string = '(a for a in b if c < d)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.GeneratorExp(
        'a', 'a', 'b',
        create_node.Compare('c', '<', 'd'))
    self.assertNodesEqual(expected_node, test_node)


class CreateIfTest(CreateNodeTestBase):

  def testBasicIf(self):
    expected_string = """if True:\n  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.If(
        create_node.Name('True'))
    self.assertNodesEqual(expected_node, test_node)

  def testBasicIfElse(self):
    expected_string = """if True:\n  pass\nelse:\n  pass"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.If(
        create_node.Name('True'), orelse=[create_node.Pass()])
    self.assertNodesEqual(expected_node, test_node)

  def testBasicIfElif(self):
    expected_string = """if True:
  pass
elif False:
  pass
"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False'))])
    self.assertNodesEqual(expected_node, test_node)

  def testIfInElse(self):
    expected_string = """if True:
  pass
else:
  if False:
    pass
"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False'))])
    self.assertNodesEqual(expected_node, test_node)

  def testIfAndOthersInElse(self):
    expected_string = """if True:
  pass
else:
  if False:
    pass
  True
"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False')),
                create_node.Expr(create_node.Name('True'))])
    self.assertNodesEqual(expected_node, test_node)


class CreateIfExpTest(CreateNodeTestBase):

  def testBasicIfExp(self):
    expected_string = """a if True else b"""
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.IfExp(
        create_node.Name('True'), create_node.Name('a'), create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)


class CreateImportTest(CreateNodeTestBase):

  def testImport(self):
    expected_string = """import foo"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Import(import_part='foo')
    self.assertNodesEqual(expected_node, test_node)

  def testImportAs(self):
    expected_string = """import foo as foobar"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Import(import_part='foo', asname='foobar')
    self.assertNodesEqual(expected_node, test_node)

  def testImportFrom(self):
    expected_string = """from bar import foo"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Import(import_part='foo', from_part='bar')
    self.assertNodesEqual(expected_node, test_node)

  def testImportFromAs(self):
    expected_string = """from bar import foo as foobar"""
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Import(
        import_part='foo', from_part='bar', asname='foobar')
    self.assertNodesEqual(expected_node, test_node)


class CreateListTest(CreateNodeTestBase):

  def testListLoad(self):
    expected_string = 'a = ["b"]'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.List(
        create_node.Str('b'), ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testListStore(self):
    expected_string = '[a, b] = ["c", "d"]'
    expected_node = GetNodeFromInput(expected_string).targets[0]
    test_node = create_node.List(
        create_node.Name('a'),
        create_node.Name('b'),
        ctx_type=create_node.CtxEnum.STORE)
    self.assertNodesEqual(expected_node, test_node)

  def testDeleteInvalid(self):
    expected_string = 'del [a, b]'
    expected_node = GetNodeFromInput(expected_string).targets[0]
    test_node = create_node.List(
        create_node.Name('a'),
        create_node.Name('b'),
        ctx_type=create_node.CtxEnum.DEL)
    self.assertNodesEqual(expected_node, test_node)

  def testListOverridesInnerCtx(self):
    expected_string = 'a = [b, c]'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.List(
        create_node.Name('b', ctx_type=create_node.CtxEnum.DEL),
        create_node.Name('c', ctx_type=create_node.CtxEnum.STORE),
        ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)


class CreateListComprehensionTest(CreateNodeTestBase):

  def testBasicListComprehension(self):
    expected_string = '[a for a in b]'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.ListComp('a', 'a', 'b')
    self.assertNodesEqual(expected_node, test_node)

  def testBasicListComprehensionWithIfs(self):
    expected_string = '[a for a in b if c < d]'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.ListComp(
        'a', 'a', 'b',
        create_node.Compare('c', '<', 'd'))
    self.assertNodesEqual(expected_node, test_node)


class CreateNameTest(CreateNodeTestBase):

  def testNameWithLoad(self):
    expected_string = 'b = a'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Name('a', ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testNameWithStore(self):
    expected_string = 'a = b'
    expected_node = GetNodeFromInput(expected_string).targets[0]
    test_node = create_node.Name('a', ctx_type=create_node.CtxEnum.STORE)
    self.assertNodesEqual(expected_node, test_node)

  def testNameWithDel(self):
    expected_string = 'del a'
    expected_node = GetNodeFromInput(expected_string).targets[0]
    test_node = create_node.Name('a', ctx_type=create_node.CtxEnum.DEL)
    self.assertNodesEqual(expected_node, test_node)


class CreateNumTest(CreateNodeTestBase):

  def testNumWithInteger(self):
    expected_string = '15'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Num(15)
    self.assertNodesEqual(expected_node, test_node)

  def testNumWithHex(self):
    expected_string = '0xa5'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Num(0xa5)
    self.assertNodesEqual(expected_node, test_node)

  def testNumWithFloat(self):
    expected_string = '0.25'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Num(0.25)
    self.assertNodesEqual(expected_node, test_node)


class CreatePassTest(CreateNodeTestBase):

  def testPass(self):
    expected_string = 'pass'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.Pass()
    self.assertNodesEqual(expected_node, test_node)


class CreateSetTest(CreateNodeTestBase):

  def testSet(self):
    expected_string = '{"a", "b"}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Set(
        create_node.Str('a'),
        create_node.Str('b'))
    self.assertNodesEqual(expected_node, test_node)


class CreateSetComprehensionTest(CreateNodeTestBase):

  def testBasicSetComprehension(self):
    expected_string = '{a for a in b}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.SetComp('a', 'a', 'b')
    self.assertNodesEqual(expected_node, test_node)

  def testBasicSetComprehensionWithIfs(self):
    expected_string = '{a for a in b if c < d}'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.SetComp(
        'a', 'a', 'b',
        create_node.Compare('c', '<', 'd'))
    self.assertNodesEqual(expected_node, test_node)


class CreateStrTest(CreateNodeTestBase):

  def testStr(self):
    expected_string = '"a"'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Str('a')
    self.assertNodesEqual(expected_node, test_node)


class CreateSyntaxFreeLineTest(CreateNodeTestBase):

  def testEmpty(self):
    expected_string = ''
    test_node = create_node.SyntaxFreeLine(comment=None)
    self.assertEqual(expected_string, test_node.full_line)

  def testSimpleComment(self):
    expected_string = '#Comment'
    test_node = create_node.SyntaxFreeLine(
        comment='Comment', col_offset=0, comment_indent=0)
    self.assertEqual(expected_string, test_node.full_line)

  def testColOffset(self):
    expected_string = '  #Comment'
    test_node = create_node.SyntaxFreeLine(
        comment='Comment', col_offset=2, comment_indent=0)
    self.assertEqual(expected_string, test_node.full_line)

  def testCommentIndent(self):
    expected_string = '  # Comment'
    test_node = create_node.SyntaxFreeLine(
        comment='Comment', col_offset=2, comment_indent=1)
    self.assertEqual(expected_string, test_node.full_line)

  def testSetFromSrcLineEmpty(self):
    test_input = '\n'
    test_node = create_node.SyntaxFreeLine()
    test_node.SetFromSrcLine(test_input)
    self.assertEqual(test_node.col_offset, 0)
    self.assertEqual(test_node.comment_indent, 0)
    self.assertEqual(test_node.comment, None)

  def testSetFromSrcLineVeryShortComment(self):
    test_input = '#\n'
    test_node = create_node.SyntaxFreeLine()
    test_node.SetFromSrcLine(test_input)
    self.assertEqual(test_node.col_offset, 0)
    self.assertEqual(test_node.comment_indent, 0)
    self.assertEqual(test_node.comment, '')

  def testSetFromSrcLineComment(self):
    test_input = '#Comment\n'
    test_node = create_node.SyntaxFreeLine()
    test_node.SetFromSrcLine(test_input)
    self.assertEqual(test_node.col_offset, 0)
    self.assertEqual(test_node.comment_indent, 0)
    self.assertEqual(test_node.comment, 'Comment')

  def testSetFromSrcLineIndentedComment(self):
    test_input = '  #Comment\n'
    test_node = create_node.SyntaxFreeLine()
    test_node.SetFromSrcLine(test_input)
    self.assertEqual(test_node.col_offset, 2)
    self.assertEqual(test_node.comment_indent, 0)
    self.assertEqual(test_node.comment, 'Comment')

  def testSetFromSrcLineOffsetComment(self):
    test_input = '  # Comment\n'
    test_node = create_node.SyntaxFreeLine()
    test_node.SetFromSrcLine(test_input)
    self.assertEqual(test_node.col_offset, 2)
    self.assertEqual(test_node.comment_indent, 1)
    self.assertEqual(test_node.comment, 'Comment')

  def testSetFromSrcLineDoubleComment(self):
    test_input = '  # Comment # More comment\n'
    test_node = create_node.SyntaxFreeLine()
    test_node.SetFromSrcLine(test_input)
    self.assertEqual(test_node.col_offset, 2)
    self.assertEqual(test_node.comment_indent, 1)
    self.assertEqual(test_node.comment, 'Comment # More comment')

  def testSetFromSrcLineNoComment(self):
    test_input = '  Comment\n'
    test_node = create_node.SyntaxFreeLine()
    with self.assertRaises(ValueError):
      test_node.SetFromSrcLine(test_input)


class CreateTupleTest(CreateNodeTestBase):

  def testTupleLoad(self):
    expected_string = 'a = ("b",)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Tuple(
        create_node.Str('b'), ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testTupleWithStrings(self):
    expected_string = 'a = (b,c)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Tuple(
        'b', 'c', ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testTupleStore(self):
    expected_string = '(a, b) = ["c", "d"]'
    expected_node = GetNodeFromInput(expected_string).targets[0]
    test_node = create_node.Tuple(
        create_node.Name('a'),
        create_node.Name('b'),
        ctx_type=create_node.CtxEnum.STORE)
    self.assertNodesEqual(expected_node, test_node)

  def testDeleteInvalid(self):
    expected_string = 'del (a, b)'
    expected_node = GetNodeFromInput(expected_string).targets[0]
    test_node = create_node.Tuple(
        create_node.Name('a'),
        create_node.Name('b'),
        ctx_type=create_node.CtxEnum.DEL)
    self.assertNodesEqual(expected_node, test_node)

  def testTupleOverridesInnerCtx(self):
    expected_string = 'a = (b, c)'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.Tuple(
        create_node.Name('b', ctx_type=create_node.CtxEnum.DEL),
        create_node.Name('c', ctx_type=create_node.CtxEnum.STORE),
        ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)


class CreateUnaryOpTest(CreateNodeTestBase):

  def testUnaryOpWithPositive(self):
    expected_string = '+b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.UnaryOp(
        '+',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testUnaryOpWithSub(self):
    expected_string = '-b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.UnaryOp(
        '-',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testUnaryOpWithNot(self):
    expected_string = 'not b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.UnaryOp(
        'not',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testUnaryOpWithInvert(self):
    expected_string = '~b'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.UnaryOp(
        '~',
        create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)


class CreateWithTest(CreateNodeTestBase):

  def testBasicWith(self):
    expected_string = 'with a:\n  pass\n'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.With(
        create_node.Name('a'))
    self.assertNodesEqual(expected_node, test_node)

  def testBasicWithAs(self):
    expected_string = 'with a as b:\n  pass\n'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.With(
        create_node.Name('a'), as_part=create_node.Name('b'))
    self.assertNodesEqual(expected_node, test_node)

  def testWithAsTuple(self):
    expected_string = 'with a as (b, c):\n  pass\n'
    expected_node = GetNodeFromInput(expected_string)
    test_node = create_node.With(
        create_node.Name('a'),
        as_part=create_node.Tuple(create_node.Name('b'),
                                  create_node.Name('c')))
    self.assertNodesEqual(expected_node, test_node)


###############################################################################
# Tests for Multiple-Node Creators
###############################################################################


class GetCtxTest(CreateNodeTestBase):

  def testGetLoad(self):
    self.assertIsInstance(create_node.GetCtx(create_node.CtxEnum.LOAD),
                          _ast.Load)

  def testGetStore(self):
    self.assertIsInstance(create_node.GetCtx(create_node.CtxEnum.STORE),
                          _ast.Store)

  def testGetDel(self):
    self.assertIsInstance(create_node.GetCtx(create_node.CtxEnum.DEL),
                          _ast.Del)

  def testGetParam(self):
    self.assertIsInstance(create_node.GetCtx(create_node.CtxEnum.PARAM),
                          _ast.Param)


class VarReferenceTest(CreateNodeTestBase):

  def testNoDotSeparated(self):
    expected_string = 'b = a'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.VarReference(
        'a', ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testSingleDotSeparated(self):
    expected_string = 'b = a.c'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.VarReference(
        'a', 'c',
        ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testDoubleDotSeparated(self):
    expected_string = 'b = a.c.d'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.VarReference(
        'a', 'c', 'd',
        ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)

  def testStringAsFirst(self):
    expected_string = 'b = "a".c.d'
    expected_node = GetNodeFromInput(expected_string).value
    test_node = create_node.VarReference(
        create_node.Str('a'), 'c', 'd',
        ctx_type=create_node.CtxEnum.LOAD)
    self.assertNodesEqual(expected_node, test_node)


if __name__ == '__main__':
  unittest.main()
