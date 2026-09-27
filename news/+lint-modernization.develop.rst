Adopted ruff with a ``make lint`` gate and completed the tree-wide lint
burndown: the classic pyflakes/pycodestyle rules, import sorting,
pyupgrade within the Python 3.9 floor, comprehension construction,
blind-except and the bugbear/simplify/misc judgment sets are all selected
with an empty global ignore list, and deliberate exceptions carry scoped
noqa reasons.  The code tree modernized along the way: PEP 604 unions,
PEP 585 builtin generics, f-strings and the mechanical pyupgrade fixes,
with load-bearing import orders preserved.  [gotcha]
