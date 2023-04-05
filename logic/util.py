import re
import numpy as np
import ast


def create_residual(eq_str: str) -> str:
    lhs, rhs = eq_str.split('=')
    return f"{lhs} - ({rhs})"


def clean_input(x: str) -> list[str]:
    str_list = x.split('\n')

    # removes spaces, except inside [..]
    regex = r'\s+(?=[^\[\]]*(?:\[|$))'
    removed_spaces = [re.sub(regex, '', string) for string in str_list]

    # remove empty lines
    cleaned = list(filter(None, removed_spaces))

    # remove comments
    no_comments = list(filter(lambda line: not line.startswith('#'), cleaned))

    return no_comments


# Use the machine epsilon to balance the round-off error
# and the secant error for numerical differentiation
epsilon_root = np.sqrt(np.finfo(float).eps)
def jacobian(x, f):
    xph = x + (epsilon_root * x)
    dx = xph - x
    n = len(x)
    J = np.zeros((n, n))
    for i in range(n):
        x_diff = x.copy()
        x_diff[i] = xph[i]
        J[:, i] = (f(x_diff) - f(x)) / dx[i]
    return J


def find_all_variables(eq: str) -> list[str]:
    lhs, rhs = eq.split('=')

    # loop var case, only one variable which is on lhs    
    if 'loop_var' in rhs:
        string = lhs
    # else look over the whole eq string
    else:
        string = create_residual(eq)

    variables = [i.id for i in ast.walk(ast.parse(string)) if isinstance(i, ast.Name)]

    return list(set(variables))


def run_equation_generators(eq_strings: list[str]):
    """
    Works by calling evaling the eq_gen() function.
    Generated equations are inserted in the place of generators.
    :param eq_strings: a list of equations in string format
    :return: original list of strs (+) generated eqs (-) the eq generators
    """

    # Create a new list to store the final list of equations
    final_eq_strings = []

    for s in eq_strings:
        if "gen_eqs" in s:
            # Generate equations using eval and extend the final list with the generated equations
            final_eq_strings.extend(eval(s))
        else:
            # Append the string to the final list as is, without generating any equations
            final_eq_strings.append(s)

    return final_eq_strings


# Helper functions for the loop_var/gen_eqs functionality
def loop_var(input_arg) -> list[float or int]:
    try:
        # Check if the input is a list comprehension and execute it
        result = eval(str(input_arg))
        if isinstance(result, list):
            return result
    except (SyntaxError, NameError, TypeError):
        pass

    # Else check if it's a list
    if isinstance(input_arg, list):
        return input_arg

    # If the input is neither a list nor a list comprehension, raise a TypeError
    raise TypeError("Input must for loop_var() be a list or a list comprehension")


def gen_eqs(input_arg) -> list[str]:
    try:
        # Check if the input is a list comprehension and execute it
        result = eval(str(input_arg))
        if isinstance(result, list):
            return result
    except (SyntaxError, NameError, TypeError):
        pass

    # If the input is neither a list nor a list comprehension, raise a TypeError
    raise TypeError("Input must for eq_gen() be a list comprehension")
