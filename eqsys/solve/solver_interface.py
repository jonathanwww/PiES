import ast
import time
import autograd.numpy as np
from eqsys.solve.solvers import solver_wrapper
from PyQt6.QtCore import QObject, pyqtSignal
from eqsys.equationsystem import EquationSystem
from eqsys.solve.result import ResultsManager


class SolverInterface(QObject):
    solve_status = pyqtSignal(str)
    solve_error = pyqtSignal(str, object)

    def __init__(self, equation_system: EquationSystem, results_manager: ResultsManager):
        super().__init__()
        self.eqsys = equation_system
        self.results_manager = results_manager
        
        # selects the solver from the solver wrapper
        self.method = 1
        
        # for sending fail information
        self.current_block_info = ""
        self.current_grid_info = ""
        
    
        # todo print verbose to output
        self.settings = {'tolerance': 1e-10, 'max_iter': 500, 'verbose': False, 'method': -1}
    
    def status(self, status: str):
        # todo: show time and iteration
        solve_message = f"{status}: Run {self.current_grid_info}, block {self.current_block_info}"
        self.solve_status.emit(solve_message)
        
    # todo: do we need this? we must remember we need to refresh the namespace
    
    def set_solver(self, solver: int):
        self.method = solver

    def create_namespace(self):
        # todo bugged since we should build the whole namespace and then exec, parameters could be added
        new_namespace = {}
        
        for name, parameter in self.eqsys.parameters.items():
            new_namespace[name] = eval(parameter.code, self.eqsys.namespace)
        
        # namespace window overrides parameters currently
        new_namespace.update(self.eqsys.namespace)
        
        if '__builtins__' in new_namespace:
            del new_namespace['__builtins__']

        return new_namespace
    
    def solve(self):
        start_time = time.time()            
        try:
            self._solve()
        except Exception as e:
            # delete empty entries 
            # self.results_manager.entries[entry_name]
            
            self.solve_error.emit(str(e), ['Output'])
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.status('Failed after {:.2f} seconds'.format(elapsed_time))
            return
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        self.status('Finished in {:.2f} seconds'.format(elapsed_time))
        
    def _solve(self) -> None:
        # todo move results stuff out into solve? at least when saving so we are sure we get partial results even if failing
        # create new entry for storing results
        variables = list(self.eqsys.variables.keys())
        entry_name = self.results_manager.create_entry(variables=variables)
        namespace = self.create_namespace()
        # prepare
        blocks = self.eqsys.blocking()
        # grid = self.eqsys.grid.get_grid()  # Assuming grid is an instance of a class that has the get_grid() method
        
        for entry in range(1):
            # solving for these variable
            X = {var.name: None for var in self.eqsys.variables.values()}
            # X.update(entry)  # add values from grid vars

            for i, block in enumerate(blocks):
                # Update messages
                self.current_block_info = f"{i + 1}/{len(blocks)}"
                # self.current_grid_info = f"{grid.index(entry) + 1}/{len(grid)}"
                self.status('Solving')
                
                # get what we need for solving the block
                block_eqs = [self.eqsys.equations[eq] for eq in self.eqsys.equations if eq in block]
                block_vars = list(set([var for eq in block_eqs for var in eq.objects if var in self.eqsys.variables]))

                unsolved_vars = [var for var in block_vars if X[var] is None]

                if not unsolved_vars:
                    continue

                x0, lb, ub = self.variable_info(unsolved_vars)
                res_f = self.create_residual_func(block_eqs, unsolved_vars, namespace, X)

                block_results = solver_wrapper(residual_func=res_f,
                                               initial_guesses=x0,
                                               bounds=(lb, ub),
                                               tol=self.settings['tolerance'],
                                               max_iter=self.settings['max_iter'],
                                               verbose=self.settings['verbose'],
                                               method=self.method)

                X.update(zip(unsolved_vars, block_results))

                # populate the row with variables just solved
                self.results_manager.add_results(entry_name, unsolved_vars, block_results)

            # todo will this work if solving ends? move to solve
            # todo: do not insert empty after fail
            # after solving for all variables commit the results as a row
            self.results_manager.commit_results(entry_name)
            
            # add variables from solving results to the set of all variables which has solutions
            #self.all_variables.update(X.keys())  # todo what for??

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
        equation_residuals = [eq.residual for eq in equations]
        # compiled = [compile(expression, '<string>', 'eval') for expression in equation_residuals]
    
        def res_func(x):
            # Update namespace with x's values of variables
            variable_namespace.update({var: val for var, val in zip(variables, x)})
            
            # Compute residuals
            res = [eval(eq, global_namespace, variable_namespace) for eq in equation_residuals]
            return np.array(res, dtype=float)
    
        return res_func
