"""Tiny DTD reader: element content models -> ordered child lists and parents.
Enough to place elements in schema order; validation itself is xmllint/lxml."""
import re

_EL = re.compile(r'<!ELEMENT\s+([\w:.-]+)\s+(.*?)>', re.S)
_NAME = re.compile(r'[A-Za-z_][\w:.-]*')
_KW = {'EMPTY', 'ANY', '#PCDATA'}


def read(*texts):
    children, parents = {}, {}
    for text in texts:
        text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
        for name, model in _EL.findall(text):
            kids = [n for n in _NAME.findall(model) if n not in _KW and not n.startswith('%')]
            children[name] = kids
    for p, kids in children.items():
        for k in kids:
            parents.setdefault(k, p)
    return children, parents
