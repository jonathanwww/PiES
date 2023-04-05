import networkx as nx
import itertools
import time
from dataclasses import dataclass, field
from abc import ABC
import numpy as np
from logic.util import find_all_variables, clean_input, run_equation_generators, create_residual
from logic.solvers import solver_wrapper
from logic.util import loop_var, gen_eqs  # for evaluating


@dataclass
class Variable(ABC):
    name: str
    used: bool = field(init=False, default=True)


@dataclass
class NormalVariable(Variable):
    used: bool = field(init=False, default=True)
    lower_bound: int = -np.inf
    upper_bound: int = np.inf
    starting_guess: int = 1


@dataclass
class ParameterVariable(Variable):
    param_value: str  # could be: a = 5 + func(..)


@dataclass
class LoopVariable(Variable):
    loop_values: list[float or int]


@dataclass
class Equation:
    id: int = field(init=False)
    string: str
    residual: str = field(init=False)
    variables: list[str]  # Contains the variable names

    _id_counter: int = 0

    def __post_init__(self):
        self.id = Equation._get_next_id()
        self.residual = create_residual(self.string)  # todo: fix residual for non normal-variables

    def __repr__(self):
        return self.string

    @classmethod
    def _get_next_id(cls):
        cls._id_counter += 1
        return cls._id_counter


@dataclass
class EquationSystem:
    equations: list[Equation] = field(init=False, default_factory=list)
    variables: dict[str, Variable] = field(init=False, default_factory=dict)  # [var.name:str, Variable]

    def _sync_variables(self, new_variables: list[Variable]) -> None:
        # remove loop / param vars from old list
        self.variables = {name: var for name, var in self.variables.items()
                          if isinstance(var, NormalVariable)}

        # set all normal variables to un-used
        for var in self.variables.values():
            var.used = False

        # add new variables and set used status
        for var in new_variables:
            if isinstance(var, (ParameterVariable, LoopVariable)):
                # add warning for replacing potential normal var? 
                self.variables[var.name] = var

            # add normal variables or set used if already present
            if var.name not in self.variables:
                self.variables[var.name] = var
            else:
                self.variables[var.name].used = True

    def _sync_equations(self, new_equations: list[Equation]) -> None:
        self.equations = new_equations

    def remove_unused_variables(self) -> None:
        self.variables = {name: var for name, var in self.variables.items() if var.used}

    def get_variable_info(self, query_variables: list[str]) -> tuple:
        """
        Gets x0,lb,ub for a subset of the variables in the equation system
        :param query_variables: list of variable names
        :return: x0, lb, ub for those variables
        """
        x0, lb, ub = [], [], []
        for var_name in query_variables:
            var = self.variables.get(var_name)
            if isinstance(var, NormalVariable):
                x0.append(var.starting_guess)
                lb.append(var.lower_bound)
                ub.append(var.upper_bound)
            else:
                raise TypeError(f"'{var_name}' is either not a NormalVariable or does not exist in the equation system")
        return np.array(x0), np.array(lb), np.array(ub)

    def create_loopvar_grid(self) -> list[dict]:
        """
        The cartesian product of all loop vars.
        :return: List of dictionaries. Keys: variable name, Values: variable value for given grid entry
        """
        loop_variables = [var for var in self.variables.values() if isinstance(var, LoopVariable)]
        loopvar_values = [var.loop_values for var in loop_variables]

        cartesian_product = list(itertools.product(*loopvar_values))

        loopvar_grids = [{var.name: value for var, value in zip(loop_variables, values)}
                         for values in cartesian_product]

        return loopvar_grids

    def update_eqsys(self, equation_window: str, code_window: str) -> None:
        # update global namespace with the stuff in the codewindow
        exec(code_window, globals())

        str_list = clean_input(equation_window)
        equations, variables = parse_input(str_list, globals())

        self._sync_variables(variables)
        self._sync_equations(equations)


def blocking(eqsys: EquationSystem) -> list:
    # Get eqs
    eqs = [eq for eq in eqsys.equations]

    # Get nodes
    eq_nodes = [eq.id for eq in eqs]
    var_nodes = list(eqsys.variables.keys())

    # Bipartite graph
    B = nx.Graph()
    B.add_nodes_from(eq_nodes, bipartite=0)
    B.add_nodes_from(var_nodes, bipartite=1)
    B.add_edges_from([(eq.id, var) for eq in eqs for var in eq.variables])

    # Matching; associate one variable with one equation
    matching = nx.algorithms.bipartite.hopcroft_karp_matching(B, top_nodes=eq_nodes)  # todo: contains both ways, remove one

    # Directed graph
    DG = nx.DiGraph()
    DG.add_nodes_from(eq_nodes)

    for eq, var in matching.items():
        shared_equations = [eq.id for eq in eqsys.equations if var in eq.variables]
        for shared_eq in shared_equations:
            DG.add_edge(eq, shared_eq)

    sccs = list(nx.strongly_connected_components(DG))
    sccs.reverse()
    return sccs


def solve(eqsys: EquationSystem) -> dict:
    settings = {'tolerance': 1e-10, 'max_iter': 500, 'verbose': False, 'method': 1}
    results = {}

    grid = eqsys.create_loopvar_grid()
    blocks = blocking(eqsys)

    # loop over the grid values
    for i, grid_entry in enumerate(grid):
        print(f"Grid entry {i + 1} of {len(grid)}: {grid_entry}")

        # Init solutions dict for all vars in eqsys 
        X = {var.name: eval(var.param_value) if isinstance(var, ParameterVariable) else None for var in
             eqsys.variables.values()}

        # insert loop variables with the grid values
        X.update(grid_entry)

        for j, block in enumerate(blocks):
            print(f"Solving block {j + 1} of {len(blocks)}")

            # get eqs in block
            block_eqs = [eq for eq in eqsys.equations if eq.id in block]

            # get variables in the current block
            block_vars = list(set([var for eq in block_eqs for var in eq.variables]))
            solved_vars = [var for var in block_vars if X[var]]
            unsolved_vars = [var for var in block_vars if not X[var]]

            # todo: add a check if num of unsolved == 1
            # block is an eq with a loop/param var
            if not unsolved_vars:
                continue

            # Map the names of the solved variables to their value
            solved_map = {k: v for k, v in X.items() if k in solved_vars}

            x0, lb, ub = eqsys.get_variable_info(unsolved_vars)

            res_f = create_residual_func(equations=block_eqs,
                                         variables=unsolved_vars,
                                         solved_variables=solved_map)

            block_results = solver_wrapper(residual_func=res_f,
                                           initial_guesses=x0,
                                           bounds=(lb, ub),
                                           tol=settings['tolerance'],
                                           max_iter=settings['max_iter'],
                                           verbose=settings['verbose'],
                                           method=settings['method'])

            X.update(zip(unsolved_vars, block_results))

        # add grid values and X values to results
        results[i] = (grid_entry, X)

    return results


def create_residual_func(equations: list[Equation], variables: list[str], solved_variables: dict) -> callable:
    def residual_func(x: list[float]):
        # maps the variables to be solved
        x_dict = dict(zip(variables, x))

        # add the mapping for the solved variables
        x_dict.update(solved_variables)

        return np.array([eval(eq.residual, globals(), x_dict) for eq in equations])

    return residual_func


def parse_input(str_equations: list[str], namespace: dict) -> tuple:
    str_eqs = run_equation_generators(str_equations)

    equations = []
    variables = {}

    for eq in str_eqs:
        eq_vars = [var for var in find_all_variables(eq)
                   if var not in namespace.keys()]

        # Add variables
        # special cases of variables
        if len(eq_vars) == 1:
            lhs, rhs = eq.split('=')

            if lhs not in variables:
                if 'loop_var' in rhs:
                    variables[lhs] = LoopVariable(name=lhs, loop_values=eval(rhs))
                else:
                    variables[lhs] = ParameterVariable(name=lhs, param_value=rhs)

        # create normal variables
        else:
            for var in eq_vars:
                if var not in variables:
                    variables[var] = NormalVariable(name=var)

        # Add equation 
        equations.append(Equation(string=eq, variables=eq_vars))

    return equations, list(variables.values())


def validate_equation_system(eqsys: EquationSystem):
    pass
