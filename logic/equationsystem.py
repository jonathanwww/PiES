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
    unit: str = field(init=False, default='')

    def __add__(self, other):
        if self.unit == other.unit:
            return
        else:
            raise ValueError(f"Incompatible units for addition: {self.name}:{self.unit} and {other.name}:{other.unit}")


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
    namespace: dict = field(init=False, default_factory=dict)  # contains the namespace from the py window
    
    def _sync_variables(self, new_variables: dict[str, Variable]) -> None:
        """
        Synchronizes the variable list with new variables.
        
        - Adds normal variables from new_variables which are not already present in eq sys.
        - Removes current param/loop variables and replaces them with the ones in new variables.
        - Sets used/unused status for all normal variables.
        
        :param new_variables: List of unique variables.
        """
        new_special_vars = {k: v for k, v in new_variables.items()
                            if not isinstance(v, NormalVariable)}
        
        current_normal_vars = {k: v for k, v in self.variables.items()
                               if isinstance(v, NormalVariable)
                               and k not in new_special_vars}  # replace current normal vars with special vars
        
        new_normal_vars = {k: v for k, v in new_variables.items()
                           if isinstance(v, NormalVariable)
                           and k not in current_normal_vars}  # remove normal vars which are already present in current vars
        
        # set used status
        for var_name, var in current_normal_vars.items():  # new_normal_vars already have used set to true
            if var_name in new_variables:
                var.used = True
            else:
                var.used = False
        
        # sort alphabetically
        unsorted_dict = {**current_normal_vars, **new_normal_vars, **new_special_vars}
        sorted_dict = {k: v for k, v in sorted(unsorted_dict.items(), key=lambda item: item[1].name)}

        self.variables = sorted_dict
        
    def _sync_equations(self, new_equations: list[Equation]) -> None:
        self.equations = new_equations

    def remove_unused_variables(self) -> None:
        self.variables = {name: var for name, var in self.variables.items() if var.used}

    def get_variable_info(self, query_variables: list[str]) -> tuple:
        """
        Gets x0, lb, ub for a subset of the variables in the equation system
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
        # set namespace for the eq system to the py window
        self.namespace = {}
        exec(code_window, self.namespace)
        
        # clean/parse input
        str_list = clean_input(equation_window)
        equations, variables = parse_input(str_list, self.namespace)

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
    settings = {'tolerance': 1e-10, 'max_iter': 500, 'verbose': False, 'method': -1}
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
            solved_vars = [var for var in block_vars if X[var] is not None]
            unsolved_vars = [var for var in block_vars if X[var] is None]

            # todo: add a check if num of unsolved == 1
            # block is an eq with a loop/param var
            if not unsolved_vars:
                continue

            # Map the names of the solved variables to their value
            solved_map = {k: v for k, v in X.items() if k in solved_vars}

            x0, lb, ub = eqsys.get_variable_info(unsolved_vars)

            res_f = create_residual_func(equations=block_eqs,
                                         variables=unsolved_vars,
                                         solved_variables=solved_map,
                                         namespace=eqsys.namespace)

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


def create_residual_func(equations: list[Equation], variables: list[str], solved_variables: dict, namespace: dict) -> callable:
    # insert solved values
    x_dict = {**solved_variables}
    
    equation_residuals = [eq.residual for eq in equations]
    compiled = [compile(expression, '<string>', 'eval') for expression in equation_residuals]
    
    def residual_func(x: np.array) -> np.array:
        # Update x_dict with new x values
        x_dict.update(zip(variables, x))
        return np.asarray([eval(eq_str, namespace, x_dict) for eq_str in compiled])

    return residual_func


def parse_input(str_equations: list[str], namespace: dict) -> tuple:
    str_eqs = run_equation_generators(str_equations)

    equations = []
    normal_variables = {}
    special_variables = {}
    
    for eq in str_eqs:
        # Find all potential variables in the equation but remove those which are in namespace from pywindow.
        # such as: functions, or variables which are defined in the pywindow, but used for something in the eq window
        eq_vars = [var for var in find_all_variables(eq)
                   if var not in namespace.keys()]

        # special cases of variables
        if len(eq_vars) == 1:
            # check lhs must contain var.
            lhs, rhs = eq.split('=')
            
            if lhs not in special_variables:
                if 'loop_var' in rhs:
                    # rhs is either a list or a list comprehension. or a variable reference to a list
                    special_variables[lhs] = LoopVariable(name=lhs, loop_values=eval(rhs))
                else:
                    # just requires the values on rhs, non evaled. simply has an expression which requires eval at solve
                    special_variables[lhs] = ParameterVariable(name=lhs, param_value=rhs)

        # create normal variables
        else:
            for var in eq_vars:
                if var not in normal_variables:
                    normal_variables[var] = NormalVariable(name=var)

        # Add equation 
        equations.append(Equation(string=eq, variables=eq_vars))
        
    normal_variables.update(special_variables)  # overrides normal vars with param vars
    
    return equations, normal_variables


def validate_equation_system(eqsys: EquationSystem):
    pass
