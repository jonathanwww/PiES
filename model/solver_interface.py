import autograd.numpy as np
from model.solvers import solver_wrapper
from PyQt6.QtCore import QObject, pyqtSignal
from model.equationsystem import EquationSystem
from model.result import ResultsManager


class Solver(QObject):
    solve_status = pyqtSignal(str)
    solve_error = pyqtSignal(str)

    def __init__(self, equation_system: EquationSystem, results_manager: ResultsManager):
        super().__init__()
        self.eqsys = equation_system
        self.results_manager = results_manager
        
        # selects the solver from the solver wrapper
        self.method = 0
        
        # for sending fail information
        self.current_block_info = ""
        self.current_grid_info = ""
        
        # for solving
        self.all_variables = set()
        self.py_namespace = {}
        
        self.settings = {'tolerance': 1e-10, 'max_iter': 500, 'verbose': False, 'method': -1}
    
    def status(self, status: str):
        solve_message = f"{status}: Run {self.current_grid_info}, block {self.current_block_info}"
        self.solve_status.emit(solve_message)
        
    def set_solver(self, solver: int):
        self.method = solver
    
    def solve(self):
        try:
            self._solve()
        except Exception as e:
            self.status('Failed')
            self.solve_error.emit(str(e))
            return
        self.status('Finished')
        
    def _solve(self) -> None:
        # create new entry for storing results
        entry_index = self.results_manager.create_entry()
        
        # prepare
        blocks = self.eqsys.blocking()
        grid = self.eqsys.grid.get_grid()  # Assuming grid is an instance of a class that has the get_grid() method
        
        for entry in grid:
            X = {var.name: None for var in self.eqsys.variables.values()}
            X.update(entry)  # add values from grid vars

            for i, block in enumerate(blocks):
                # Update messages
                self.current_block_info = f"{i + 1}/{len(blocks)}"
                self.current_grid_info = f"{grid.index(entry) + 1}/{len(grid)}"
                self.status('Solving')

                # get what we need for solving the block
                block_eqs = [self.eqsys.equations[eq] for eq in self.eqsys.equations if eq in block]
                block_vars = list(set([var for eq in block_eqs for var in eq.variables]))

                unsolved_vars = [var for var in block_vars if X[var] is None and var not in entry.keys()]

                if not unsolved_vars:
                    continue

                x0, lb, ub = self.variable_info(unsolved_vars)
                res_f = self.create_residual_func(block_eqs, unsolved_vars, self.py_namespace, X)

                block_results = solver_wrapper(residual_func=res_f,
                                               initial_guesses=x0,
                                               bounds=(lb, ub),
                                               tol=self.settings['tolerance'],
                                               max_iter=self.settings['max_iter'],
                                               verbose=self.settings['verbose'],
                                               method=self.method)

                X.update(zip(unsolved_vars, block_results))

            # add variables from solving results to the set of all variables which has solutions
            self.all_variables.update(X.keys())
            
            # append the results to entry
            self.results_manager.update_entry(entry_index, X)

    def variable_info(self, query_variables: list[str]) -> tuple:
        x0, lb, ub = [], [], []
        for var_name in query_variables:
            var = self.eqsys.variables[var_name]
            x0.append(var.starting_guess)
            lb.append(var.lower_bound)
            ub.append(var.upper_bound)
        return np.array(x0), np.array(lb), np.array(ub)

    @staticmethod
    def create_residual_func(equations, variables, global_namespace, variable_namespace):
        equation_residuals = [eq.residual_form for eq in equations]
        compiled = [compile(expression, '<string>', 'eval') for expression in equation_residuals]
    
        def res_func(x):
            # Update namespace with x's values of variables
            variable_namespace.update({var: val for var, val in zip(variables, x)})
    
            # Compute residuals
            res = [eval(eq, global_namespace, variable_namespace) for eq in compiled]
            return np.array(res, dtype=float)
    
        return res_func
