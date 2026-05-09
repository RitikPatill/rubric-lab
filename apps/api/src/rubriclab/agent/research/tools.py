import ast
import operator as op

_CANNED: list[tuple[str, str]] = [
    ("tokyo", "Tokyo population: approximately 13.96 million (city), 37.4 million (greater metro area) as of 2024."),
    ("boiling point", "Water boils at 100°C (212°F) at standard atmospheric pressure (1 atm)."),
    ("apple", "Apple Inc. was founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne. Headquarters: Cupertino, CA."),
    ("telephone", "Alexander Graham Bell is credited with inventing the telephone in 1876."),
]


def web_search(query: str) -> str:
    q = query.lower()
    for keyword, result in _CANNED:
        if keyword in q:
            return result
    return f"No results found for: {query}"


_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
}


def calculator(expression: str) -> str:
    expr = expression.replace(",", "").strip()
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval(tree.body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def _eval(node: ast.expr) -> int | float:
    if isinstance(node, ast.Constant):
        return node.value  # type: ignore[return-value]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand)
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for current information. Returns a text summary.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search query"}},
        "required": ["query"],
    },
}

CALCULATOR_TOOL = {
    "name": "calculator",
    "description": "Evaluate a mathematical expression. Supports +, -, *, /, **, %. Use plain numbers (no units).",
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Math expression, e.g. '42 * 17'"}
        },
        "required": ["expression"],
    },
}

TOOLS = [WEB_SEARCH_TOOL, CALCULATOR_TOOL]
