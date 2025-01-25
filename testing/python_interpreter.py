######
# This file is a modified version of the original file from the HuggingFace Inc. team.
######

# !/usr/bin/env python
# coding=utf-8

# Copyright 2023 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import difflib
from collections.abc import Mapping
import sys
import traceback
from typing import Any, Callable, Dict


class InterpretorError(ValueError):
    """
    An error raised when the interpretor cannot evaluate a Python expression, due to syntax error or unsupported
    operations.
    """

    pass


def evaluate(code: str, tools: Dict[str, Callable], state=None, chat_mode=False):
    """
    Evaluate a python expression using the content of the variables stored in a state and only evaluating a given set
    of functions.

    This function will recurse through the nodes of the tree provided.

    Args:
        code (`str`):
            The code to evaluate.
        tools (`Dict[str, Callable]`):
            The functions that may be called during the evaluation. Any call to another function will fail with an
            `InterpretorError`.
        state (`Dict[str, Any]`):
            A dictionary mapping variable names to values. The `state` should contain the initial inputs but will be
            updated by this function to contain all variables as they are evaluated.
        chat_mode (`bool`, *optional*, defaults to `False`):
            Whether or not the function is called from `Agent.chat`.
    """
    try:
        expression = ast.parse(code)
    except SyntaxError as e:
        print("The code generated by the agent is not valid.\n", e)
        return
    if state is None:
        state = {}
    result = None

    code_lines = code.split('\n')  # Split the code into individual lines
    for idx, node in enumerate(expression.body):
        try:
            line_result = evaluate_ast(node, state, tools)
        except InterpretorError as e:
            error_line = node.lineno
            error_content = code_lines[error_line - 1] if error_line <= len(code_lines) else '<unknown>'
            msg = f"Evaluation of the code stopped at line {error_line} before the end because of the following error: {e}"
            msg += f"\nError occurred at line {error_line}: {error_content}"
            msg += f":\n{e}"
            print(msg)
            raise InterpretorError(msg) from None
        except Exception as e:
            error_line = node.lineno
            error_content = code_lines[error_line - 1] if error_line <= len(code_lines) else '<unknown>'
            msg = f"Evaluation of the code stopped at line {error_line} before the end because of the following error: {e}"
            msg += f"\nError occurred at line {error_line}: {error_content}"
            raise Exception(msg) from None
        if line_result is not None:
            result = line_result

    return result, state


def unpack_tuple_listcomp(state, target, value):
    if isinstance(target, ast.Tuple):
        for sub_target, sub_value in zip(target.elts, value):
            unpack_tuple(state, sub_target, sub_value)
    else:
        state[target.id] = value


def evaluate_ast(expression: ast.AST, state: Dict[str, Any], tools: Dict[str, Callable]):
    """
    Evaluate an absract syntax tree using the content of the variables stored in a state and only evaluating a given
    set of functions.

    This function will recurse trough the nodes of the tree provided.

    Args:
        expression (`ast.AST`):
            The code to evaluate, as an abastract syntax tree.
        state (`Dict[str, Any]`):
            A dictionary mapping variable names to values. The `state` is updated if need be when the evaluation
            encounters assignements.
        tools (`Dict[str, Callable]`):
            The functions that may be called during the evaluation. Any call to another function will fail with an
            `InterpretorError`.
    """
    if isinstance(expression, ast.Assign):
        # Assignement -> we evaluate the assignement which should update the state
        # We return the variable assigned as it may be used to determine the final result.
        return evaluate_assign(expression, state, tools)
    elif isinstance(expression, ast.Call):
        # Function call -> we return the value of the function call
        return evaluate_call(expression, state, tools)
    elif isinstance(expression, ast.Constant):
        # Constant -> just return the value
        return expression.value
    elif isinstance(expression, ast.Dict):
        # Dict -> evaluate all keys and values
        keys = [evaluate_ast(k, state, tools) for k in expression.keys]
        values = [evaluate_ast(v, state, tools) for v in expression.values]
        return dict(zip(keys, values))
    elif isinstance(expression, ast.Expr):
        # Expression -> evaluate the content
        return evaluate_ast(expression.value, state, tools)
    elif isinstance(expression, ast.For):
        # For loop -> execute the loop
        return evaluate_for(expression, state, tools)
    elif isinstance(expression, ast.FormattedValue):
        # Formatted value (part of f-string) -> evaluate the content and return
        return evaluate_ast(expression.value, state, tools)
    elif isinstance(expression, ast.If):
        # If -> execute the right branch
        if isinstance(expression.test, ast.Compare) and \
                isinstance(expression.test.left, ast.Name) and expression.test.left.id == "__name__" and \
                isinstance(expression.test.comparators[0], ast.Constant) and expression.test.comparators[
            0].value == "__main__":
            # This is a `if __name__ == "__main__"` block, execute it
            for node in expression.body:
                evaluate_ast(node, state, tools)
        else:
            return evaluate_if(expression, state, tools)
    elif hasattr(ast, "Index") and isinstance(expression, ast.Index):
        return evaluate_ast(expression.value, state, tools)
    elif isinstance(expression, ast.JoinedStr):
        return "".join([str(evaluate_ast(v, state, tools)) for v in expression.values])
    elif isinstance(expression, ast.List):
        # List -> evaluate all elements
        return [evaluate_ast(elt, state, tools) for elt in expression.elts]
    elif isinstance(expression, ast.Name):
        # Name -> pick up the value in the state
        return evaluate_name(expression, state, tools)
    elif isinstance(expression, ast.Subscript):
        # Subscript -> return the value of the indexing
        return evaluate_subscript(expression, state, tools)
    elif isinstance(expression, ast.BinOp):
        return evaluate_binop(expression, state, tools)
    elif isinstance(expression, ast.Tuple):
        return tuple(evaluate_ast(element, state, tools) for element in expression.elts)
    elif isinstance(expression, ast.Import):
        return evaluate_import(expression, state)
    elif isinstance(expression, ast.ImportFrom):
        return evaluate_import_from(expression, state)
    elif isinstance(expression, ast.Attribute):
        # Attribute -> get the value of the attribute
        return evaluate_attribute(expression, state, tools)
    elif isinstance(expression, ast.AugAssign):
        return evaluate_aug_assign(expression, state, tools)
    elif isinstance(expression, ast.IfExp):
        return evaluate_ifexp(expression, state, tools)
    elif isinstance(expression, ast.UnaryOp):
        return evaluate_unaryop(expression, state, tools)
    elif isinstance(expression, ast.ListComp):
        # List comprehension -> evaluate the generator and the element
        generator = expression.generators[0]
        iter_list = evaluate_ast(generator.iter, state, tools)
        results = []
        for value in iter_list:
            if isinstance(generator.target, ast.Tuple):  # Handle tuple unpacking
                for target, val in zip(generator.target.elts, value):
                    state[target.id] = val
            else:
                state[generator.target.id] = value
            results.append(evaluate_ast(expression.elt, state, tools))
        return results
    elif isinstance(expression, ast.FunctionDef):
        # Function definition -> add a new function to the state
        return evaluate_function_def(expression, state, tools)
    elif isinstance(expression, ast.Starred):
        return evaluate_ast(expression.value, state, tools)
    elif isinstance(expression, ast.Compare):
        return evaluate_compare(expression, state, tools)
    elif isinstance(expression, ast.BoolOp):
        return evaluate_boolop(expression, state, tools)
    elif isinstance(expression, ast.Return):
        return evaluate_return(expression, state, tools)
    elif isinstance(expression, ast.Pass):
        return None
    elif isinstance(expression, ast.Raise):
        return evaluate_raise(expression, state, tools)
    elif isinstance(expression, ast.Assert):
        return evaluate_assert(expression, state, tools)
    elif isinstance(expression, ast.Try):
        try:
            # Evaluate each statement in the try block
            for stmt in expression.body:
                evaluate_ast(stmt, state, tools)
        except Exception as e:
            # This is a simplification. In a real scenario, you'd match the exception type
            handled = False
            for handler in expression.handlers:
                # Assuming a generic catch for simplification. Normally, you'd check the exception type here.
                if not handler.type or isinstance(e, handler.type):
                    for stmt in handler.body:
                        evaluate_ast(stmt, state, tools)
                    handled = True
                    break
            if not handled:
                raise  # Re-raise the exception if not handled
        finally:
            # Evaluate the finally block if it exists
            if expression.finalbody:
                for stmt in expression.finalbody:
                    evaluate_ast(stmt, state, tools)
    else:
        # For now we refuse anything else. Let's add things as we need them.
        raise InterpretorError(f"{expression.__class__.__name__} is not supported.")


def evaluate_assert(assert_statement: ast.Assert, state: Dict[str, Any], tools: Dict[str, Callable]):
    condition = evaluate_ast(assert_statement.test, state, tools)
    if not condition:
        if assert_statement.msg is not None:
            msg = evaluate_ast(assert_statement.msg, state, tools)
            raise AssertionError(msg)
        else:
            raise AssertionError("Assertion failed")
    return None


def evaluate_raise(raise_expr: ast.Raise, state: Dict[str, Any], tools: Dict[str, Callable]):
    if raise_expr.exc is not None:
        exception = evaluate_ast(raise_expr.exc, state, tools)
        if isinstance(exception, BaseException):
            raise exception
        else:
            raise InterpretorError(f"{exception}")
    else:
        raise InterpretorError("Raise statement without an exception is not supported.")


def evaluate_return(return_statement: ast.Return, state: Dict[str, Any], tools: Dict[str, Callable]):
    if return_statement.value is not None:
        return evaluate_ast(return_statement.value, state, tools)
    else:
        return None


def evaluate_boolop(boolop, state, tools):
    values = [evaluate_ast(value, state, tools) for value in boolop.values]
    if isinstance(boolop.op, ast.And):
        return all(values)
    elif isinstance(boolop.op, ast.Or):
        return any(values)
    else:
        raise InterpretorError(f"Boolean operator {boolop.op} not supported")


def evaluate_compare(compare, state, tools):
    left = evaluate_ast(compare.left, state, tools)
    results = []
    for op, right in zip(compare.ops, compare.comparators):
        right = evaluate_ast(right, state, tools)
        if isinstance(op, ast.Eq):
            results.append(left == right)
        elif isinstance(op, ast.NotEq):
            results.append(left != right)
        elif isinstance(op, ast.Lt):
            results.append(left < right)
        elif isinstance(op, ast.LtE):
            results.append(left <= right)
        elif isinstance(op, ast.Gt):
            results.append(left > right)
        elif isinstance(op, ast.GtE):
            results.append(left >= right)
        elif isinstance(op, ast.In):
            results.append(left in right)
        elif isinstance(op, ast.NotIn):
            results.append(left not in right)
        elif isinstance(op, ast.Is):
            results.append(left is right)
        elif isinstance(op, ast.IsNot):
            results.append(left is not right)
        else:
            raise InterpretorError(f"Comparison operator {op} not supported")
        left = right
    return all(results)


def evaluate_function_def(function_def, state, tools):
    # Get the function name
    func_name = function_def.name

    # Get the function parameters
    parameters = [arg.arg for arg in function_def.args.args]

    # Get the default values for the parameters
    defaults = [evaluate_ast(default, state, tools) for default in function_def.args.defaults]

    # Get the function body
    body = function_def.body

    # Define the function
    def func(*args, **kwargs):
        # Create a new local state for the function to avoid conflicts with the global state
        local_state = state.copy()

        # Check the number of arguments
        if len(args) + len(kwargs) < len(parameters) - len(defaults) or len(args) > len(parameters):
            raise InterpretorError(f"Invalid number of arguments for function {func_name}.")

        # Update the local state with the arguments
        for param, arg in zip(parameters, args):
            local_state[param] = arg

        # Update the local state with the keyword arguments
        for param, arg in kwargs.items():
            if param not in parameters:
                raise InterpretorError(f"Invalid keyword argument {param} for function {func_name}.")
            local_state[param] = arg

        # Update the local state with the default values
        for param, default in zip(parameters[-len(defaults):], defaults):
            if param not in local_state:
                local_state[param] = default

        # Evaluate the function body
        for node in body:
            result = evaluate_ast(node, local_state, tools)

        # Return the result of the last line
        return result

    # Add the function to the state
    state[func_name] = func
    # add to tools as well to prevent errors when calling the function
    tools[func_name] = func

    return None


def evaluate_import(import_node, state):
    for alias in import_node.names:
        module = __import__(alias.name)
        state[alias.name] = module

    return None


def evaluate_import_from(import_from_node, state):
    module = __import__(import_from_node.module, fromlist=[import_from_node.names[0].name])
    for alias in import_from_node.names:
        state[alias.name] = getattr(module, alias.name)
    return None


def evaluate_unaryop(unaryop, state, tools):
    operand = evaluate_ast(unaryop.operand, state, tools)
    if isinstance(unaryop.op, ast.UAdd):
        return +operand
    elif isinstance(unaryop.op, ast.USub):
        return -operand
    elif isinstance(unaryop.op, ast.Not):
        return not operand
    elif isinstance(unaryop.op, ast.Invert):
        return ~operand
    elif isinstance(unaryop.op, ast.UAdd):
        return +operand
    else:
        raise InterpretorError(f"Unary operator {unaryop.op} not supported")


def evaluate_aug_assign(aug_assign, state, tools):
    target = evaluate_ast(aug_assign.target, state, tools)
    value = evaluate_ast(aug_assign.value, state, tools)

    if isinstance(aug_assign.op, ast.Add):
        state[aug_assign.target.id] = target + value
    elif isinstance(aug_assign.op, ast.Sub):
        state[aug_assign.target.id] = target - value
    elif isinstance(aug_assign.op, ast.Mult):
        state[aug_assign.target.id] = target * value
    elif isinstance(aug_assign.op, ast.Div):
        state[aug_assign.target.id] = target / value
    else:
        raise InterpretorError(f"Augmented assignment {aug_assign.op} not supported")

    return state[aug_assign.target.id]


def evaluate_ifexp(ifexp, state, tools):
    condition = evaluate_ast(ifexp.test, state, tools)
    if condition:
        return evaluate_ast(ifexp.body, state, tools)
    else:
        return evaluate_ast(ifexp.orelse, state, tools)


def evaluate_assign(assign, state, tools):
    result = evaluate_ast(assign.value, state, tools)
    target = assign.targets[0]
    # Unpacking single tuple into multiple variables
    if isinstance(assign.targets[0], ast.Tuple) and isinstance(result, (list, tuple)):
        var_names = [t.id for t in assign.targets[0].elts]
        if len(result) != len(var_names):
            raise InterpretorError(f"Expected {len(var_names)} values but got {len(result)}.")
        for var_name, r in zip(var_names, result):
            state[var_name] = r
    # Single assignment
    elif isinstance(target, ast.Name):
        var_name = target.id
        state[var_name] = result
    # Handle subscript assignment
    elif isinstance(target, ast.Subscript):
        var_name = target.value.id
        index = evaluate_ast(target.slice, state, tools)
        if var_name not in state:
            state[var_name] = {}
        state[var_name][index] = result
    else:
        raise InterpretorError(f"Unsupported target type: {type(target).__name__}")
    return result


def evaluate_attribute(attribute: ast.Attribute, state: Dict[str, Any], tools: Dict[str, Callable]):
    # Get the object and the attribute name
    obj = evaluate_ast(attribute.value, state, tools)
    attr_name = attribute.attr

    # Get the attribute
    attr = getattr(obj, attr_name)

    return attr


def evaluate_call(call, state, tools):
    if isinstance(call.func, ast.Attribute):
        # Get the object and the method name
        obj = evaluate_ast(call.func.value, state, tools)
        method_name = call.func.attr

        # Get the method
        method = getattr(obj, method_name)

    elif isinstance(call.func, ast.Name):
        func_name = call.func.id
        if func_name not in tools:
            raise InterpretorError(
                f"It is not permitted to evaluate other functions than the provided tools (tried to execute {call.func.id})."
            )
        method = tools[func_name]
    else:
        raise InterpretorError(
            f"It is not permitted to evaluate other functions than the provided tools (tried to execute {call.func} of "
            f"type {type(call.func)})."
        )

    # Handle unpacking of arguments
    args = []
    for arg in call.args:
        if isinstance(arg, ast.Starred):
            args.extend(evaluate_ast(arg.value, state, tools))
        else:
            args.append(evaluate_ast(arg, state, tools))

    kwargs = {keyword.arg: evaluate_ast(keyword.value, state, tools) for keyword in call.keywords}
    return method(*args, **kwargs)


def evaluate_subscript(subscript, state, tools):
    if isinstance(subscript.slice, ast.Slice):
        sliced = evaluate_slice(subscript.slice, state, tools)
    else:
        sliced = evaluate_ast(subscript.slice, state, tools)

    value = evaluate_ast(subscript.value, state, tools)

    if isinstance(value, (list, tuple, str)):
        return value[sliced]
    if sliced in value:
        return value[sliced]

    if isinstance(sliced, str) and isinstance(value, Mapping):
        close_matches = difflib.get_close_matches(sliced, list(value.keys()))
        if len(close_matches) > 0:
            return value[close_matches[0]]

    raise InterpretorError(f"Could not index/subscript {value} with '{sliced}'.")


def evaluate_name(name, state, tools):
    if name.id in state:
        return state[name.id]
    close_matches = difflib.get_close_matches(name.id, list(state.keys()))
    if len(close_matches) > 0:
        return state[close_matches[0]]
    raise InterpretorError(f"The variable `{name.id}` is not defined.")


def evaluate_condition(condition, state, tools):
    if hasattr(condition, "ops"):
        if len(condition.ops) > 1:
            raise InterpretorError("Cannot evaluate conditions with multiple operators")

        left = evaluate_ast(condition.left, state, tools)
        comparator = condition.ops[0]
        right = evaluate_ast(condition.comparators[0], state, tools)

        if isinstance(comparator, ast.Eq):
            return left == right
        elif isinstance(comparator, ast.NotEq):
            return left != right
        elif isinstance(comparator, ast.Lt):
            return left < right
        elif isinstance(comparator, ast.LtE):
            return left <= right
        elif isinstance(comparator, ast.Gt):
            return left > right
        elif isinstance(comparator, ast.GtE):
            return left >= right
        elif isinstance(comparator, ast.Is):
            return left is right
        elif isinstance(comparator, ast.IsNot):
            return left is not right
        elif isinstance(comparator, ast.In):
            return left in right
        elif isinstance(comparator, ast.NotIn):
            return left not in right
        else:
            raise InterpretorError(f"Operator not supported: {comparator}")
    elif isinstance(condition, ast.UnaryOp) and isinstance(condition.op, ast.Not):
        # Handle 'not' unary operator
        return not evaluate_ast(condition.operand, state, tools)
    else:
        # Evaluate as a boolean expression
        return bool(evaluate_ast(condition, state, tools))


def evaluate_if(if_statement, state, tools):
    result = None
    if evaluate_condition(if_statement.test, state, tools):
        for line in if_statement.body:
            line_result = evaluate_ast(line, state, tools)
            if line_result is not None:
                result = line_result
    else:
        for line in if_statement.orelse:
            line_result = evaluate_ast(line, state, tools)
            if line_result is not None:
                result = line_result
    return result


def unpack_tuple(target, values, state):
    if len(values) != len(target.elts):
        raise InterpretorError("Mismatch in number of variables to unpack")

    for idx, variable in enumerate(target.elts):
        if isinstance(variable, ast.Tuple):
            unpack_tuple(variable, values[idx], state)
        else:
            state[variable.id] = values[idx]


def evaluate_for(for_loop, state, tools):
    result = None
    iterator = evaluate_ast(for_loop.iter, state, tools)

    if isinstance(for_loop.target, ast.Tuple):  # Handle tuple unpacking
        for values in iterator:
            unpack_tuple(for_loop.target, values, state)

            for expression in for_loop.body:
                line_result = evaluate_ast(expression, state, tools)
                if line_result is not None:
                    result = line_result
    else:
        for counter in iterator:
            state[for_loop.target.id] = counter
            for expression in for_loop.body:
                line_result = evaluate_ast(expression, state, tools)
                if line_result is not None:
                    result = line_result
    return result


def evaluate_binop(binop, state, tools):
    left = evaluate_ast(binop.left, state, tools)
    right = evaluate_ast(binop.right, state, tools)
    if isinstance(binop.op, ast.Add):
        return left + right
    elif isinstance(binop.op, ast.Sub):
        return left - right
    elif isinstance(binop.op, ast.Mult):
        return left * right
    elif isinstance(binop.op, ast.Div):
        return left / right
    elif isinstance(binop.op, ast.FloorDiv):
        return left // right
    elif isinstance(binop.op, ast.Mod):
        return left % right
    elif isinstance(binop.op, ast.Pow):
        return left ** right
    else:
        raise InterpretorError(f"Operator {binop.op} not supported")


def evaluate_slice(slice_op, state, tools):
    lower = evaluate_ast(slice_op.lower, state, tools) if slice_op.lower else None
    upper = evaluate_ast(slice_op.upper, state, tools) if slice_op.upper else None
    step = evaluate_ast(slice_op.step, state, tools) if slice_op.step else None
    return slice(lower, upper, step)