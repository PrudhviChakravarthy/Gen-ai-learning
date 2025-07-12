from server import mcp
import ast
import operator as op

@mcp.tool()
def calculate(expression: str) -> float:
    """
    Evaluate a mathematical expression and return the result.
    Supports basic operations: +, -, *, /, parentheses, and implicit multiplication (e.g., 3(4) = 12)
    
    Args:
        expression: A string containing a mathematical expression (e.g., "1*3(4)*7")
        
    Returns:
        The result of the calculation as a float
        
    Examples:
        calculate("1*3(4)*7") -> 84
        calculate("(2+3)*4") -> 20
    """
    # First replace implicit multiplication with explicit *
    expr = expression.replace(')(', ')*(')
    for i in range(len(expr)-1):
        if expr[i].isdigit() and expr[i+1] == '(':
            expr = expr[:i+1] + '*' + expr[i+1:]
        elif expr[i] == ')' and expr[i+1].isdigit():
            expr = expr[:i+1] + '*' + expr[i+1:]
    
    # Now safely evaluate the expression
    return eval_expr(expr)

# Supported operators
_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg
}

def eval_expr(expr):
    """
    Safely evaluate a mathematical expression string
    """
    try:
        return _eval(ast.parse(expr, mode='eval').body)
    except (SyntaxError, TypeError, ZeroDivisionError) as e:
        return f"Error: {str(e)}"

def _eval(node):
    if isinstance(node, ast.Num):  # Number
        return node.n
    elif isinstance(node, ast.BinOp):  # Binary operation
        return _operators[type(node.op)](_eval(node.left), _eval(node.right))
    elif isinstance(node, ast.UnaryOp):  # Unary operation
        return _operators[type(node.op)](_eval(node.operand))
    elif isinstance(node, ast.Constant):  # Constant (Python 3.8+)
        return node.value
    else:
        raise TypeError(node)