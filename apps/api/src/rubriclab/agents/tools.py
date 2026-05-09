import ast
from typing import Callable

# ---------------------------------------------------------------------------
# Web search stub — keyword-matched canned results
# ---------------------------------------------------------------------------

_CANNED: list[tuple[str, str]] = [
    ("tokyo", "Tokyo's population is approximately 13.96 million in the city proper and 37.4 million in the Greater Tokyo Area (2023)."),
    ("boiling point", "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at sea level."),
    ("telephone", "Alexander Graham Bell is credited with inventing the telephone in 1876."),
    ("capital", "The capital of France is Paris."),
    ("france", "The capital of France is Paris."),
    ("apple", "Apple Inc. is an American multinational technology company headquartered in Cupertino, California."),
]

_CATCH_ALL = "No specific information found for your query. Please try a more specific search."


def web_search(query: str) -> str:
    q = query.lower()
    for keyword, canned_text in _CANNED:
        if keyword in q:
            return f"[web_search] {canned_text}"
    return f"[web_search] {_CATCH_ALL}"


# ---------------------------------------------------------------------------
# Safe AST-based calculator
# ---------------------------------------------------------------------------

_ALLOWED_BINOP = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.FloorDiv, ast.Mod)
_ALLOWED_UNOP = (ast.USub, ast.UAdd)


class _SafeVisitor(ast.NodeVisitor):
    def visit_BinOp(self, node: ast.BinOp) -> None:
        if not isinstance(node.op, _ALLOWED_BINOP):
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if not isinstance(node.op, _ALLOWED_UNOP):
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    def visit_Num(self, node: ast.Num) -> None:  # type: ignore[override]
        pass  # Python <3.8 compatibility

    def generic_visit(self, node: ast.AST) -> None:
        allowed = (ast.BinOp, ast.UnaryOp, ast.Constant, ast.Num, ast.Expression)
        if not isinstance(node, allowed):
            raise ValueError(f"Unsupported expression node: {type(node).__name__}")
        super().generic_visit(node)


def calculator(expression: str) -> str:
    expr = expression.replace(",", "").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression syntax: {exc}") from exc
    _SafeVisitor().visit(tree)
    result = eval(compile(tree, "<string>", "eval"))  # noqa: S307
    return str(result)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

TOOL_DISPATCH: dict[str, Callable[[dict], str]] = {
    "web_search": lambda inp: web_search(inp["query"]),
    "calculator": lambda inp: calculator(inp["expression"]),
}
