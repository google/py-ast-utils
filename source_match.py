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


Module for annotating an AST with .matcher objects. See README.
"""

import _ast
import pprint
import re

import create_node
import node_tree_util


class Error(Exception):
  pass


class BadlySpecifiedTemplateError(Error):
  pass


def GetDefaultQuoteType():
  return '"'


def GetSource(field, text=None, starting_parens=None, assume_no_indent=False):
  """Gets the source corresponding with a given field.

  If the node is not a string or a node with a .matcher function,
  this will get the matcher for the node, attach the matcher, and
  match the text provided. If no text is provided, it will rely on defaults.

  Args:
    field: {str|_ast.AST} The field we want the source from.
    text: {str} The text to match if a matcher doesn't exist.
    starting_parens: {[TextPlaceholder]} The list of parens that the field
        starts with.
    assume_no_indent: {bool} True if we can assume the node isn't indented.
        Used for things like new nodes that aren't yet in a module.

  Returns:
    A string, representing the source code for the node.

  Raises:
    ValueError: When passing in a stmt node that has no string or module_node.
        This is an error because we have no idea how much to indent it.
  """
  if field is None:
    return ''
  if starting_parens is None:
    starting_parens = []
  if isinstance(field, str):
    return field
  if isinstance(field, int):
    return str(field)
  if hasattr(field, 'matcher') and field.matcher:
    return field.matcher.GetSource()
  else:
    field.matcher = GetMatcher(field, starting_parens)
    if text:
      field.matcher.Match(text)
    # TODO: Fix this to work with lambdas
    elif isinstance(field, _ast.stmt) and not assume_no_indent:
      if not hasattr(field, 'module_node'):
        raise ValueError(
            'No text was provided, and we try to get source from node {} which'
            'is a statement, so it must have a .module_node field defined. '
            'To add this automatically, call ast_annotate.AddBasicAnnotations'
            .format(field))
      FixSourceIndentation(field.module_node, field)

    return field.matcher.GetSource()


def FixSourceIndentation(
    module_node, node_to_fix, starting_parens=None):
  if starting_parens is None:
    starting_parens = []
  default_source = node_to_fix.matcher.GetSource()
  node_to_fix.matcher = GetMatcher(node_to_fix, starting_parens)
  starting_indent = '  ' * node_tree_util.GetIndentLevel(
      module_node, node_to_fix)
  node_to_fix.matcher.Match(starting_indent + default_source)


def ValidateStart(full_string, starting_string):
  stripped_full = StripStartParens(full_string)
  stripped_start = StripStartParens(starting_string)
  if not stripped_full.startswith(stripped_start):
    raise BadlySpecifiedTemplateError(
        'String "{}" should have started with string "{}"'
        .format(stripped_full, stripped_start))
  return True


def _GetListDefault(l, index, default):
  if index < len(l):
    return l[index]
  else:
    return default.Copy()


# TODO: Consolidate with StringParser
def MatchPlaceholder(string, node, placeholder):
  """Match a placeholder against a string."""
  matched_text = placeholder.Match(node, string)
  if not matched_text:
    return string
  ValidateStart(string, matched_text)
  if not isinstance(placeholder, TextPlaceholder):
    matched_text = StripStartParens(matched_text)
  before, after = string.split(matched_text, 1)
  if StripStartParens(before):
    raise BadlySpecifiedTemplateError(
        'string "{}" should have started with placeholder "{}"'
        .format(string, placeholder))
  return after


def MatchPlaceholderList(string, node, placeholders, starting_parens=None):
  remaining_string = string
  for placeholder in placeholders:
    if remaining_string == string:
      placeholder.SetStartingParens(starting_parens)
    remaining_string = MatchPlaceholder(
        remaining_string, node, placeholder)
  return remaining_string


def StripStartParens(string):
  remaining_string = string
  while remaining_string.startswith('('):
    matcher = GetStartParenMatcher()
    matched_text = matcher.Match(None, remaining_string)
    remaining_string = remaining_string[len(matched_text):]
  return remaining_string


class StringParser(object):
  """Class encapsulating parsing a string while matching placeholders."""

  def __init__(self, string, elements, starting_parens=None):
    if not starting_parens:
      starting_parens = []
    self.starting_parens = starting_parens
    self.string = string
    self.before_string = None
    self.remaining_string = string
    self.elements = elements
    self.matched_substrings = []
    self.Parse()

  def _ProcessSubstring(self, substring):
    """Process a substring, validating its state and calculating remaining."""
    if not substring:
      return
    stripped_substring = StripStartParens(substring)
    stripped_remaining = StripStartParens(self.remaining_string)
    if not stripped_remaining.startswith(stripped_substring):
      raise BadlySpecifiedTemplateError(
          'string "{}" should be in string "{}"'
          .format(stripped_substring, stripped_remaining))
    self.remaining_string = self.remaining_string.split(
        stripped_substring, 1)[1]

  def _MatchTextPlaceholder(self, element):
    if self.remaining_string == self.string:
      element.SetStartingParens(self.starting_parens)
    matched_text = element.Match(None, self.remaining_string)
    self._ProcessSubstring(matched_text)
    self.matched_substrings.append(matched_text)

  def _MatchNode(self, node):
    starting_parens = []
    if self.remaining_string == self.string:
      starting_parens = self.starting_parens
    node_src = GetSource(node, self.remaining_string, starting_parens)
    self._ProcessSubstring(node_src)
    self.matched_substrings.append(node_src)

  def GetMatchedText(self):
    return ''.join(self.matched_substrings)

  def Parse(self):
    """Parses the string, handling nodes and TextPlaceholders."""
    for element in self.elements:
      if isinstance(element, Placeholder):
        self._MatchTextPlaceholder(element)
      else:
        self._MatchNode(element)


class Placeholder(object):
  """Base class for other placeholder objects."""

  def __init__(self):
    self.starting_parens = []

  def Match(self, node, string):
    raise NotImplementedError

  def GetSource(self, node):
    raise NotImplementedError

  def SetStartingParens(self, starting_parens):
    self.starting_parens = starting_parens


class NodePlaceholder(Placeholder):
  """Placeholder to wrap an AST node."""

  def __init__(self, node):
    super(NodePlaceholder, self).__init__()
    self.node = node

  def Match(self, unused_node, string):
    node_src = GetSource(self.node, string, self.starting_parens)
    ValidateStart(string, node_src)
    return node_src

  def GetSource(self, unused_node):
    return GetSource(self.node)


class TextPlaceholder(Placeholder):
  """Placeholder for text (non-field). For example, 'def (' in FunctionDef."""

  def __init__(self, regex, default=None):
    super(TextPlaceholder, self).__init__()
    self.original_regex = regex
    self.regex = self._TransformRegex(regex)
    if default is None:
      self.default = regex
    else:
      self.default = default
    self.matched_text = None

  def _TransformRegex(self, regex):
    non_whitespace_parts = regex.split(r'\s*')
    regex = r'\s*(\\\s*|#.*\s*)*'.join(non_whitespace_parts)
    non_linebreak_parts = regex.split(r'\n')
    regex = r'( *#.*\n| *;| *\n)'.join(non_linebreak_parts)
    return regex

  def Match(self, unused_node, string, dotall=False):
    """Attempts to match string against self.regex.

    Saves the matched section for use in GetSource.

    Args:
      unused_node: unused.
      string: The string we attempt to match a substring of.
      dotall: Whether to apply re.DOTALL to the match.

    Raises:
      BadlySpecifiedTemplateError: If the regex doesn't match anywhere.

    Returns:
      The substring of string that matches.
    """
    if dotall:
      match_attempt = re.match(self.regex, string, re.DOTALL)
    else:
      match_attempt = re.match(self.regex, string)
    if not match_attempt:
      raise BadlySpecifiedTemplateError(
          'string "{}" does not match regex "{}" (technically, "{}")'
          .format(string, self.original_regex, self.regex))
    self.matched_text = match_attempt.group(0)
    return self.matched_text

  def GetSource(self, unused_node):
    """Returns self.matched_text if it exists, or self.default otherwise."""
    if self.matched_text is None:
      return self.default
    return self.matched_text

  def Copy(self):
    return TextPlaceholder(self.regex, self.default)

  def __repr__(self):
    return 'TextPlaceholder with regex "{}" ("{}") and default "{}"'.format(
        self.original_regex, self.regex, self.default)


class CompositePlaceholder(Placeholder):
  """Node which wraps one or more other nodes."""

  def Match(self, node, string):
    """Makes sure node.(self.field_name) is in string."""
    self.Validate(node)
    parser = StringParser(
        string, self.GetElements(node), starting_parens=self.starting_parens)
    return parser.GetMatchedText()

  def GetSource(self, node):
    return ''.join(
        element.GetSource(node) for element in self.GetElements(node))

  def Validate(self, unused_node):
    return True


class FieldPlaceholder(CompositePlaceholder):
  """Placeholder for a field."""

  def __init__(
      self, field_name, before_placeholder=None):
    super(FieldPlaceholder, self).__init__()
    self.field_name = field_name
    self.before_placeholder = before_placeholder

  def GetElements(self, node):
    field_value = getattr(node, self.field_name)
    if not field_value:
      return []

    elements = []
    if self.before_placeholder:
      elements.append(self.before_placeholder)
    elements.append(NodePlaceholder(field_value))
    return elements

  def Validate(self, node):
    field_value = getattr(node, self.field_name)
    if isinstance(field_value, (list, tuple)):
      raise BadlySpecifiedTemplateError(
          'Field {} of node {} is a list. please use a ListFieldPlaceholder'
          'instead of a FieldPlaceholder'.format(self.field_name, node))

  def __repr__(self):
    return 'FieldPlaceholder for field "{}"'.format(
        self.field_name)


class ListFieldPlaceholder(CompositePlaceholder):
  """Placeholder for a field which is a list of child nodes."""

  def __init__(self, field_name,
               before_placeholder=None, after_placeholder=None,
               prefix_placeholder=None,
               exclude_first_before=False):
    """Initializes a field which is a list of child nodes.

    Args:
      field_name: {str} The name of the field
      before_placeholder: {TextPlaceholder} Text to expect to come before the
        child element.
      after_placeholder: {TextPlaceholder} Text to expect to come after the
        child element.
      prefix_placeholder: {TextPlaceholder} Text to expect to come before
        the list.
      exclude_first_before: {bool} Whether to exclude the last
        before_placholder, used for SeparatorListFieldPlaceholder.
    """
    super(ListFieldPlaceholder, self).__init__()
    self.field_name = field_name
    self.prefix_placeholder = prefix_placeholder
    self.before_placeholder = before_placeholder
    self.after_placeholder = after_placeholder
    self.exclude_first_before = exclude_first_before
    self.matched_before = []
    self.matched_after = []

  def _GetBeforePlaceholder(self, index):
    if index < len(self.matched_before):
      return self.matched_before[index]
    new_placeholder = self.before_placeholder.Copy()
    self.matched_before.append(new_placeholder)
    return new_placeholder

  def _GetAfterPlaceholder(self, index):
    if index < len(self.matched_after):
      return self.matched_after[index]
    new_placeholder = self.after_placeholder.Copy()
    self.matched_after.append(new_placeholder)
    return new_placeholder

  def GetValueAtIndex(self, values, index):
    """Gets the set of node in values at index, including before and after."""
    elements = []
    child_value = values[index]
    if isinstance(child_value, create_node.SyntaxFreeLine):
      return [NodePlaceholder(child_value)]
    if (self.before_placeholder and
        not (self.exclude_first_before and index == 0)):
      before_index = index-1 if self.exclude_first_before else index
      elements.append(self._GetBeforePlaceholder(before_index))
    elements.append(NodePlaceholder(child_value))
    if self.after_placeholder:
      elements.append(self._GetAfterPlaceholder(index))
    return elements

  def GetElements(self, node):
    field_value = getattr(node, self.field_name) or []
    elements = []
    if self.prefix_placeholder and field_value:
      elements.append(self.prefix_placeholder)
    for i in xrange(len(field_value)):
      elements.extend(self.GetValueAtIndex(field_value, i))
    return elements

  def Validate(self, node):
    field_value = getattr(node, self.field_name)
    if field_value and not isinstance(field_value, (list, tuple)):
      raise BadlySpecifiedTemplateError(
          'Field {} of node {} is a not list, so please use a FieldPlaceholder'
          'instead of a ListFieldPlaceholder'.format(self.field_name, node))

  def __repr__(self):
    return ('ListFieldPlaceholder for field "{}" with before placeholder "{}"'
            'and after placeholder "{}"'.format(
                self.field_name, self.before_placeholder,
                self.after_placeholder))


class SeparatedListFieldPlaceholder(ListFieldPlaceholder):

  def __init__(self, field_name, separator_placeholder):
    super(SeparatedListFieldPlaceholder, self).__init__(
        field_name, before_placeholder=separator_placeholder,
        exclude_first_before=True)


class ArgsDefaultsPlaceholder(CompositePlaceholder):
  """Placeholder to handle args and defaults for _ast.argument.

  These fields behave differently than most other fields and therefore
  don't fall into any of the other placeholders. Therefore, we have to define
  a custom placeholder.
  """

  def __init__(self, arg_separator_placeholder, kwarg_separator_placeholder):
    super(ArgsDefaultsPlaceholder, self).__init__()
    self.arg_separator_placeholder = arg_separator_placeholder
    self.kwarg_separator_placeholder = kwarg_separator_placeholder
    self.arg_separators = []
    self.kwarg_separators = []

  def _GetArgSeparator(self, index):
    if index < len(self.arg_separators):
      return self.arg_separators[index]
    new_placeholder = self.arg_separator_placeholder.Copy()
    self.arg_separators.append(new_placeholder)
    return new_placeholder

  def _GetKwargSeparator(self, index):
    if index < len(self.kwarg_separators):
      return self.kwarg_separators[index]
    new_placeholder = self.kwarg_separator_placeholder.Copy()
    self.kwarg_separators.append(new_placeholder)
    return new_placeholder

  def _GetArgsKwargs(self, node):
    kwargs = zip(node.args[len(node.args)-len(node.defaults):], node.defaults)
    args = node.args[:-len(kwargs)] if kwargs else node.args
    return args, kwargs

  def GetElements(self, node):
    """Gets the basic elements of this composite placeholder."""
    args, kwargs = self._GetArgsKwargs(node)
    elements = []
    arg_index = 0
    kwarg_index = 0
    for index, arg in enumerate(args):
      elements.append(NodePlaceholder(arg))
      if index is not len(args)-1 or kwargs:
        elements.append(self._GetArgSeparator(arg_index))
        arg_index += 1
    for index, (key, val) in enumerate(kwargs):
      elements.append(NodePlaceholder(key))
      elements.append(self._GetKwargSeparator(kwarg_index))
      kwarg_index += 1
      elements.append(NodePlaceholder(val))
      if index is not len(kwargs)-1:
        elements.append(self._GetArgSeparator(arg_index))
        arg_index += 1
    return elements

  def __repr__(self):
    return ('ArgsDefaultsPlaceholder separating args with "{}" '
            'and kwargs with "{}"'
            .format(self.arg_separator_placeholder,
                    self.kwarg_separator_placeholder))


class KeysValuesPlaceholder(ArgsDefaultsPlaceholder):

  def _GetArgsKwargs(self, node):
    return [], zip(node.keys, node.values)


class ArgsKeywordsPlaceholder(ArgsDefaultsPlaceholder):

  def __init__(self, arg_separator_placeholder, kwarg_separator_placeholder):
    super(ArgsKeywordsPlaceholder, self).__init__(
        arg_separator_placeholder, kwarg_separator_placeholder)
    self.stararg_separator = TextPlaceholder(r'\s*,?\s*\*', ', *')

  def GetElements(self, node):
    """Gets the basic elements of this composite placeholder."""
    args = node.args or []
    keywords = node.keywords or []
    elements = []
    arg_index = 0
    for index, arg in enumerate(args):
      elements.append(NodePlaceholder(arg))
      if index != len(args)-1 or keywords:
        elements.append(self._GetArgSeparator(arg_index))
        arg_index += 1
    if node.starargs:
      elements.append(self.stararg_separator)
      elements.append(NodePlaceholder(node.starargs))
      if keywords:
        elements.append(self._GetArgSeparator(arg_index))
        arg_index += 1
    for index, arg in enumerate(keywords):
      elements.append(NodePlaceholder(arg))
      if index != len(keywords)-1:
        elements.append(self._GetArgSeparator(arg_index))
        arg_index += 1
    return elements


class OpsComparatorsPlaceholder(ArgsDefaultsPlaceholder):

  def _GetArgsKwargs(self, node):
    return [], zip(node.ops, node.comparators)


class BodyPlaceholder(ListFieldPlaceholder):
  """Placeholder for a "body" field. Handles adding SyntaxFreeLine nodes."""

  def __init__(self, *args, **kwargs):
    self.match_after = kwargs.pop('match_after', False)
    super(BodyPlaceholder, self).__init__(*args, **kwargs)

  def MatchSyntaxFreeLine(self, remaining_string):
    line, remaining_string = remaining_string.split('\n', 1)
    syntax_free_node = create_node.SyntaxFreeLine()
    line += '\n'
    syntax_free_node.SetFromSrcLine(line)
    GetSource(syntax_free_node, text=line)
    return remaining_string, syntax_free_node

  def Match(self, node, string):
    remaining_string = string
    new_node = []
    field_value = getattr(node, self.field_name)
    if not field_value:
      return ''
    if self.prefix_placeholder:
      remaining_string = MatchPlaceholder(
          remaining_string, node, self.prefix_placeholder)
    field_value = getattr(node, self.field_name)
    for index, child in enumerate(field_value):
      while create_node.SyntaxFreeLine.MatchesStart(remaining_string):
        remaining_string, syntax_free_node = self.MatchSyntaxFreeLine(
            remaining_string)
        new_node.append(syntax_free_node)
      new_node.append(child)
      indent_level = ' ' * (len(remaining_string) -
                            len(remaining_string.lstrip()))
      remaining_string = MatchPlaceholderList(
          remaining_string, node, self.GetValueAtIndex(field_value, index))

    while (create_node.SyntaxFreeLine.MatchesStart(remaining_string) and
           (remaining_string.startswith(indent_level) or self.match_after)):
      remaining_string, syntax_free_node = self.MatchSyntaxFreeLine(
          remaining_string)
      new_node.append(syntax_free_node)
    setattr(node, self.field_name, new_node)
    matched_string = string
    if remaining_string:
      matched_string = string[:-len(remaining_string)]
    return matched_string

  def GetElements(self, node):
    field_value = getattr(node, self.field_name)
    elements = []
    if not field_value:
      return elements
    if self.prefix_placeholder:
      elements.append(self.prefix_placeholder)
    for index, unused_child in enumerate(field_value):
      elements.extend(self.GetValueAtIndex(field_value, index))
    return elements


def GetStartParenMatcher():
  return TextPlaceholder(r'\(\s*', '')


def GetEndParenMatcher():
  return TextPlaceholder(r'\s*\)', '')


class SourceMatcher(object):
  """Base class for all SourceMatcher objects.

  These are designed to match the source that corresponds to a given node.
  """

  def __init__(self, node, stripped_parens=None):
    self.node = node
    self.end_paren_matchers = []
    self.paren_wrapped = False
    if not stripped_parens:
      stripped_parens = []
    self.start_paren_matchers = stripped_parens

  def Match(self, string):
    raise NotImplementedError

  def GetSource(self):
    raise NotImplementedError

  def MatchStartParens(self, string):
    """Matches the starting parens in a string."""
    remaining_string = string
    matched_parts = []
    try:
      while True:
        start_paren_matcher = GetStartParenMatcher()
        remaining_string = MatchPlaceholder(
            remaining_string, None, start_paren_matcher)
        self.start_paren_matchers.append(start_paren_matcher)
        matched_parts.append(start_paren_matcher.matched_text)
    except BadlySpecifiedTemplateError:
      pass
    return remaining_string

  def MatchEndParen(self, string):
    """Matches the ending parens in a string."""
    if not self.start_paren_matchers:
      return
    remaining_string = string
    matched_parts = []
    try:
      for unused_i in xrange(len(self.start_paren_matchers)):
        end_paren_matcher = GetEndParenMatcher()
        remaining_string = MatchPlaceholder(
            remaining_string, None, end_paren_matcher)
        self.end_paren_matchers.append(end_paren_matcher)
        matched_parts.append(end_paren_matcher.matched_text)
        self.paren_wrapped = True
    except BadlySpecifiedTemplateError:
      pass

    new_end_matchers = []
    new_start_matchers = []
    min_size = min(len(self.start_paren_matchers), len(self.end_paren_matchers))
    if min_size == 0:
      return
    for end_matcher in self.end_paren_matchers[:min_size]:
      new_start_matchers.append(self.start_paren_matchers.pop())
      new_end_matchers.append(end_matcher)
    self.start_paren_matchers = new_start_matchers[::-1]
    self.end_paren_matchers = new_end_matchers

  def GetStartParenText(self):
    if self.paren_wrapped:
      return ''.join(matcher.GetSource(None)
                     for matcher in self.start_paren_matchers)
    return ''

  def GetEndParenText(self):
    if self.paren_wrapped:
      return ''.join(matcher.GetSource(None)
                     for matcher in self.end_paren_matchers)
    return ''


class DefaultSourceMatcher(SourceMatcher):
  """Class to generate the source for a node."""

  def __init__(self, node, expected_parts, starting_parens=None):
    super(DefaultSourceMatcher, self).__init__(node, starting_parens)
    previous_was_string = False
    # We validate that the expected parts does not contain two strings in
    # a row.
    for part in expected_parts:
      if not isinstance(part, Placeholder):
        raise ValueError('All expected parts must be Placeholder objects')
      if isinstance(part, TextPlaceholder) and not previous_was_string:
        previous_was_string = True
      elif isinstance(part, TextPlaceholder) and previous_was_string:
        raise ValueError('Template cannot expect two strings in a row')
      else:
        previous_was_string = False
    self.expected_parts = expected_parts
    self.matched = False

  def Match(self, string):
    """Matches the string against self.expected_parts.

    Note that this is slightly peculiar in that it first matches fields,
    then goes back to match text before them. This is because currently we
    don't have matchers for every node, so by default, we separate each
    field with a '.*' TextSeparator, which is basically the current behavior
    of ast_annotate. This can change after we no longer have any need for
    '.*' TextSeparators.

    Args:
      string: {str} The string to match.

    Returns:
      The matched text.

    Raises:
      BadlySpecifiedTemplateError: If there is a mismatch between the
        expected_parts and the string.
      ValueError: If there is more than one TextPlaceholder in a rwo
    """
    remaining_string = self.MatchStartParens(string)

    try:
      remaining_string = MatchPlaceholderList(
          remaining_string, self.node, self.expected_parts,
          self.start_paren_matchers)
      self.MatchEndParen(remaining_string)

    except BadlySpecifiedTemplateError as e:
      raise BadlySpecifiedTemplateError(
          'When attempting to match string "{}" with {}, this '
          'error resulted:\n\n{}'
          .format(string, self, e.message))
    matched_string = string
    if remaining_string:
      matched_string = string[:-len(remaining_string)]
    return (self.GetStartParenText() +
            matched_string +
            self.GetEndParenText())

  def GetSource(self):
    source_list = []
    for part in self.expected_parts:
      source_list.append(part.GetSource(self.node))
    source = ''.join(source_list)
    if self.paren_wrapped:
      source = '{}{}{}'.format(
          self.GetStartParenText(),
          source,
          self.GetEndParenText())
    return source

  def __repr__(self):
    return ('DefaultSourceMatcher "{}" for node "{}" expecting to match "{}"'
            .format(super(DefaultSourceMatcher, self).__repr__(),
                    self.node,
                    pprint.pformat(self.expected_parts)))


def GetMatcher(node, starting_parens=None):
  """Gets an initialized matcher for the given node (doesnt call .Match).

  If there is no corresponding matcher in _matchers, this will return a
  default matcher, which starts with a placeholder for the first field, ends
  with a placeholder for the last field, and includes TextPlaceholders
  with '.*' regexes between.

  Args:
    node: The node to get a matcher for.
    starting_parens: The parens the matcher may start with.

  Returns:
    A matcher corresponding to that node, or the default matcher (see above).
  """
  if starting_parens is None:
    starting_parens = []
  parts_or_matcher = _matchers[node.__class__]
  try:
    parts = parts_or_matcher()
    return DefaultSourceMatcher(node, parts, starting_parens)
  except TypeError:
    return parts_or_matcher(node, starting_parens)


# TODO: Add an indent placeholder that respects col_offset
def get_Add_expected_parts():
  return [TextPlaceholder(r'\+', '+')]


def get_alias_expected_parts():
  return [
      FieldPlaceholder('name'),
      FieldPlaceholder(
          'asname',
          before_placeholder=TextPlaceholder(r' *as *', ' as ')),
  ]


def get_And_expected_parts():
  return [TextPlaceholder(r'and')]


def get_arguments_expected_parts():
  return [
      ArgsDefaultsPlaceholder(
          TextPlaceholder(r'\s*,\s*', ', '),
          TextPlaceholder(r'\s*=\s*', '=')),
      FieldPlaceholder(
          'vararg',
          before_placeholder=TextPlaceholder(r'\s*,?\s*\*\s*', ', *')),
      FieldPlaceholder(
          'kwarg',
          before_placeholder=TextPlaceholder(r'\s*,?\s*\*\*\s*', ', **'))
  ]


def get_Assert_expected_parts():
  return [
      TextPlaceholder(r' *assert *', 'assert '),
      FieldPlaceholder('test'),
      FieldPlaceholder(
          'msg', before_placeholder=TextPlaceholder(r', *', ', ')),
      TextPlaceholder(r' *\n', '\n'),
  ]


def get_Assign_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*', ''),
      SeparatedListFieldPlaceholder(
          'targets', TextPlaceholder(r'\s*=\s*', ', ')),
      TextPlaceholder(r'[ \t]*=[ \t]*', ' = '),
      FieldPlaceholder('value'),
      TextPlaceholder(r'\n', '\n')
  ]


def get_Attribute_expected_parts():
  return [
      FieldPlaceholder('value'),
      TextPlaceholder(r'\s*\.\s*', '.'),
      FieldPlaceholder('attr')
  ]


def get_AugAssign_expected_parts():
  return [
      TextPlaceholder(r' *', ''),
      FieldPlaceholder('target'),
      TextPlaceholder(r' *', ' '),
      FieldPlaceholder('op'),
      TextPlaceholder(r'= *', '= '),
      FieldPlaceholder('value'),
      TextPlaceholder(r'\n', '\n')
  ]


# TODO: Handle parens better
def get_BinOp_expected_parts():
  return [
      FieldPlaceholder('left'),
      TextPlaceholder(r'\s*', ' '),
      FieldPlaceholder('op'),
      TextPlaceholder(r'\s*', ' '),
      FieldPlaceholder('right'),
  ]


def get_BitAnd_expected_parts():
  return [TextPlaceholder(r'&', '&')]


def get_BitOr_expected_parts():
  return [
      TextPlaceholder(r'\|', '|'),
  ]


def get_BitXor_expected_parts():
  return [
      TextPlaceholder(r'\^', '^'),
  ]


# TODO: Handle parens better
class BoolOpSourceMatcher(SourceMatcher):
  """Class to generate the source for an _ast.BoolOp node."""

  def __init__(self, node, starting_parens=None):
    super(BoolOpSourceMatcher, self).__init__(node, starting_parens)
    self.separator_placeholder = TextPlaceholder(r'\s*', ' ')
    self.matched_placeholders = []

  def GetSeparatorCopy(self):
    copy = self.separator_placeholder.Copy()
    self.matched_placeholders.append(copy)
    return copy

  def Match(self, string):
    remaining_string = self.MatchStartParens(string)

    elements = [self.node.values[0]]
    for value in self.node.values[1:]:
      elements.append(self.GetSeparatorCopy())
      elements.append(self.node.op)
      elements.append(self.GetSeparatorCopy())
      elements.append(value)

    parser = StringParser(remaining_string, elements, self.start_paren_matchers)
    matched_text = ''.join(parser.matched_substrings)
    remaining_string = parser.remaining_string

    self.MatchEndParen(remaining_string)

    return self.GetStartParenText() + matched_text + self.GetEndParenText()

  def GetSource(self):
    source_list = []
    if self.paren_wrapped:
      source_list.append(self.GetStartParenText())
    source_list.append(GetSource(self.node.values[0]))
    index = 0
    for value in self.node.values[1:]:
      source_list.append(_GetListDefault(
          self.matched_placeholders,
          index,
          self.separator_placeholder).GetSource(None))
      source_list.append(GetSource(self.node.op))
      index += 1
      source_list.append(_GetListDefault(
          self.matched_placeholders,
          index,
          self.separator_placeholder).GetSource(None))
      source_list.append(GetSource(value))
      index += 1
    if self.paren_wrapped:
      source_list.append(self.GetEndParenText())
    return ''.join(source_list)


def get_Break_expected_parts():
  return [TextPlaceholder(r' *break *\n', 'break\n')]


def get_Call_expected_parts():
  return [
      FieldPlaceholder('func'),
      TextPlaceholder(r'\(\s*', '('),
      ArgsKeywordsPlaceholder(
          TextPlaceholder(r'\s*,\s*', ', '),
          TextPlaceholder('')),
      FieldPlaceholder(
          'kwargs',
          before_placeholder=TextPlaceholder(r'\s*,?\s*\*\*', ', **')),
      TextPlaceholder(r'\s*,?\s*\)', ')'),
  ]


def get_ClassDef_expected_parts():
  return [
      ListFieldPlaceholder(
          'decorator_list',
          before_placeholder=TextPlaceholder('[ \t]*@', '@'),
          after_placeholder=TextPlaceholder(r'\n', '\n')),
      TextPlaceholder(r'[ \t]*class[ \t]*', 'class '),
      FieldPlaceholder('name'),
      TextPlaceholder(r'\(?\s*', '('),
      SeparatedListFieldPlaceholder(
          'bases', TextPlaceholder(r'\s*,\s*', ', ')),
      TextPlaceholder(r'\s*,?\s*\)?:\n', '):\n'),
      BodyPlaceholder('body')
  ]


def get_Compare_expected_parts():
  return [
      FieldPlaceholder('left'),
      TextPlaceholder(r'\s*', ' '),
      OpsComparatorsPlaceholder(
          TextPlaceholder(r'\s*', ' '),
          TextPlaceholder(r'\s*', ' '))
  ]


def get_comprehension_expected_parts():
  return [
      TextPlaceholder(r'\s*for\s*', 'for '),
      FieldPlaceholder('target'),
      TextPlaceholder(r'\s*in\s*', ' in '),
      FieldPlaceholder('iter'),
      ListFieldPlaceholder(
          'ifs',
          before_placeholder=TextPlaceholder(r'\s*if\s*', ' if '))
  ]


def get_Continue_expected_parts():
  return [TextPlaceholder(r' *continue\n')]


def get_Delete_expected_parts():
  return [
      TextPlaceholder(r' *del *'),
      ListFieldPlaceholder('targets'),
      TextPlaceholder(r'\n', '\n'),
  ]


def get_Dict_expected_parts():
  return [
      TextPlaceholder(r'\s*{\s*', '{'),
      KeysValuesPlaceholder(
          TextPlaceholder(r'\s*,\s*', ', '),
          TextPlaceholder(r'\s*:\s*', ': ')),
      TextPlaceholder(r'\s*,?\s*}', '}')
  ]


def get_Div_expected_parts():
  return [
      TextPlaceholder(r'/', '/'),
  ]


# TODO: Handle both types of k/v syntax
def get_DictComp_expected_parts():
  return [
      TextPlaceholder(r'\{\s*', '{'),
      FieldPlaceholder('key'),
      TextPlaceholder(r'\s*:\s*', ': '),
      FieldPlaceholder('value'),
      TextPlaceholder(r' *', ' '),
      ListFieldPlaceholder('generators'),
      TextPlaceholder(r'\s*\}', '}'),
  ]


def get_Eq_expected_parts():
  return [TextPlaceholder(r'==', '==')]


def get_ExceptHandler_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*except:?[ \t]*', 'except '),
      FieldPlaceholder('type'),
      FieldPlaceholder(
          'name',
          before_placeholder=TextPlaceholder(r' *as *| *, *', ' as ')),
      TextPlaceholder(r'[ \t]*:?[ \t]*\n', ':\n'),
      BodyPlaceholder('body')
  ]


def get_Expr_expected_parts():
  return [
      TextPlaceholder(r' *', ''),
      FieldPlaceholder('value'),
      TextPlaceholder(r' *\n', '\n')
  ]


def get_FloorDiv_expected_parts():
  return [
      TextPlaceholder(r'//', '//'),
  ]


def get_For_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*for[ \t]*', 'for '),
      FieldPlaceholder('target'),
      TextPlaceholder(r'[ \t]*in[ \t]*', ' in '),
      FieldPlaceholder('iter'),
      TextPlaceholder(r':\n', ':\n'),
      BodyPlaceholder('body'),
      BodyPlaceholder(
          'orelse',
          prefix_placeholder=TextPlaceholder(r' *else:\n', 'else:\n')),
  ]


def get_FunctionDef_expected_parts():
  return [
      BodyPlaceholder(
          'decorator_list',
          before_placeholder=TextPlaceholder('[ \t]*@', '@'),
          after_placeholder=TextPlaceholder(r'\n', '\n')),
      TextPlaceholder(r'[ \t]*def ', 'def '),
      FieldPlaceholder('name'),
      TextPlaceholder(r'\(\s*', '('),
      FieldPlaceholder('args'),
      TextPlaceholder(r'\s*,?\s*\):\n?', '):\n'),
      BodyPlaceholder('body')
  ]


def get_GeneratorExp_expected_parts():
  return [
      FieldPlaceholder('elt'),
      TextPlaceholder(r'\s*', ' '),
      ListFieldPlaceholder('generators'),
  ]


def get_Global_expected_parts():
  return [
      TextPlaceholder(r' *global *', 'global '),
      SeparatedListFieldPlaceholder(
          r'names',
          TextPlaceholder(r'\s*,\s*', ', ')),
      TextPlaceholder(r' *\n', '\n')
  ]


def get_Gt_expected_parts():
  return [TextPlaceholder(r'>', '>')]


def get_GtE_expected_parts():
  return [TextPlaceholder(r'>=', '>=')]


class IfSourceMatcher(SourceMatcher):
  """Class to generate the source for an _ast.If node."""

  def __init__(self, node, starting_parens=None):
    super(IfSourceMatcher, self).__init__(node, starting_parens)
    self.if_placeholder = TextPlaceholder(r' *if\s*', 'if ')
    self.test_placeholder = FieldPlaceholder('test')
    self.if_colon_placeholder = TextPlaceholder(r':\n?', ':\n')
    self.body_placeholder = BodyPlaceholder('body')
    self.else_placeholder = TextPlaceholder(r' *else:\n', 'else:\n')
    self.orelse_placeholder = BodyPlaceholder('orelse')
    self.is_elif = False
    self.if_indent = 0

  def Match(self, string):
    self.if_indent = len(string) - len(string.lstrip())
    placeholder_list = [self.if_placeholder,
                        self.test_placeholder,
                        self.if_colon_placeholder,
                        self.body_placeholder]
    remaining_string = MatchPlaceholderList(
        string, self.node, placeholder_list)
    if not self.node.orelse:
      return string[:len(remaining_string)]
    else:
      # Handles the case of a blank line before an elif/else statement
      # Can't pass the "match_after" kwarg to self.body_placeholder,
      # because we don't want to match after if we don't have an else.
      while create_node.SyntaxFreeLine.MatchesStart(remaining_string):
        remaining_string, syntax_free_node = (
            self.body_placeholder.MatchSyntaxFreeLine(remaining_string))
        self.node.body.append(syntax_free_node)
      if remaining_string.lstrip().startswith('elif'):
        self.is_elif = True
        indent = len(remaining_string) - len(remaining_string.lstrip())
        remaining_string = (remaining_string[:indent] +
                            remaining_string[indent+2:])
        # This is a hack to handle the fact that elif is a special case
        # BodyPlaceholder uses the indent of the other child statements
        # to match SyntaxFreeLines, which breaks in this case, because the
        # child isn't indented
        self.orelse_placeholder = ListFieldPlaceholder('orelse')
      else:
        remaining_string = MatchPlaceholder(
            remaining_string, self.node, self.else_placeholder)
    remaining_string = self.orelse_placeholder.Match(
        self.node, remaining_string)
    if not remaining_string:
      return string
    return string[:len(remaining_string)]

  def GetSource(self):
    placeholder_list = [self.if_placeholder,
                        self.test_placeholder,
                        self.if_colon_placeholder,
                        self.body_placeholder]
    source_list = [p.GetSource(self.node) for p in placeholder_list]
    if not self.node.orelse:
      return ''.join(source_list)
    if (len(self.node.orelse) == 1 and
        isinstance(self.node.orelse[0], _ast.If) and
        self.is_elif):
      elif_source = GetSource(self.node.orelse[0])
      indent = len(elif_source) - len(elif_source.lstrip())
      source_list.append(elif_source[:indent] + 'el' + elif_source[indent:])
    else:
      if self.else_placeholder:
        source_list.append(self.else_placeholder.GetSource(self.node))
      else:
        source_list.append(' '*self.if_indent)
        source_list.append('else:\n')
      source_list.append(self.orelse_placeholder.GetSource(self.node))
    return ''.join(source_list)


def get_IfExp_expected_parts():
  return [
      FieldPlaceholder('body'),
      TextPlaceholder(r'\s*if\s*', ' if '),
      FieldPlaceholder('test'),
      TextPlaceholder(r'\s*else\s*', ' else '),
      FieldPlaceholder('orelse'),
  ]


def get_Import_expected_parts():
  return [
      TextPlaceholder(r' *import ', 'import '),
      SeparatedListFieldPlaceholder(
          'names', TextPlaceholder('[ \t]*,[ \t]', ', ')),
      TextPlaceholder(r'\n', '\n')
  ]


def get_ImportFrom_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*from ', 'from '),
      FieldPlaceholder('module'),
      TextPlaceholder(r' import '),
      SeparatedListFieldPlaceholder(
          'names', TextPlaceholder('[ \t]*,[ \t]', ', ')),
      TextPlaceholder(r'\n', '\n')
  ]


def get_In_expected_parts():
  return [TextPlaceholder(r'in', 'in')]


def get_Index_expected_parts():
  return [FieldPlaceholder(r'value')]


def get_Invert_expected_parts():
  return [TextPlaceholder(r'~', '~')]


def get_Is_expected_parts():
  return [TextPlaceholder(r'is', 'is')]


def get_IsNot_expected_parts():
  return [TextPlaceholder(r'is *not', 'is not')]


def get_keyword_expected_parts():
  return [
      FieldPlaceholder('arg'),
      TextPlaceholder(r'\s*=\s*', '='),
      FieldPlaceholder('value'),
  ]


def get_Lambda_expected_parts():
  return [
      TextPlaceholder(r'lambda\s*', 'lambda '),
      FieldPlaceholder('args'),
      TextPlaceholder(r'\s*:\s*', ': '),
      FieldPlaceholder('body'),
  ]


def get_List_expected_parts():
  return [
      TextPlaceholder(r'\[\s*', '['),
      SeparatedListFieldPlaceholder(
          'elts', TextPlaceholder(r'\s*,\s*', ', ')),
      TextPlaceholder(r'\s*,?\s*\]', ']')]


def get_ListComp_expected_parts():
  return [
      TextPlaceholder(r'\[\s*', '['),
      FieldPlaceholder('elt'),
      TextPlaceholder(r' *', ' '),
      ListFieldPlaceholder('generators'),
      TextPlaceholder(r'\s*\]', ']'),
  ]


def get_LShift_expected_parts():
  return [
      TextPlaceholder(r'<<', '<<'),
  ]


def get_Lt_expected_parts():
  return [TextPlaceholder(r'<', '<')]


def get_LtE_expected_parts():
  return [TextPlaceholder(r'<=', '<=')]


def get_Mod_expected_parts():
  return [TextPlaceholder(r'%')]


def get_Module_expected_parts():
  return [BodyPlaceholder('body')]


def get_Mult_expected_parts():
  return [TextPlaceholder(r'\*', '*')]


def get_Name_expected_parts():
  return [FieldPlaceholder('id')]


def get_NotEq_expected_parts():
  return [TextPlaceholder(r'!=')]


def get_Not_expected_parts():
  return [TextPlaceholder(r'not', 'not')]


def get_NotIn_expected_parts():
  return [TextPlaceholder(r'not *in', 'not in')]


class NumSourceMatcher(SourceMatcher):
  """Class to generate the source for an _ast.Num node."""

  def __init__(self, node, starting_parens=None):
    super(NumSourceMatcher, self).__init__(node, starting_parens)
    self.matched_num = None
    self.matched_as_str = None
    self.suffix = None

  def Match(self, string):
    node_as_str = str(self.node.n)
    if isinstance(self.node.n, int):
      # Handle hex values
      node_as_str = re.match(r'[+-]?(0x[0-9a-f]*|0[0-7]*|\d+)', string).group(0)
    elif isinstance(self.node.n, float):
      node_as_str = re.match(r'[-+]?\d*.\d*', string).group(0)
    self.matched_num = self.node.n
    self.matched_as_str = node_as_str

    unused_before, after = string.split(node_as_str, 1)
    if after and after[0] in ('l', 'L', 'j', 'J'):
      self.suffix = after[0]
      node_as_str += after[0]
    return node_as_str

  def GetSource(self):
    node_as_str = str(self.node.n)
    if self.matched_num is not None and self.matched_num == self.node.n:
      node_as_str = self.matched_as_str
    if self.suffix:
      node_as_str += self.suffix
    return node_as_str


def get_Or_expected_parts():
  return [TextPlaceholder(r'or')]


def get_Pass_expected_parts():
  return [TextPlaceholder(r'[ \t]*pass\n', 'pass\n')]


def get_Pow_expected_parts():
  return [
      TextPlaceholder(r'\*\*', '**'),
  ]


# TODO: Support non-nl syntax
def get_Print_expected_parts():
  return [
      TextPlaceholder(r' *print *', 'print '),
      FieldPlaceholder(
          'dest',
          before_placeholder=TextPlaceholder(r'>>', '>>')),
      ListFieldPlaceholder(
          r'values',
          TextPlaceholder(r'\s*,?\s*', ', ')),
      TextPlaceholder(r' *,? *\n', '\n')
  ]


def get_Raise_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*raise[ \t]*', 'raise '),
      FieldPlaceholder('type'),
      TextPlaceholder(r'\n', '\n'),
  ]


def get_Return_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*return[ \t]*', 'return '),
      FieldPlaceholder('value'),
      TextPlaceholder(r'\n', '\n'),
  ]


def get_RShift_expected_parts():
  return [
      TextPlaceholder(r'>>', '>>'),
  ]


def get_Set_expected_parts():
  return [
      TextPlaceholder(r'\{\s*', '{'),
      SeparatedListFieldPlaceholder(
          'elts', TextPlaceholder(r'\s*,\s*', ', ')),
      TextPlaceholder(r'\s*\}', '}'),
  ]


def get_SetComp_expected_parts():
  return [
      TextPlaceholder(r'\{\s*', '{'),
      FieldPlaceholder('elt'),
      TextPlaceholder(r' *', ' '),
      ListFieldPlaceholder('generators'),
      TextPlaceholder(r'\s*\}', '}'),
  ]


def get_Slice_expected_parts():
  return [
      FieldPlaceholder('lower'),
      TextPlaceholder(r'\s*:?\s*', ':'),
      FieldPlaceholder('upper'),
      TextPlaceholder(r'\s*:?\s*', ':'),
      FieldPlaceholder('step'),
  ]


def _IsBackslashEscapedQuote(string, quote_index):
  """Checks if the quote at the given index is backslash escaped."""
  num_preceding_backslashes = 0
  for char in reversed(string[:quote_index]):
    if char == '\\':
      num_preceding_backslashes += 1
    else:
      break
  return num_preceding_backslashes % 2 == 1


def _FindQuoteEnd(string, quote_type):
  """Recursively finds the ending index of a quote.

  Args:
    string: The string to search inside of.
    quote_type: The quote type we're looking for.

  Returns:
    The index of the end of the first quote.

  The method works by attempting to find the first instance of the end of
  the quote, then recursing if it isn't valid. If -1 is returned at any time,
  we can't find the end, and we return -1.
  """
  trial_index = string.find(quote_type)
  if trial_index == -1:
    return -1
  elif not _IsBackslashEscapedQuote(string, trial_index):
    return trial_index
  else:
    new_start = trial_index + 1
    rest_index = _FindQuoteEnd(string[new_start:], quote_type)
    if rest_index == -1:
      return -1
    else:  # Return the recursive sum
      return new_start + rest_index


class StringPartPlaceholder(Placeholder):
  """A container object for a single string part.

  Because of implicit concatination, a single _ast.Str node might have
  multiple parts.
  """

  def __init__(self):
    super(StringPartPlaceholder, self).__init__()
    self.prefix_placeholder = TextPlaceholder(r'ur|uR|Ur|UR|u|r|U|R|', '')
    self.quote_match_placeholder = TextPlaceholder(r'"""|\'\'\'|"|\'')
    self.inner_text_placeholder = TextPlaceholder(r'.*', '')

  def Match(self, node, string):
    elements = [self.prefix_placeholder, self.quote_match_placeholder]
    remaining_string = StringParser(string, elements).remaining_string

    quote_type = self.quote_match_placeholder.matched_text
    end_index = _FindQuoteEnd(remaining_string, quote_type)
    if end_index == -1:
      raise ValueError('String {} does not end properly'.format(string))
    self.inner_text_placeholder.Match(
        None, remaining_string[:end_index], dotall=True)
    remaining_string = remaining_string[end_index+len(quote_type):]
    if not remaining_string:
      return string
    return string[:-len(remaining_string)]

  def GetSource(self, node):
    placeholder_list = [self.prefix_placeholder,
                        self.quote_match_placeholder,
                        self.inner_text_placeholder,
                        self.quote_match_placeholder]
    source_list = [p.GetSource(node) for p in placeholder_list]
    return ''.join(source_list)


class StrSourceMatcher(SourceMatcher):
  """Class to generate the source for an _ast.Str node."""

  def __init__(self, node, starting_parens=None):
    super(StrSourceMatcher, self).__init__(node, starting_parens)
    self.separator_placeholder = TextPlaceholder(r'\s*', '')
    self.quote_parts = []
    self.separators = []
    # If set, will apply to all parts of the string.
    self.quote_type = None
    self.original_quote_type = None
    self.original_s = None

  def _GetMatchedInnerText(self):
    return ''.join(p.inner_text_placeholder.GetSource(self.node)
                   for p in self.quote_parts)

  def Match(self, string):
    remaining_string = self.MatchStartParens(string)
    self.original_s = self.node.s

    part = StringPartPlaceholder()
    remaining_string = MatchPlaceholder(remaining_string, None, part)
    self.quote_parts.append(part)

    while True:
      separator = self.separator_placeholder.Copy()
      trial_string = MatchPlaceholder(remaining_string, None, separator)
      if (not re.match(r'ur"|uR"|Ur"|UR"|u"|U"|r"|R"|"', trial_string) and
          not re.match(r"ur'|uR'|Ur'|UR'|u'|U'|r'|R'|'", trial_string)):
        break
      remaining_string = trial_string
      self.separators.append(separator)
      part = StringPartPlaceholder()
      remaining_string = MatchPlaceholder(remaining_string, None, part)
      self.quote_parts.append(part)

    self.MatchEndParen(remaining_string)

    self.original_quote_type = (
        self.quote_parts[0].quote_match_placeholder.matched_text)

    return (self.GetStartParenText() +
            string[:-len(remaining_string)] +
            self.GetEndParenText())

  def GetSource(self):
    # We try to preserve the formatting on a best-effort basis
    if self.original_s is not None and self.original_s != self.node.s:
      self.quote_parts = [self.quote_parts[0]]
      self.quote_parts[0].inner_text_placeholder.matched_text = self.node.s

    if self.original_s is None:
      if not self.quote_type:
        self.quote_type = self.original_quote_type or GetDefaultQuoteType()
      return self.quote_type + self.node.s + self.quote_type

    if self.quote_type:
      for part in self.quote_parts:
        part.quote_match_placeholder.matched_text = self.quote_type

    source_list = [self.GetStartParenText()]
    source_list.append(_GetListDefault(
        self.quote_parts, 0, None).GetSource(None))
    for index in xrange(len(self.quote_parts[1:])):
      source_list.append(_GetListDefault(
          self.separators, index,
          self.separator_placeholder).GetSource(None))
      source_list.append(_GetListDefault(
          self.quote_parts, index+1, None).GetSource(None))

    source_list.append(self.GetEndParenText())
    return ''.join(source_list)


def get_Sub_expected_parts():
  return [
      TextPlaceholder(r'\-', '-'),
  ]


def get_Subscript_expected_parts():
  return [
      FieldPlaceholder('value'),
      TextPlaceholder(r'\s*\[\s*', '['),
      FieldPlaceholder('slice'),
      TextPlaceholder(r'\s*\]', ']'),
  ]


def get_SyntaxFreeLine_expected_parts():
  return [FieldPlaceholder('full_line'),
          TextPlaceholder(r'\n', '\n')]


class TupleSourceMatcher(DefaultSourceMatcher):
  """Source matcher for _ast.Tuple nodes."""

  def __init__(self, node, starting_parens=None):
    expected_parts = [
        TextPlaceholder(r'\s*', '('),
        SeparatedListFieldPlaceholder(
            'elts', TextPlaceholder(r'\s*,\s*', ', ')),
        TextPlaceholder(r'\s*,?\s*', ')')
    ]
    super(TupleSourceMatcher, self).__init__(
        node, expected_parts, starting_parens)

  def Match(self, string):
    matched_text = super(TupleSourceMatcher, self).Match(string)
    if not self.paren_wrapped:
      matched_text = matched_text.rstrip()
      return super(TupleSourceMatcher, self).Match(matched_text)


def get_TryExcept_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*try:[ \t]*\n', 'try:\n'),
      BodyPlaceholder('body', match_after=True),
      ListFieldPlaceholder('handlers'),
      BodyPlaceholder(
          'orelse',
          prefix_placeholder=TextPlaceholder(r'[ \t]*else:\n', 'else:\n'))
  ]


class TryFinallySourceMatcher(DefaultSourceMatcher):
  """Source matcher for _ast.Tuple nodes."""

  def __init__(self, node, starting_parens=None):
    expected_parts = [
        BodyPlaceholder('body', match_after=True),
        TextPlaceholder(r'[ \t]*finally:[ \t]*\n', 'finally:\n'),
        BodyPlaceholder('finalbody'),
    ]
    super(TryFinallySourceMatcher, self).__init__(
        node, expected_parts, starting_parens)
    self.optional_try = TextPlaceholder(r'[ \t]*try:[ \t]*\n', 'try:\n')

  def Match(self, string):
    remaining_string = string
    if not isinstance(self.node.body[0], _ast.TryExcept):
      remaining_string = MatchPlaceholder(
          remaining_string, None, self.optional_try)
    return super(TryFinallySourceMatcher, self).Match(remaining_string)

  def GetSource(self):
    source_start = ''
    if not isinstance(self.node.body[0], _ast.TryExcept):
      source_start = self.optional_try.GetSource(None)
    return source_start + super(TryFinallySourceMatcher, self).GetSource()


def get_UAdd_expected_parts():
  return [
      TextPlaceholder(r'\+', '+'),
  ]


def get_UnaryOp_expected_parts():
  return [
      FieldPlaceholder('op'),
      TextPlaceholder(r' *', ' '),
      FieldPlaceholder('operand'),
  ]


def get_USub_expected_parts():
  return [
      TextPlaceholder(r'-', '-'),
  ]


def get_While_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*while[ \t]*', 'while '),
      FieldPlaceholder('test'),
      TextPlaceholder(r'[ \t]*:[ \t]*\n', ':\n'),
      BodyPlaceholder('body'),
  ]


class WithSourceMatcher(SourceMatcher):
  """Class to generate the source for an _ast.With node."""

  def __init__(self, node, starting_parens=None):
    super(WithSourceMatcher, self).__init__(node, starting_parens)
    self.with_placeholder = TextPlaceholder(r' *(with)? *', 'with ')
    self.context_expr = FieldPlaceholder('context_expr')
    self.optional_vars = FieldPlaceholder(
        'optional_vars',
        before_placeholder=TextPlaceholder(r' *as *', ' as '))
    self.compound_separator = TextPlaceholder(r'\s*,\s*', ', ')
    self.colon_placeholder = TextPlaceholder(r':\n?', ':\n')
    self.body_placeholder = BodyPlaceholder('body')
    self.is_compound_with = False
    self.starting_with = True

  def Match(self, string):
    if string.lstrip().startswith('with'):
      self.starting_with = True
    placeholder_list = [self.with_placeholder,
                        self.context_expr,
                        self.optional_vars]
    remaining_string = MatchPlaceholderList(
        string, self.node, placeholder_list)
    if remaining_string.lstrip().startswith(','):
      self.is_compound_with = True
      placeholder_list = [self.compound_separator,
                          self.body_placeholder]
      remaining_string = MatchPlaceholderList(
          remaining_string, self.node, placeholder_list)
    else:
      placeholder_list = [self.colon_placeholder,
                          self.body_placeholder]
      remaining_string = MatchPlaceholderList(
          remaining_string, self.node, placeholder_list)

    if not remaining_string:
      return string
    return string[:len(remaining_string)]

  def GetSource(self):
    placeholder_list = []
    if self.starting_with:
      placeholder_list.append(self.with_placeholder)
    placeholder_list.append(self.context_expr)
    placeholder_list.append(self.optional_vars)
    if (self.is_compound_with and
        isinstance(self.node.body[0], _ast.With)):
      if not hasattr(self.node.body[0], 'matcher'):
        # Triggers attaching a matcher. We don't act like an stmt,
        # so we can assume no indent.
        GetSource(self.node.body[0], assume_no_indent=True)
      # If we're part of a compound with, we want to make
      # sure the initial "with" of the body isn't included
      self.node.body[0].matcher.starting_with = False
      placeholder_list.append(self.compound_separator)
    else:
      # If we're not a compound with, we expect the colon
      placeholder_list.append(self.colon_placeholder)
    placeholder_list.append(self.body_placeholder)

    source_list = [p.GetSource(self.node) for p in placeholder_list]
    return ''.join(source_list)


def get_Yield_expected_parts():
  return [
      TextPlaceholder(r'[ \t]*yield[ \t]*', 'yield '),
      FieldPlaceholder('value'),
  ]


# A mapping of node_type: expected_parts
_matchers = {
    _ast.Add: get_Add_expected_parts,
    _ast.alias: get_alias_expected_parts,
    _ast.And: get_And_expected_parts,
    _ast.Assert: get_Assert_expected_parts,
    _ast.Assign: get_Assign_expected_parts,
    _ast.Attribute: get_Attribute_expected_parts,
    _ast.AugAssign: get_AugAssign_expected_parts,
    _ast.arguments: get_arguments_expected_parts,
    _ast.BinOp: get_BinOp_expected_parts,
    _ast.BitAnd: get_BitAnd_expected_parts,
    _ast.BitOr: get_BitOr_expected_parts,
    _ast.BitXor: get_BitXor_expected_parts,
    _ast.BoolOp: BoolOpSourceMatcher,
    _ast.Break: get_Break_expected_parts,
    _ast.Call: get_Call_expected_parts,
    _ast.ClassDef: get_ClassDef_expected_parts,
    _ast.Compare: get_Compare_expected_parts,
    _ast.comprehension: get_comprehension_expected_parts,
    _ast.Continue: get_Continue_expected_parts,
    _ast.Delete: get_Delete_expected_parts,
    _ast.Dict: get_Dict_expected_parts,
    _ast.DictComp: get_DictComp_expected_parts,
    _ast.Div: get_Div_expected_parts,
    _ast.Eq: get_Eq_expected_parts,
    _ast.Expr: get_Expr_expected_parts,
    _ast.ExceptHandler: get_ExceptHandler_expected_parts,
    _ast.FloorDiv: get_FloorDiv_expected_parts,
    _ast.For: get_For_expected_parts,
    _ast.FunctionDef: get_FunctionDef_expected_parts,
    _ast.GeneratorExp: get_GeneratorExp_expected_parts,
    _ast.Global: get_Global_expected_parts,
    _ast.Gt: get_Gt_expected_parts,
    _ast.GtE: get_GtE_expected_parts,
    _ast.If: IfSourceMatcher,
    _ast.IfExp: get_IfExp_expected_parts,
    _ast.Import: get_Import_expected_parts,
    _ast.ImportFrom: get_ImportFrom_expected_parts,
    _ast.In: get_In_expected_parts,
    _ast.Index: get_Index_expected_parts,
    _ast.Invert: get_Invert_expected_parts,
    _ast.Is: get_Is_expected_parts,
    _ast.IsNot: get_IsNot_expected_parts,
    _ast.keyword: get_keyword_expected_parts,
    _ast.Lambda: get_Lambda_expected_parts,
    _ast.List: get_List_expected_parts,
    _ast.ListComp: get_ListComp_expected_parts,
    _ast.LShift: get_LShift_expected_parts,
    _ast.Lt: get_Lt_expected_parts,
    _ast.LtE: get_LtE_expected_parts,
    _ast.Mod: get_Mod_expected_parts,
    _ast.Module: get_Module_expected_parts,
    _ast.Mult: get_Mult_expected_parts,
    _ast.Name: get_Name_expected_parts,
    _ast.Not: get_Not_expected_parts,
    _ast.NotIn: get_NotIn_expected_parts,
    _ast.NotEq: get_NotEq_expected_parts,
    _ast.Num: NumSourceMatcher,
    _ast.Or: get_Or_expected_parts,
    _ast.Pass: get_Pass_expected_parts,
    _ast.Pow: get_Pow_expected_parts,
    _ast.Print: get_Print_expected_parts,
    _ast.Raise: get_Raise_expected_parts,
    _ast.Return: get_Return_expected_parts,
    _ast.RShift: get_RShift_expected_parts,
    _ast.Slice: get_Slice_expected_parts,
    _ast.Sub: get_Sub_expected_parts,
    _ast.Set: get_Set_expected_parts,
    _ast.SetComp: get_SetComp_expected_parts,
    _ast.Subscript: get_Subscript_expected_parts,
    _ast.Str: StrSourceMatcher,
    create_node.SyntaxFreeLine: get_SyntaxFreeLine_expected_parts,
    _ast.Tuple: TupleSourceMatcher,
    _ast.TryExcept: get_TryExcept_expected_parts,
    _ast.TryFinally: TryFinallySourceMatcher,
    _ast.UAdd: get_UAdd_expected_parts,
    _ast.UnaryOp: get_UnaryOp_expected_parts,
    _ast.USub: get_USub_expected_parts,
    _ast.While: get_While_expected_parts,
    _ast.With: WithSourceMatcher,
    _ast.Yield: get_Yield_expected_parts,
}
