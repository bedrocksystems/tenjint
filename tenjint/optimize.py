"""Optimize parts of interrupt for production.

This module contains function that will try to optimize interrupt when it is
used in production and has been compiled with -O. In paritcular, the module
will replace all calls to logging.
"""
import importlib
import importlib.abc
import importlib.util
import sys
# Important import! We need tokenize or get_source fails
import tokenize
import ast
import types
import inspect
import logging

DEBUG = False

if DEBUG:
    logger = logging.getLogger()

def debug(msg, level=0):
    """Provides debug output if DEBUG is enabled."""
    if DEBUG:
        if level == 0:
            logger.warning("{}[!!!] {}".format("\t"*level, msg))
        else:
            logger.warning("{}[*] {}".format("\t"*level, msg))

class LogTransformer(ast.NodeTransformer):
    """Removes all calls to logging."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Targets for replacement
        self._target_obj = ["logging", "self._logger", "logger"]

    def _get_name(self, node):
        """Try to get the full name of an access.

        This function will try to return the full name of an access.
        For instance, if the function debug is called of the module
        logging, this function will return "logging.debug".
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return "{}.{}".format(self._get_name(node.value), node.attr)

        return ""

    def visit_ImportFrom(self, node):
        """Filter imports of the logger from the logger module.

        The logger module has a global variable logger that can be imported.
        The purpose of this hook is to filter these imports. In particular,
        the hook will filter all imports of the form "from logger import logger.
        """
        if node.module == "logger" and node.names[0].name == "logger":
            debug("[IMP] Removing import 'from logger import logger'", level=2)
            return None

        return node

    def visit_Assign(self, node):
        """Filter assignments of target objects.

        This function will filter all assignments of a target object to a
        variable. The assigned variable will be added to the target object
        list. For example, the hook will filter assignments of the form
        "log = logging.getLogg()" and add "log" to the target objects of
        the current module.
        """

        name_target = self._get_name(node.targets[0])
        if isinstance(node.value, ast.Call):
            name_source = self._get_name(node.value.func)
        else:
            name_source = self._get_name(node.value)

        name_source_split = name_source.split(".")

        if name_source_split and name_source_split[0] in self._target_obj:
            debug("[ASSIGN] REPLACING '{} = {}' with PASS".format(name_target,
                                                                  name_source),
                                                                  level=2)
            self._target_obj.append(name_target)
            p = ast.Pass()
            p.lineno = node.lineno
            p.col_offset = node.col_offset
            return p

        return node

    def visit_Expr(self, node):
        """Filter calls on target objects.

        This hook will filter calls on target objects. For instance, it will
        filter calls of the form "logging.getLogger()".
        """
        if not isinstance(node.value, ast.Call):
            return node

        name = self._get_name(node.value.func)

        for x in self._target_obj:
            if name.startswith(x):
                debug("[EXPR] REPLACING {} with PASS".format(name), level=2)
                p = ast.Pass()
                p.lineno = node.lineno
                p.col_offset = node.col_offset
                return p

        return node

class CustomLoader(importlib.abc.Loader):
    def __init__(self, fullname, source):
        self.fullname = fullname
        self.source = source

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        debug("EXEC {}".format(module), level=1)
        exec(compile(self.source, module.__name__, mode="exec"), module.__dict__)

        return module

class PathFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if not hasattr(self, "_processing"):
            self._processing = []

        if (fullname in self._processing):
            return

        if ("tenjint" not in fullname):
            return

        debug("Found import {}...".format(fullname))

        self._processing.append(fullname)

        spec = importlib.util.find_spec(fullname)
        with open(spec.origin, "rb") as f:
            src = f.read()

        debug("Module origin: {}".format(spec.origin), level=1)

        if spec.origin.endswith(".so"):
            self._processing.pop()
            return

        tree = ast.parse(src)
        tree = LogTransformer().visit(tree)
        self._processing.pop()
        spec.loader = CustomLoader(fullname, tree)
        return spec

sys.meta_path.insert(0, PathFinder())
