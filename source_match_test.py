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


Tests for source_match.py
"""

import unittest

import create_node
import source_match

DEFAULT_TEXT = 'default'


class TextPlaceholderTest(unittest.TestCase):

  def testMatchSimpleText(self):
    placeholder = source_match.TextPlaceholder('.*', DEFAULT_TEXT)
    matched_text = placeholder.Match(None, 'to match')
    self.assertEqual(matched_text, 'to match')
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, 'to match')

  def testPartialMatchEnd(self):
    placeholder = source_match.TextPlaceholder(r'def \(', DEFAULT_TEXT)
    matched_text = placeholder.Match(None, 'def (foo')
    self.assertEqual(matched_text, 'def (')
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, 'def (')

  def testMatchWithoutMatchingReturnsDefault(self):
    placeholder = source_match.TextPlaceholder('.*', DEFAULT_TEXT)
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, DEFAULT_TEXT)

  def testCantMatchThrowsError(self):
    placeholder = source_match.TextPlaceholder('doesnt match', DEFAULT_TEXT)
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      placeholder.Match(None, 'to match')

  def testMatchWhitespace(self):
    whitespace_text = '  \t \n  '
    placeholder = source_match.TextPlaceholder(r'\s*')
    matched_text = placeholder.Match(None, whitespace_text)
    self.assertEqual(matched_text, whitespace_text)
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, whitespace_text)

  def testWhitespaceMatchesLineContinuations(self):
    whitespace_text = '  \t \n \\\n  \\\n  '
    placeholder = source_match.TextPlaceholder(r'\s*')
    matched_text = placeholder.Match(None, whitespace_text)
    self.assertEqual(matched_text, whitespace_text)
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, whitespace_text)

  def testWhitespaceMatchesComments(self):
    whitespace_text = '  \t # abc\n  '
    placeholder = source_match.TextPlaceholder(r'\s*')
    matched_text = placeholder.Match(None, whitespace_text)
    self.assertEqual(matched_text, whitespace_text)
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, whitespace_text)

  def testMultipleStatementsSeparatedBySemicolon(self):
    whitespace_text = 'pdb;pdb'
    placeholder = source_match.TextPlaceholder(r'pdb\npdb')
    matched_text = placeholder.Match(None, whitespace_text)
    self.assertEqual(matched_text, whitespace_text)
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, whitespace_text)

  def testCommentAfterExpectedLinebreak(self):
    whitespace_text = 'pdb  # A comment\n'
    placeholder = source_match.TextPlaceholder(r'pdb\n')
    matched_text = placeholder.Match(None, whitespace_text)
    self.assertEqual(matched_text, whitespace_text)
    test_output = placeholder.GetSource(None)
    self.assertEqual(test_output, whitespace_text)


class FieldPlaceholderTest(unittest.TestCase):

  def testMatchSimpleField(self):
    node = create_node.Name('foobar')
    placeholder = source_match.FieldPlaceholder('id')
    matched_text = placeholder.Match(node, 'foobar')
    self.assertEqual(matched_text, 'foobar')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar')

  def testPartialMatch(self):
    node = create_node.Name('bar')
    placeholder = source_match.FieldPlaceholder(
        'id', before_placeholder=source_match.TextPlaceholder('foo'))
    matched_text = placeholder.Match(node, 'foobarbaz')
    self.assertEqual(matched_text, 'foobar')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar')

  def testBeforePlaceholder(self):
    node = create_node.Name('bar')
    placeholder = source_match.FieldPlaceholder(
        'id',
        before_placeholder=source_match.TextPlaceholder('before '))
    matched_text = placeholder.Match(node, 'before bar')
    self.assertEqual(matched_text, 'before bar')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'before bar')

  def testCantMatchThrowsError(self):
    node = create_node.Name('doesnt_match')
    placeholder = source_match.FieldPlaceholder('id')
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      placeholder.Match(node, 'to match')

  def testRaisesErrorIfFieldIsList(self):
    node = create_node.FunctionDef('function_name')
    placeholder = source_match.FieldPlaceholder('body')
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      placeholder.Match(node, 'invalid_match')

  def testChangingValueChangesOutput(self):
    node = create_node.Name('bar')
    placeholder = source_match.FieldPlaceholder(
        'id', before_placeholder=source_match.TextPlaceholder('foo'))
    matched_text = placeholder.Match(node, 'foobarbaz')
    self.assertEqual(matched_text, 'foobar')
    node.id = 'hello'
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foohello')

  def testWithoutMatch(self):
    node = create_node.Name('bar')
    placeholder = source_match.FieldPlaceholder('id')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'bar')


class ListFieldPlaceholderTest(unittest.TestCase):

  def testMatchSimpleField(self):
    body_node = create_node.Expr(create_node.Name('foobar'))
    node = create_node.FunctionDef('function_name', body=[body_node])
    placeholder = source_match.ListFieldPlaceholder('body')
    matched_text = placeholder.Match(node, 'foobar\n')
    self.assertEqual(matched_text, 'foobar\n')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar\n')

  def testMultipleListItems(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    placeholder = source_match.ListFieldPlaceholder('body')
    matched_text = placeholder.Match(node, 'foobar\nbaz\n')
    self.assertEqual(matched_text, 'foobar\nbaz\n')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar\nbaz\n')

  def testMultipleListItemsBeginningAndEnd(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    placeholder = source_match.ListFieldPlaceholder(
        'body',
        before_placeholder=source_match.TextPlaceholder('z'),
        after_placeholder=source_match.TextPlaceholder('zz'))
    matched_text = placeholder.Match(node, 'zfoobar\nzzzbaz\nzz')
    self.assertEqual(matched_text, 'zfoobar\nzzzbaz\nzz')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'zfoobar\nzzzbaz\nzz')

  def testMatchRaisesErrorIfFieldIsNotList(self):
    node = create_node.Name('bar')
    placeholder = source_match.ListFieldPlaceholder(
        'id', before_placeholder=source_match.TextPlaceholder('\n', '\n'),
        exclude_first_before=True)
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      placeholder.Match(node, 'foobar\nbaz')

  def testMatchRaisesErrorIfFieldDoesntMatch(self):
    body_node = create_node.Expr(create_node.Name('foobar'))
    node = create_node.FunctionDef('function_name', body=[body_node])
    placeholder = source_match.ListFieldPlaceholder(
        'body', before_placeholder=source_match.TextPlaceholder('\n', '\n'),
        exclude_first_before=True)
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      placeholder.Match(node, 'no match here')

  def testMatchRaisesErrorIfSeparatorDoesntMatch(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    placeholder = source_match.ListFieldPlaceholder(
        'body', before_placeholder=source_match.TextPlaceholder('\n', '\n'),
        exclude_first_before=True)
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      placeholder.Match(node, 'foobarbaz')

  # TODO: Renabled this after adding indent information to matchers
  @unittest.expectedFailure
  def testListDefaults(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    module_node = create_node.Module(node)
    placeholder = source_match.ListFieldPlaceholder(
        'body', before_placeholder=source_match.TextPlaceholder('', ', '),
        exclude_first_before=True)
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, '  foobar\n,   baz\n')


class BodyPlaceholderTest(unittest.TestCase):

  def testMatchSimpleField(self):
    body_node = create_node.Expr(create_node.Name('foobar'))
    node = create_node.Module(body_node)
    placeholder = source_match.BodyPlaceholder('body')
    matched_text = placeholder.Match(node, 'foobar\n')
    self.assertEqual(matched_text, 'foobar\n')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar\n')

  def testMatchFieldAddsEmptySyntaxFreeLine(self):
    body_node_foobar = create_node.Expr(create_node.Name('foobar'))
    body_node_a = create_node.Expr(create_node.Name('a'))
    node = create_node.Module(body_node_foobar, body_node_a)
    placeholder = source_match.BodyPlaceholder('body')
    matched_text = placeholder.Match(node, 'foobar\n\na\n')
    self.assertEqual(matched_text, 'foobar\n\na\n')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar\n\na\n')

  def testMatchFieldAddsEmptySyntaxFreeLineWithComment(self):
    body_node_foobar = create_node.Expr(create_node.Name('foobar'))
    body_node_a = create_node.Expr(create_node.Name('a'))
    node = create_node.Module(body_node_foobar, body_node_a)
    placeholder = source_match.BodyPlaceholder('body')
    matched_text = placeholder.Match(node, 'foobar\n#blah\na\n')
    self.assertEqual(matched_text, 'foobar\n#blah\na\n')
    test_output = placeholder.GetSource(node)
    self.assertEqual(test_output, 'foobar\n#blah\na\n')

  def testDoesntMatchAfterEndOfBody(self):
    body_node_foobar = create_node.Expr(create_node.Name('foobar'))
    body_node_a = create_node.Expr(create_node.Name('a'))
    node = create_node.FunctionDef('a', body=[body_node_foobar, body_node_a])
    matcher = source_match.GetMatcher(node)
    text_to_match = """def a():
  foobar
  #blah
  a

# end comment
c
"""
    matched_text = matcher.Match(text_to_match)
    expected_match = """def a():
  foobar
  #blah
  a
"""
    self.assertEqual(matched_text, expected_match)


class TestDefaultSourceMatcher(unittest.TestCase):

  def testInvalidExpectedPartsType(self):
    node = create_node.Name('bar')
    with self.assertRaises(ValueError):
      source_match.DefaultSourceMatcher(node, ['blah'])

  def testBasicTextMatch(self):
    matcher = source_match.DefaultSourceMatcher(
        None, [source_match.TextPlaceholder('blah', DEFAULT_TEXT)])
    matcher.Match('blah')
    self.assertEqual(matcher.GetSource(), 'blah')

  def testRaisesErrorIfNoTextMatch(self):
    matcher = source_match.DefaultSourceMatcher(
        None, [source_match.TextPlaceholder('blah', DEFAULT_TEXT)])
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      matcher.Match('bla')

  def testBasicFieldMatch(self):
    node = create_node.Name('bar')
    matcher = source_match.DefaultSourceMatcher(
        node, [source_match.FieldPlaceholder('id')])
    matcher.Match('bar')
    self.assertEqual(matcher.GetSource(), 'bar')

  def testRaisesErrorIfNoFieldMatch(self):
    node = create_node.Name('bar')
    matcher = source_match.DefaultSourceMatcher(
        node, [source_match.FieldPlaceholder('id')])
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      matcher.Match('ba')

  def testBasicFieldMatchWhenChangedFieldValue(self):
    node = create_node.Name('bar')
    matcher = source_match.DefaultSourceMatcher(
        node, [source_match.FieldPlaceholder('id')])
    matcher.Match('bar')
    node.id = 'foo'
    self.assertEqual(matcher.GetSource(), 'foo')

  def testBasicListMatch(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    matcher = source_match.DefaultSourceMatcher(
        node, [source_match.ListFieldPlaceholder('body')])
    matcher.Match('foobar\nbaz\n')
    self.assertEqual(matcher.GetSource(), 'foobar\nbaz\n')

  def testRaisesErrorWhenNoMatchInBasicList(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    matcher = source_match.DefaultSourceMatcher(
        node, [source_match.ListFieldPlaceholder('body')])
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      matcher.Match('foobar\nba\n')

  def testBasicListMatchWhenChangedFieldValue(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    matcher = source_match.DefaultSourceMatcher(
        node,
        [source_match.ListFieldPlaceholder('body')])
    matcher.Match('foobar\nbaz\n')
    node.body[0].value.id = 'hello'
    self.assertEqual(matcher.GetSource(), 'hello\nbaz\n')

  def testAdvancedMatch(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    matcher = source_match.DefaultSourceMatcher(
        node,
        [source_match.TextPlaceholder('def ', 'def '),
         source_match.FieldPlaceholder('name'),
         source_match.TextPlaceholder(r'\(\)', r'()'),
         source_match.ListFieldPlaceholder('body')])
    matcher.Match('def function_name()foobar\nbaz\n')
    node.body[0].value.id = 'hello'
    self.assertEqual(matcher.GetSource(), 'def function_name()hello\nbaz\n')

  # TODO: Renabled this after adding indent information to matchers
  @unittest.expectedFailure
  def testGetSourceWithoutMatchUsesDefaults(self):
    body_nodes = [create_node.Expr(create_node.Name('foobar')),
                  create_node.Expr(create_node.Name('baz'))]
    node = create_node.FunctionDef('function_name', body=body_nodes)
    module_node = create_node.Module(node)
    matcher = source_match.DefaultSourceMatcher(
        node,
        [source_match.TextPlaceholder('def ', 'default '),
         source_match.FieldPlaceholder('name'),
         source_match.TextPlaceholder(r'\(\)', r'()'),
         source_match.SeparatedListFieldPlaceholder(
             'body', source_match.TextPlaceholder('\n', ', '))])
    node.body[0].value.id = 'hello'
    self.assertEqual(matcher.GetSource(),
                     'default function_name()  hello\n,   baz\n')


class TestGetMatcher(unittest.TestCase):

  def testDefaultMatcher(self):
    node = create_node.VarReference('foo', 'bar')
    matcher = source_match.GetMatcher(node)
    matcher.Match('foo.bar')
    self.assertEqual(matcher.GetSource(), 'foo.bar')

  def testDefaultMatcherWithModification(self):
    node = create_node.VarReference('foo', 'bar')
    matcher = source_match.GetMatcher(node)
    matcher.Match('foo.bar')
    node.attr = 'hello'
    self.assertEqual(matcher.GetSource(), 'foo.hello')


class ParenWrappedTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Name('a')
    string = '(a)'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testNewLineMatch(self):
    node = create_node.Name('a')
    string = '(\na\n)'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testWithComplexLine(self):
    node = create_node.Compare('a', '<', 'c')
    string = '(a < \n c\n)'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testWithTuple(self):
    node = create_node.Call('c', args=[create_node.Name('d'),
                                       create_node.Tuple('a', 'b')])
    string = 'c(d, (a, b))'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class ArgumentsMatcherTest(unittest.TestCase):

  def testEmpty(self):
    node = create_node.arguments()
    string = ''
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testSingleArg(self):
    node = create_node.arguments(args=('a'))
    string = 'a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMultipleArgs(self):
    node = create_node.arguments(args=('a', 'b'))
    string = 'a, b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testDefault(self):
    node = create_node.arguments(keys=('a'), values=('b'))
    string = 'a=b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testDefaults(self):
    node = create_node.arguments(keys=('a', 'c'), values=('b', 'd'))
    string = 'a=b, c=d'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testArgsAndDefaults(self):
    node = create_node.arguments(
        args=('e', 'f'), keys=('a', 'c'), values=('b', 'd'))
    string = 'e, f, a=b, c=d'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testArgsDefaultsVarargs(self):
    node = create_node.arguments(
        args=('e', 'f'), keys=('a', 'c'), values=('b', 'd'),
        vararg_name='args')
    string = 'e, f, a=b, c=d, *args'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testArgsDefaultsVarargsKwargs(self):
    node = create_node.arguments(
        args=('e', 'f'), keys=('a', 'c'), values=('b', 'd'),
        vararg_name='args', kwarg_name='kwargs')
    string = 'e, f, a=b, c=d, *args, **kwargs'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class AssertMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Assert(create_node.Name('a'))
    string = 'assert a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithMessage(self):
    node = create_node.Assert(create_node.Name('a'),
                              create_node.Str('message'))
    string = 'assert a, "message"\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class AttributeMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.VarReference('a', 'b')
    string = 'a.b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testTripleReferenceMatch(self):
    node = create_node.VarReference('a', 'b', 'c')
    string = 'a.b.c'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class AugAssignMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.AugAssign('a', create_node.Add(), create_node.Num(1))
    string = 'a += 1\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class BinOpMatcherTest(unittest.TestCase):

  def testAddBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.Add(),
        create_node.Name('b'))
    string = 'a + b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testSubBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.Sub(),
        create_node.Name('b'))
    string = 'a - b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMultBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.Mult(),
        create_node.Name('b'))
    string = 'a * b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testDivBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.Div(),
        create_node.Name('b'))
    string = 'a / b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testFloorDivBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.FloorDiv(),
        create_node.Name('b'))
    string = 'a // b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testModBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.Mod(),
        create_node.Name('b'))
    string = 'a % b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testPowBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.Pow(),
        create_node.Name('b'))
    string = 'a ** b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testLShiftBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.LShift(),
        create_node.Name('b'))
    string = 'a << b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testRShiftBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.RShift(),
        create_node.Name('b'))
    string = 'a >> b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBitOrBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.BitOr(),
        create_node.Name('b'))
    string = 'a | b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBitXorBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.BitXor(),
        create_node.Name('b'))
    string = 'a ^ b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBitAndBinOp(self):
    node = create_node.BinOp(
        create_node.Name('a'),
        create_node.BitAnd(),
        create_node.Name('b'))
    string = 'a & b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class BoolOpMatcherTest(unittest.TestCase):

  def testAndBoolOp(self):
    node = create_node.BoolOp(
        create_node.Name('a'),
        create_node.And(),
        create_node.Name('b'))
    string = 'a and b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testOrBoolOp(self):
    node = create_node.BoolOp(
        create_node.Name('a'),
        create_node.Or(),
        create_node.Name('b'))
    string = 'a or b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testAndOrBoolOp(self):
    node = create_node.BoolOp(
        create_node.Name('a'),
        create_node.And(),
        create_node.Name('b'),
        create_node.Or(),
        create_node.Name('c'))
    string = 'a and b or c'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testOrAndBoolOp(self):
    node = create_node.BoolOp(
        create_node.Name('a'),
        create_node.Or(),
        create_node.Name('b'),
        create_node.And(),
        create_node.Name('c'))
    string = 'a or b and c'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class CallMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Call('a')
    string = 'a()'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchStarargs(self):
    node = create_node.Call('a', starargs='args')
    string = 'a(*args)'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithStarargsBeforeKeyword(self):
    node = create_node.Call('a', keys=('b',), values=('c',), starargs='args')
    string = 'a(*args, b=c)'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class ClassDefMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.ClassDef('TestClass')
    string = 'class TestClass():\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchBases(self):
    node = create_node.ClassDef(
        'TestClass', bases=('Base1', 'Base2'))
    string = 'class TestClass(Base1, Base2):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchBody(self):
    node = create_node.ClassDef(
        'TestClass', body=[create_node.Expr(create_node.Name('a'))])
    string = 'class TestClass():\n  a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchDecoratorList(self):
    node = create_node.ClassDef(
        'TestClass',
        decorator_list=[create_node.Name('dec'),
                        create_node.Call('dec2')])
    string = '@dec\n@dec2()\nclass TestClass():\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testComplete(self):
    node = create_node.ClassDef(
        'TestClass',
        bases=('Base1', 'Base2'),
        body=[create_node.Expr(create_node.Name('a'))],
        decorator_list=[create_node.Name('dec'),
                        create_node.Call('dec2')])
    string = '@dec\n@dec2()\nclass TestClass(Base1, Base2):\n  a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testCanChangeValues(self):
    node = create_node.ClassDef(
        'TestClass',
        bases=('Base1', 'Base2'),
        body=[create_node.Expr(create_node.Name('a'))],
        decorator_list=[create_node.Name('dec'),
                        create_node.Call('dec2')])
    string = '@dec\n@dec2()\nclass TestClass(Base1, Base2):\n  a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.bases = [create_node.Name('Base3')]
    node.decorator_list = [create_node.Name('dec3')]
    node.body[0].value.id = 'x'
    node.name = 'TestClass2'
    changed_string = '@dec3\nclass TestClass2(Base3):\n  x\n'
    self.assertEqual(changed_string, matcher.GetSource())


class CompareMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.Lt(),
        create_node.Name('b'))
    string = 'a < b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMultiMatch(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.Lt(),
        create_node.Name('b'),
        create_node.Lt(),
        create_node.Name('c'))
    string = 'a < b < c'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testEq(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.Eq(),
        create_node.Name('b'))
    string = 'a == b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testNotEq(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.NotEq(),
        create_node.Name('b'))
    string = 'a != b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testLt(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.Lt(),
        create_node.Name('b'))
    string = 'a < b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testLtE(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.LtE(),
        create_node.Name('b'))
    string = 'a <= b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testGt(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.Gt(),
        create_node.Name('b'))
    string = 'a > b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testGtE(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.GtE(),
        create_node.Name('b'))
    string = 'a >= b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testIs(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.Is(),
        create_node.Name('b'))
    string = 'a is b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testIsNot(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.IsNot(),
        create_node.Name('b'))
    string = 'a is not b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testIn(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.In(),
        create_node.Name('b'))
    string = 'a in b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testNotIn(self):
    node = create_node.Compare(
        create_node.Name('a'),
        create_node.NotIn(),
        create_node.Name('b'))
    string = 'a not in b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class ComprehensionMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.comprehension('a', 'b')
    string = 'for a in b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithIf(self):
    node = create_node.comprehension(
        'a', 'b',
        create_node.Compare('c', '<', 'd'))
    string = 'for a in b if c < d'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class DictMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Dict([create_node.Name('a')],
                            [create_node.Name('b')])
    string = '{a: b}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testEmptyMatch(self):
    node = create_node.Dict()
    string = '{}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testTwoItemMatch(self):
    node = create_node.Dict(
        [create_node.Name('a'), create_node.Str('c')],
        [create_node.Name('b'), create_node.Str('d')])
    string = '{a: b, "c": "d"}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testChangeKey(self):
    first_key = create_node.Name('a')
    node = create_node.Dict(
        [first_key, create_node.Str('c')],
        [create_node.Name('b'), create_node.Str('d')])
    string = '{a: b, "c": "d"}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    first_key.id = 'k'
    self.assertEqual('{k: b, "c": "d"}', matcher.GetSource())

  def testChangeVal(self):
    first_val = create_node.Name('b')
    node = create_node.Dict(
        [create_node.Name('a'), create_node.Str('c')],
        [first_val, create_node.Str('d')])
    string = '{a: b, "c": "d"}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    first_val.id = 'k'
    self.assertEqual('{a: k, "c": "d"}', matcher.GetSource())


class DictComprehensionMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.DictComp('e', 'f', 'a', 'b')
    string = '{e: f for a in b}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithIf(self):
    node = create_node.DictComp(
        'e', 'f', 'a', 'b',
        create_node.Compare('c', '<', 'd'))
    string = '{e: f for a in b if c < d}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class ExceptHandlerMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.ExceptHandler()
    string = 'except:\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithType(self):
    node = create_node.ExceptHandler('TestException')
    string = 'except TestException:\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithName(self):
    node = create_node.ExceptHandler('TestException', name='as_part')
    string = 'except TestException as as_part:\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithBody(self):
    node = create_node.ExceptHandler(
        body=[create_node.Expr(create_node.Name('a'))])
    string = 'except:\n  a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class FunctionDefMatcherTest(unittest.TestCase):

  def testEmpty(self):
    node = create_node.FunctionDef('test_fun')
    string = 'def test_fun():\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testSingleArg(self):
    node = create_node.FunctionDef('test_fun', args=('a'))
    string = 'def test_fun(a):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMultipleArgs(self):
    node = create_node.FunctionDef('test_fun', args=('a', 'b'))
    string = 'def test_fun(a, b):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testDefault(self):
    node = create_node.FunctionDef('test_fun', keys=('a'), values=('b'))
    string = 'def test_fun(a=b):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testDefaults(self):
    node = create_node.FunctionDef(
        'test_fun', keys=('a', 'c'), values=('b', 'd'))
    string = 'def test_fun(a=b, c=d):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testArgsAndDefaults(self):
    node = create_node.FunctionDef(
        'test_fun', args=('e', 'f'), keys=('a', 'c'), values=('b', 'd'))
    string = 'def test_fun(e, f, a=b, c=d):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testArgsDefaultsVarargs(self):
    node = create_node.FunctionDef(
        'test_fun', args=('e', 'f'), keys=('a', 'c'), values=('b', 'd'),
        vararg_name='args')
    string = 'def test_fun(e, f, a=b, c=d, *args):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testArgsDefaultsVarargsKwargs(self):
    node = create_node.FunctionDef(
        'test_fun', args=('e', 'f'), keys=('a', 'c'), values=('b', 'd'),
        vararg_name='args', kwarg_name='kwargs')
    string = 'def test_fun(e, f, a=b, c=d, *args, **kwargs):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testDecoratorList(self):
    node = create_node.FunctionDef(
        'test_fun',
        decorator_list=[create_node.Name('dec'),
                        create_node.Call('call_dec')])
    string = '@dec\n@call_dec()\ndef test_fun():\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testCommentInDecoratorList(self):
    node = create_node.FunctionDef(
        'test_fun',
        decorator_list=[create_node.Name('dec'),
                        create_node.Call('call_dec')])
    string = '@dec\n#hello world\n@call_dec()\ndef test_fun():\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBody(self):
    node = create_node.FunctionDef(
        'test_fun',
        body=(create_node.Expr(create_node.Name('a')),))
    string = 'def test_fun():\n  a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class IfMatcherTest(unittest.TestCase):

  def testBasicIf(self):
    node = create_node.If(
        create_node.Name('True'))
    string = """if True:\n  pass\n"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicIfElse(self):
    node = create_node.If(
        create_node.Name('True'), orelse=[create_node.Pass()])
    string = """if True:\n  pass\nelse:\n  pass\n"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicIfElif(self):
    node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False'))])
    string = """if True:
  pass
elif False:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testIfElifWithSpace(self):
    node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False'))])
    string = """if True:
  pass

elif False:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testIfInElse(self):
    node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False'))])
    string = """if True:
  pass
else:
  if False:
    pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testIfAndOthersInElse(self):
    node = create_node.If(
        create_node.Name('True'),
        orelse=[create_node.If(create_node.Name('False')),
                create_node.Expr(create_node.Name('True'))])
    string = """if True:
  pass
else:
  if False:
    pass
  True
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class IfExpMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.IfExp(
        create_node.Name('True'), create_node.Name('a'), create_node.Name('b'))
    string = 'a if True else b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testChangeParts(self):
    node = create_node.IfExp(
        create_node.Name('True'), create_node.Name('a'), create_node.Name('b'))
    string = 'a if True else b'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.test = create_node.Name('False')
    node.body = create_node.Name('c')
    node.orelse = create_node.Name('d')
    self.assertEqual('c if False else d', matcher.GetSource())


class LambdaMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Lambda(create_node.Name('a'))
    string = 'lambda: a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithArgs(self):
    node = create_node.Lambda(
        create_node.Name('a'),
        args=create_node.arguments(args=('b')))
    string = 'lambda b: a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithArgsOnNewLine(self):
    node = create_node.Lambda(
        create_node.Name('a'),
        args=create_node.arguments(args=('b')))
    string = '(lambda\nb: a)'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class ListComprehensionMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.ListComp('c', 'a', 'b')
    string = '[c for a in b]'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithIf(self):
    node = create_node.ListComp(
        'c', 'a', 'b',
        create_node.Compare('c', '<', 'd'))
    string = '[c for a in b if c < d]'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class ModuleMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Module(create_node.Expr(create_node.Name('a')))
    string = 'a\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithEmptyLines(self):
    node = create_node.Module(
        create_node.Expr(create_node.Name('a')),
        create_node.Expr(create_node.Name('b')))
    string = 'a\n\nb\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithCommentLines(self):
    node = create_node.Module(
        create_node.Expr(create_node.Name('a')),
        create_node.Expr(create_node.Name('b')))
    string = 'a\n#blah\nb\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class NameMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Name('foobar')
    string = 'foobar'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('foobar', matcher.GetSource())

  def testIdChange(self):
    node = create_node.Name('foobar')
    string = 'foobar'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.id = 'hello'
    self.assertEqual('hello', matcher.GetSource())


class NumMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Num('1')
    string = '1'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('1', matcher.GetSource())

  def testBasicMatchWithSuffix(self):
    node = create_node.Num('1')
    string = '1L'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('1L', matcher.GetSource())


class SetMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Set('c', 'a', 'b')
    string = '{c, a, b}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class SetComprehensionMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.SetComp('c', 'a', 'b')
    string = '{c for a in b}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithIf(self):
    node = create_node.SetComp(
        'c', 'a', 'b',
        create_node.Compare('c', '<', 'd'))
    string = '{c for a in b if c < d}'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class StrMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.Str('foobar')
    string = '"foobar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('"foobar"', matcher.GetSource())

  def testPrefixMatch(self):
    node = create_node.Str('foobar')
    string = 'r"foobar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('r"foobar"', matcher.GetSource())

  def testQuoteWrapped(self):
    node = create_node.Str('foobar')
    string = '("foobar")'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('("foobar")', matcher.GetSource())

  def testContinuationMatch(self):
    node = create_node.Str('foobar')
    string = '"foo"\n"bar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('"foo"\n"bar"', matcher.GetSource())

  def testContinuationMatchWithPrefix(self):
    node = create_node.Str('foobar')
    string = '"foo"\nr"bar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('"foo"\nr"bar"', matcher.GetSource())

  def testBasicTripleQuoteMatch(self):
    node = create_node.Str('foobar')
    string = '"""foobar"""'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('"""foobar"""', matcher.GetSource())

  def testMultilineTripleQuoteMatch(self):
    node = create_node.Str('foobar\n\nbaz')
    string = '"""foobar\n\nbaz"""'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('"""foobar\n\nbaz"""', matcher.GetSource())

  def testQuoteTypeMismatch(self):
    node = create_node.Str('foobar')
    string = '"foobar\''
    matcher = source_match.GetMatcher(node)
    with self.assertRaises(ValueError):
      matcher.Match(string)

  def testSChange(self):
    node = create_node.Str('foobar')
    string = '"foobar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.s = 'hello'
    self.assertEqual('"hello"', matcher.GetSource())

  def testSChangeInContinuation(self):
    node = create_node.Str('foobar')
    string = '"foo"\n"bar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.s = 'foobaz'
    self.assertEqual('"foobaz"', matcher.GetSource())

  def testQuoteTypeChange(self):
    node = create_node.Str('foobar')
    string = '"foobar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    matcher.quote_type = "'"
    self.assertEqual("'foobar'", matcher.GetSource())

  def testQuoteTypeChangeToTripleQuote(self):
    node = create_node.Str('foobar')
    string = '"foobar"'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    matcher.quote_type = "'''"
    self.assertEqual("'''foobar'''", matcher.GetSource())


class SubscriptMatcherTest(unittest.TestCase):
  """Tests for the SyntaxFreeLine matcher."""

  def testBasicMatch(self):
    node = create_node.Subscript('a', 1)
    string = 'a[1]'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('a[1]', matcher.GetSource())

  def testAllPartsMatch(self):
    node = create_node.Subscript('a', 1, 2, 3)
    string = 'a[1:2:3]'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('a[1:2:3]', matcher.GetSource())

  def testSeparatedWithStrings(self):
    node = create_node.Subscript('a', 1, 2, 3)
    string = 'a [ 1 : 2 : 3 ]'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('a [ 1 : 2 : 3 ]', matcher.GetSource())


class SyntaxFreeLineMatcherTest(unittest.TestCase):
  """Tests for the SyntaxFreeLine matcher."""

  def testBasicMatch(self):
    node = create_node.SyntaxFreeLine()
    string = '\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('\n', matcher.GetSource())

  def testVeryShortMatch(self):
    node = create_node.SyntaxFreeLine(
        comment='', col_offset=0, comment_indent=0)
    string = '#\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('#\n', matcher.GetSource())

  def testCommentMatch(self):
    node = create_node.SyntaxFreeLine(
        comment='comment', col_offset=0, comment_indent=0)
    string = '#comment\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('#comment\n', matcher.GetSource())

  def testIndentedCommentMatch(self):
    node = create_node.SyntaxFreeLine(
        comment='comment', col_offset=0, comment_indent=2)
    string = '#  comment\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('#  comment\n', matcher.GetSource())

  def testOffsetCommentMatch(self):
    node = create_node.SyntaxFreeLine(
        comment='comment', col_offset=2, comment_indent=0)
    string = '  #comment\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual('  #comment\n', matcher.GetSource())

  def testChangeComment(self):
    node = create_node.SyntaxFreeLine(
        comment='comment', col_offset=1, comment_indent=0)
    string = ' #comment\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.col_offset = 0
    node.comment_indent = 1
    node.comment = 'hello'
    self.assertEqual('# hello\n', matcher.GetSource())

  def testNotCommentFails(self):
    node = create_node.SyntaxFreeLine(
        comment='comment', col_offset=1, comment_indent=0)
    string = ' comment\n'
    matcher = source_match.GetMatcher(node)
    with self.assertRaises(source_match.BadlySpecifiedTemplateError):
      matcher.Match(string)


class TryExceptMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.TryExcept(
        [create_node.Expr(create_node.Name('a'))],
        [create_node.ExceptHandler()])
    string = """try:
  a
except:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchMultipleExceptHandlers(self):
    node = create_node.TryExcept(
        [create_node.Expr(create_node.Name('a'))],
        [create_node.ExceptHandler('TestA'),
         create_node.ExceptHandler('TestB')])
    string = """try:
  a
except TestA:
  pass
except TestB:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchExceptAndOrElse(self):
    node = create_node.TryExcept(
        [create_node.Expr(create_node.Name('a'))],
        [create_node.ExceptHandler()],
        orelse=[create_node.Pass()])
    string = """try:
  a
except:
  pass
else:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testMatchWithEmptyLine(self):
    node = create_node.TryExcept(
        [create_node.Expr(create_node.Name('a'))],
        [create_node.ExceptHandler()])
    string = """try:
  a

except:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class TryFinallyMatcherTest(unittest.TestCase):

  def testBasicMatch(self):
    node = create_node.TryFinally(
        [create_node.Expr(create_node.Name('a'))],
        [create_node.Expr(create_node.Name('c'))])
    string = """try:
  a
finally:
  c
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithExcept(self):
    node = create_node.TryFinally(
        [create_node.TryExcept(
            [create_node.Expr(create_node.Name('a'))],
            [create_node.ExceptHandler()])],
        [create_node.Expr(create_node.Name('c'))])
    string = """try:
  a
except:
  pass
finally:
  c
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicMatchWithBlankLines(self):
    node = create_node.TryFinally(
        [create_node.Expr(create_node.Name('a'))],
        [create_node.Expr(create_node.Name('c'))])
    string = """try:

  a

finally:

  c
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class UnaryOpMatcherTest(unittest.TestCase):

  def testUAddUnaryOp(self):
    node = create_node.UnaryOp(
        create_node.UAdd(),
        create_node.Name('a'))
    string = '+a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testUSubUnaryOp(self):
    node = create_node.UnaryOp(
        create_node.USub(),
        create_node.Name('a'))
    string = '-a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testNotUnaryOp(self):
    node = create_node.UnaryOp(
        create_node.Not(),
        create_node.Name('a'))
    string = 'not a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testInvertUnaryOp(self):
    node = create_node.UnaryOp(
        create_node.Invert(),
        create_node.Name('a'))
    string = '~a'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())


class WithMatcherTest(unittest.TestCase):

  def testBasicWith(self):
    node = create_node.With(
        create_node.Name('a'))
    string = 'with a:\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testBasicWithAs(self):
    node = create_node.With(
        create_node.Name('a'), as_part=create_node.Name('b'))
    string = 'with a as b:\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testWithAsTuple(self):
    node = create_node.With(
        create_node.Name('a'),
        as_part=create_node.Tuple(create_node.Name('b'),
                                  create_node.Name('c')))
    string = 'with a as (b, c):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  def testChangeWithAsTuple(self):
    node = create_node.With(
        create_node.Name('a'),
        as_part=create_node.Tuple(create_node.Name('b'),
                                  create_node.Name('c')))
    string = 'with a as (b, c):\n  pass\n'
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    node.context_expr = create_node.Name('d')
    node.optional_vars.elts[0] = create_node.Name('e')
    node.optional_vars.elts[1] = create_node.Name('f')
    self.assertEqual('with d as (e, f):\n  pass\n', matcher.GetSource())

  def testCompoundWith(self):
    node = create_node.With(
        create_node.Name('a'),
        as_part=create_node.Name('c'),
        body=[
            create_node.With(
                create_node.Name('b'),
                as_part=create_node.Name('d')
            )]
    )
    string = """with a as c, b as d:
  pass
"""
    matcher = source_match.GetMatcher(node)
    matcher.Match(string)
    self.assertEqual(string, matcher.GetSource())

  # TODO: Renabled this after adding indent information to matchers
  @unittest.expectedFailure
  def testCompoundWithReplacements(self):
    node = create_node.With(
        create_node.Name('a'),
        as_part=create_node.Name('c'),
        body=[
            create_node.With(
                create_node.Name('b'),
                as_part=create_node.Name('d')
            )]
    )
    module_node = create_node.Module(node)
    string = 'with a as c, b as d:\n  pass\n'
    node.matcher = source_match.GetMatcher(node)
    node.matcher.Match(string)
    node.body[0] = create_node.With(
        create_node.Name('e'),
        as_part=create_node.Name('f')
    )
    self.assertEqual('with a as c, e as f:\n  pass\n',
                     node.matcher.GetSource())


if __name__ == '__main__':
  unittest.main()
