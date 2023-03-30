import itertools
import re
import time
import ast
from dataclasses import dataclass, field
import numpy as np
from numpy import inf
import logging

from logic.util import blocking, clean_input
from logic.solvers import solver_wrapper


@dataclass
class Variable:
    name: str
    lower_bound: int = -inf
    upper_bound: int = inf
    starting_guess: int = 1
    used: bool = field(init=False, default=True)  # var will only be created if in current eqs
    loop_var: bool = field(init=False, default=False)
    param_var: bool = field(init=False, default=False)

    def __str__(self):
        return self.name


@dataclass
class Equation:
    residual: str
    variables: list[str] = field(init=False)  # list[Variable.name]

    def __init__(self, residual):
        self.residual = residual
        self.variables = list(set([i.id for i in ast.walk(ast.parse(residual)) if
                                   isinstance(i, ast.Name) and i.id not in globals().keys()]))

    def __str__(self):
        return self.residual


@dataclass
class EquationSystem:
    equations: list[Equation] = field(init=False, default_factory=list)
    variables: list[Variable] = field(init=False, default_factory=list)
    loop_variables: dict[str, list] = field(init=False, default_factory=list)

    def _sync_vars(self, new_variables: list[str]) -> None:  
        # set used/unused on current self.variables
        for cur_var in self.variables:
            if any(cur_var.name == new_var for new_var in new_variables):
                cur_var.used = True
            else:
                cur_var.used = False

        # add new variables if not present in self.variables
        for new_var in new_variables:
            if not any(cur_var.name == new_var for cur_var in self.variables):  # create if no variable with same name  
                self.variables = self.variables + [Variable(name=new_var)]
        
        for var in self.variables:
            # set loop vars
            if var.loop_var and var.name not in self.loop_variables:  # Set to false if no longer loop var
                var.loop_var = False
            if var.name in self.loop_variables:  # Set to true if loop var
                var.loop_var = True
            # set param vars
            if any(len(eq.variables) == 1 and eq.variables[0] == var.name for eq in self.equations):
                var.param_var = True
            else:
                var.param_var = False
            
    def _sync_loop_vars(self, new_loop_variables: dict[str, list]) -> None:
        self.loop_variables = dict(new_loop_variables)
    
    def _sync_eqs(self, str_list: list[str]) -> None:
        self.equations = [Equation(new_eq) for new_eq in str_list]

    def update_loop_vars(self, loop_var_vals, loop_var_names):
        # inserts loop var vals into loop var eqs
        for i, name in enumerate(loop_var_names):
            idx = [self.equations.index(eq) for eq in self.equations
                   if len(eq.variables) == 1
                   and name in eq.variables]
            self.equations[idx[0]].residual = f'{name}-{loop_var_vals[i]}'

    def update_eqsys(self, eq_window: str, code: str) -> None:
        # executes the input from the python window in the gui
        exec(code, globals())
        
        # prepare data by findining loop vars and equation generators in python window
        loop_vars = find_loop_vars(eq_window)
        loop_var_eqs = [f'{var}=0' for var in loop_vars]
        eq_gens = find_eq_gens(eq_window)
        eq_list = remove_loop_vars_eq_gens(eq_window).replace(' ', '').split('\n')

        # run eq generators and clean all eqs
        generated_eqs = generate_eqs(eq_gens)
        new_equations = clean_input(eq_list + generated_eqs + loop_var_eqs)
        all_equation_vars = find_all_vars(new_equations) + list(loop_vars.keys())  # + the variables which might only be in the loop vars
        
        # sync with eq sys
        self._sync_eqs(new_equations)  # removes unused eqs
        self._sync_loop_vars(loop_vars)  # removes unused loop vars
        self._sync_vars(all_equation_vars)  # keeps unused vars


def solve(eq_sys: EquationSystem):
    # time stuff
    loop_vars_time = []
    block_time = []
    solver_time = []

    all_eqsys_solutions = []

    # solve for each lists in loop_var_grid. The grid is over the combination of all the loop variable values
    loop_var_names, loop_var_grid = create_loop_grid(eq_sys)

    # get vars and their settings
    x, x_names, lb, ub = get_variable_info(eq_sys)

    # blocking - should we only perform this once? if not then move back inside loop_var loop 
    blocks = blocking(eq_sys)

    for loop_var_vals in loop_var_grid:
        # time start
        start_time = time.perf_counter()

        # updates the value of the loop var with the current iteration values
        eq_sys.update_loop_vars(loop_var_vals, loop_var_names)

        # get loop var index from the sorted var list - through x names
        loop_var_idx = np.where(np.isin(x_names, list(eq_sys.loop_variables.keys())))

        # insert loop var values 
        x[loop_var_idx] = loop_var_vals

        # Time end
        end_time = time.perf_counter()
        loop_vars_time.append((end_time - start_time) * 1000)

        for block in blocks:
            # time start
            start_time = time.perf_counter()

            # find equations and variables in block
            block_eqs = [eq_sys.equations[i] for i in block]
            block_vars = sorted(set([var for eq in block_eqs for var in eq.variables]), key=str)

            # find the index of the block
            var_idx = np.where(np.isin(x_names, block_vars))

            f = make_residual_function(block_eqs, block_vars)

            # time start
            start_time_solve = time.perf_counter()
            solution = solver_wrapper(residual_func=f,
                                      initial_guesses=x[var_idx],
                                      bounds=(lb[var_idx], ub[var_idx]),
                                      tol=1e-10,
                                      max_iter=500,
                                      verbose=False,
                                      method = 0)
            # Time end
            end_time_solve = time.perf_counter()
            solver_time.append((end_time_solve - start_time_solve) * 1000)

            # # time start
            # start_time_solve = time.perf_counter()
            # _solution = solver_wrapper(residual_func=f,
            #                           initial_guesses=x[var_idx],
            #                           bounds=(lb[var_idx], ub[var_idx]),
            #                           tol=1e-10,
            #                           max_iter=500,
            #                           verbose=False,
            #                           method = 1)
            # # Time end
            # end_time_solve = time.perf_counter()
            # scipy_time = (end_time_solve - start_time_solve) * 1000
            # logging.debug("Internal solver took %f ms and SciPy solver took %f ms", solver_time[-1], scipy_time)

            # update x with results for this block, so we can solve next block
            x[var_idx] = solution

            # Time end
            end_time = time.perf_counter()
            block_time.append((end_time - start_time) * 1000)

        all_eqsys_solutions.append((loop_var_vals, list(zip(x_names, x))))

    print(f'Loop var grid num:{len(loop_var_grid)}, num of vars/eqs:{len(eq_sys.equations)}')
    print(f'Total time in outer loop (doing the loop var stuff): {sum(loop_vars_time):.5f} ms')
    print(f'Total time in block loop (not solving): {sum(block_time) - sum(solver_time):.5f} ms')
    print(f'Total time in block loop (solving): {sum(solver_time):.5f} ms')
    return all_eqsys_solutions


def find_loop_vars(code: str) -> dict[str, list]:
    def contains_loopvar(node):
        if isinstance(node, ast.Call) and node.func.id == "loop_var":
            return True
        for child in ast.iter_child_nodes(node):
            if contains_loopvar(child):
                return True
        return False

    loop_vars = [(ast.unparse(i.targets),
                  eval(compile(re.search(r'\[[^]]*]',
                                         ast.unparse(i.value)).group(0),
                               '<string>', 'eval')))
                 for i in ast.walk(ast.parse(code))
                 if isinstance(i, ast.Assign)
                 and contains_loopvar(i.value)]
    
    return dict(loop_vars)


def find_eq_gens(code: str) -> list:
    equation_generators = [i.args[0] for i in ast.walk(ast.parse(code))  # args[0] = the list comprehension = [i for i in ...]
                           if isinstance(i, ast.Call) and i.func.id == 'gen_eqs']
    return equation_generators
    

def find_all_vars(eq_res: list[str]) -> list[str]:
    pot_vars = []
    for string in eq_res:
        pot_vars = pot_vars + [i.id for i in ast.walk(ast.parse(string)) if
                               isinstance(i, ast.Name) and i.id not in globals().keys()]
    return list(set(pot_vars))


def generate_eqs(equation_generators: list) -> list:
    generated_eqs = [eval(compile(ast.Expression(eq_gen), '<string>', 'eval'))
                     for eq_gen in equation_generators]  # evals a list of list-comprehensions
    return list(itertools.chain(*generated_eqs))  # flattens the lists of lists


def remove_loop_vars_eq_gens(code: str) -> str:
    class RemoveGenFunctions(ast.NodeTransformer):
        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                if node.value.func.id == 'gen_eqs':
                    return None
            return node

    class RemoveLoopVariables(ast.NodeTransformer):
        def visit_Assign(self, node):
            if isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'loop_var':
                return None
            return node

    tree = ast.parse(code)
    new_tree = RemoveGenFunctions().visit(tree)
    new_tree_final = RemoveLoopVariables().visit(new_tree)
    return ast.unparse(new_tree_final)
    

def make_residual_function(equations: list[Equation], variables: list[str]):
    def residual_function(x: np.ndarray) -> np.ndarray:
        # solve the block, pass x[var_idx], that is the vars which is present in the block
        res = [eval(eq.residual,  # eval residual
                    globals(),
                    # include globals, equationsystem.py runs the code window from the gui, so it has the names defined there 
                    {var: x[variables.index(var)] for var in eq.variables})
               # add a mapping for the eq variables to x[i]
               for eq in equations]
        return np.asarray(res)
    return residual_function


def create_loop_grid(eq_sys: EquationSystem):
    loop_var_values = list(eq_sys.loop_variables.values())
    loop_var_names = list(eq_sys.loop_variables.keys())
    loop_var_grid = [list(t) for t in itertools.product(*loop_var_values)]
    return loop_var_names, loop_var_grid


def get_variable_info(eq_sys):
    # sort vars alphabetically so order is correct
    sorted_vars = sorted([var for var in eq_sys.variables if var.used], key=lambda x: x.name)

    # create x:array with initial guesses - we update this with solutions
    x0 = np.array([var.starting_guess for var in sorted_vars], dtype=np.float64)
    
    # get other info for x
    x_names = np.array([var.name for var in sorted_vars])
    lb = np.array([var.lower_bound for var in sorted_vars], dtype=np.float64)
    ub = np.array([var.upper_bound for var in sorted_vars], dtype=np.float64)
    
    return x0, x_names, lb, ub
