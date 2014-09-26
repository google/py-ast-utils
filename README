A collection of util modules for working with Python abstract syntax trees.

In the current state, the two most useful parts are:
1. source_match.GetSource: Allows for "round tripping" between python
source and an AST, preserving all formatting.

In more detail: given a node in a Python AST and the text it should
match against, attaches .matcher functions to each node in the tree, which
know how to return the source that generated them, with formatting (line
breaks, spaces, comments, docstrings) preserved. In other words, if we call 
this on the _ast.Module node with the text that generated the ast, then call
module_node.matcher.GetSource(), we will get the exact copy of the source
we passed in.

Example:
>>> some_code = open('code.py').read()
>>> import ast
>>> module_node = ast.parse(some_code)
>>> import source_match
>>> source_match.GetSource(module_node, some_code)
>>> assert some_code == module_node.matcher.GetSource()

This preservation persists even after new nodes are added (they get default
formatting) or nodes are removed.

2. create_node.py: This module contains a bunch of functions for creating
nodes with reasonable defaults.

NOTE: This is not an official Google project!
