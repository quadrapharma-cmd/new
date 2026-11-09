import pytest
from dossier_engine.expr import evaluate, compile_expr, names, ExprError

ENV = {'origin': 'local', 'licence': 'toll', 'api_options': ['CEP', 'FULL'], 'pharmacopoeial': True,
       'dosage_specifics': ['coated']}


@pytest.mark.parametrize('src,expected', [
    ("origin == 'local'", True),
    ("origin != 'local'", False),
    ("licence in ['toll', 'f_toll']", True),
    ("'CEP' in api_options", True),
    ("'DMF' not in api_options", True),
    ("pharmacopoeial and not 'sterile' in dosage_specifics", True),
    ("origin == 'imported' or licence == 'toll'", True),
    ("true", True), ("false", False),
])
def test_eval(src, expected):
    assert evaluate(src, ENV) is expected


@pytest.mark.parametrize('src', [
    "__import__('os')", "origin.upper()", "api_options[0]", "(lambda: 1)()",
    "[x for x in api_options]", "origin + 'x'", "open('f')", "a if b else c", "",
])
def test_rejects_unsafe(src):
    with pytest.raises(ExprError):
        compile_expr(src)


def test_unknown_field():
    with pytest.raises(ExprError):
        evaluate("nosuch == 1", ENV)


def test_names():
    assert names("'CEP' in api_options and origin == 'local' and true") == {'api_options', 'origin'}
