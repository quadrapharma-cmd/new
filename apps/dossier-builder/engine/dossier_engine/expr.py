"""Safe boolean expression language for rule packs.

Grammar (a strict subset of Python syntax, parsed with `ast`, never executed):
  literals: 'text', "text", numbers, true/false/True/False, [list], (tuple)
  names:    profile fields (looked up in a dict; unknown name -> ExprError)
  ops:      and, or, not, ==, !=, <, <=, >, >=, in, not in
Anything else (calls, attributes, subscripts, lambdas, comprehensions…) is
rejected at compile time.
"""
import ast
from functools import lru_cache


class ExprError(ValueError):
    pass


_CMP = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}
_CONST_NAMES = {'true': True, 'false': False, 'True': True, 'False': False, 'none': None, 'None': None}


def _check(node):
    if isinstance(node, ast.Expression):
        return _check(node.body)
    if isinstance(node, ast.BoolOp):
        for v in node.values:
            _check(v)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _check(node.operand)
    if isinstance(node, ast.Compare):
        _check(node.left)
        for op, c in zip(node.ops, node.comparators):
            if type(op) not in _CMP:
                raise ExprError(f'operator not allowed: {type(op).__name__}')
            _check(c)
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
        return
    if isinstance(node, ast.Name):
        return
    if isinstance(node, (ast.List, ast.Tuple)):
        for e in node.elts:
            _check(e)
        return
    raise ExprError(f'syntax not allowed: {type(node).__name__}')


@lru_cache(maxsize=4096)
def compile_expr(src: str):
    if not isinstance(src, str) or not src.strip():
        raise ExprError('empty expression')
    try:
        tree = ast.parse(src.strip(), mode='eval')
    except SyntaxError as e:
        raise ExprError(f'syntax error in {src!r}: {e.msg}') from None
    _check(tree)
    return tree.body


def names(src: str) -> set:
    """Field names an expression reads (for pack linting)."""
    out = set()
    for n in ast.walk(compile_expr(src)):
        if isinstance(n, ast.Name) and n.id not in _CONST_NAMES:
            out.add(n.id)
    return out


def _ev(node, env):
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_ev(v, env) for v in node.values)
        return any(_ev(v, env) for v in node.values)
    if isinstance(node, ast.UnaryOp):
        return not _ev(node.operand, env)
    if isinstance(node, ast.Compare):
        left = _ev(node.left, env)
        for op, c in zip(node.ops, node.comparators):
            right = _ev(c, env)
            try:
                if not _CMP[type(op)](left, right):
                    return False
            except TypeError as e:
                raise ExprError(f'type error: {e}') from None
            left = right
        return True
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in _CONST_NAMES:
            return _CONST_NAMES[node.id]
        if node.id not in env:
            raise ExprError(f'unknown field: {node.id}')
        return env[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_ev(e, env) for e in node.elts]
    raise ExprError(f'syntax not allowed: {type(node).__name__}')  # pragma: no cover


def evaluate(src: str, env: dict) -> bool:
    return bool(_ev(compile_expr(src), env))
