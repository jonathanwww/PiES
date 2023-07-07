import networkx as nx
from PyQt6.QtCore import QObject, pyqtSignal
from pint import UnitRegistry
from model.equation import Equation, EquationManager
from model.variable import Variable, VariableManager
from model.util import Grid
from validation.validation import ValidateUnits


class EquationSystem(QObject):
    data_changed = pyqtSignal()
    
    def __init__(self, cache_size=1000):
        super().__init__()
        # is set by validate_equation_system
        self.valid = False
        
        # unit registry for variables and validation
        self.ureg = None
        self.unit_validator = None
        
        # Store function units for validating equations
        # todo: refactor into a functions manager?
        self.function_units = {}
        
        self.equation_manager = EquationManager()
        self.variable_manager = VariableManager(cache_size)

        self.equations = self.equation_manager.equations
        self.variables = self.variable_manager.variables
        
        # to keep track of which variables is parameter vars
        self.parameter_variables = {}
        
        # grid object for solving over a set of variables
        self.grid = Grid()
        
    def _on_change(self) -> None:
        self.data_changed.emit()
        self.valid = False
    
    def _find_all_variables(self, equation_id: str) -> set:
        """
        excluding the variables in equation id
        """
        all_equation_variables = set(var for equation in self.equations.values()
                                     for var in equation.variables
                                     if equation.id != equation_id)
        return all_equation_variables

    def set_ureg_validation(self, ureg: UnitRegistry) -> None:
        self.ureg = ureg
        self.variable_manager.ureg = ureg
        self.unit_validator = ValidateUnits(unit_registry=ureg)
        
    def set_grid(self, grid: Grid) -> None:
        self.grid = grid    
    
    def insert_equation(self, equation: Equation, variables: list[Variable]) -> None:
        # if parameter equation increment value or insert
        if equation.parameter_equation:
            param_var = equation.variables[0]

            # Check if the param is already present, if yes increment its value by 1, if not insert it
            if param_var in self.parameter_variables: 
                self.parameter_variables[param_var] += 1
            else:
                self.parameter_variables[param_var] = 1
                
        # insert equation and variables
        self.equation_manager.insert_equation(equation)
        for variable in variables:
            self.variable_manager.insert_variable(variable)
        self._on_change()

    def delete_equation(self, equation_id: str) -> None:
        # if parameter equation decrease value or delete
        if self.equations[equation_id].parameter_equation:
            param_var = self.equations[equation_id].variables[0]

            # Check if the element is in the dictionary
            if param_var in self.parameter_variables:
                self.parameter_variables[param_var] -= 1
                # If the value is now 1, remove the key
                if self.parameter_variables[param_var] == 0:
                    del self.parameter_variables[param_var]
                
        # Get the set of variables in the equation to be deleted
        eq_vars = self.equations[equation_id].variables
        
        # Get the set of all variables in all other equations
        all_other_vars = self._find_all_variables(equation_id)
        
        # check if there is any variables which is only present in the eq being deleted
        unused_vars = set(eq_vars) - all_other_vars
        
        # delete unused variables and the equation
        for variable in unused_vars:
            self.variable_manager.delete_variable(variable)

        self.equation_manager.delete_equation(equation_id)
        self._on_change()
        
    def validate_grid(self, grid: Grid) -> bool:
        grid_variables = grid.variables.keys()
        eq_variables = self.variables.keys()
        
        # no grid variables overlap with parameter variables
        no_param = all(variable not in self.parameter_variables for variable in grid_variables)
        
        # all grid variables is present in equation system
        all_present = all(variable in eq_variables for variable in grid_variables)

        return all_present and no_param 
    
    def validate_equation(self, equation_id: str) -> list[str]:
        """
        checks if all unit operations is allowed
        returns list of any potential warnings
        """
        equation = self.equation_manager.equations[equation_id]
        var_dict = {}
        for variable in equation.variables:
            # key:(var_name:str) value(var: variable)
            var_dict[variable] = self.variables[variable]
        unit_warnings = self.unit_validator.validate(tree=equation.tree,
                                                     var_dict=var_dict,
                                                     func_dict=self.function_units)
        return unit_warnings
    
    def validate_equation_system(self):
        block_status = {}
        blocks = self.blocking()
        solved_variables = set()
        
        # add grid variables since we are not solving for those
        # parameters is handled by having their own equation, ie their own block
        if self.grid is not None:
            grid_variables = set(self.grid.variables.keys())
            solved_variables.update(grid_variables)
            
        for i, block in enumerate(blocks):
            # Get eqs in block
            block_eqs = [self.equations[eq] for eq in self.equations if self.equations[eq].id in block]

            # Get variables in the current block
            block_vars = list(set(var for eq in block_eqs for var in eq.variables)) 
            
            # Remove block variables that are already solved
            block_vars = [var for var in block_vars if var not in solved_variables]

            # Check the status of the block
            if len(block_vars) == len(block_eqs):
                status = 'valid'
            elif len(block_vars) < len(block_eqs):
                status = 'over-determined'
            elif len(block_vars) > len(block_eqs):
                status = 'under-determined'
            
            # Add block information to the dictionary
            block_status[i] = (status, block_eqs, block_vars)
            
            # Add block variables to solved
            solved_variables.update(block_vars)
            
        # check if all blocks is valid and set eqsys valid status
        all_valid = all(value[0] == 'valid' for value in block_status.values())
        if all_valid:
            self.valid = True
        else:
            self.valid = False
        
        return block_status
    
    def blocking(self) -> list:
        # Get eqs
        eqs = [eq for eq in self.equations.values()]

        # Get nodes
        eq_nodes = [eq.id for eq in eqs]
        var_nodes = list(self.variables.keys())

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
            shared_equations = [eq.id for eq in self.equations.values() if var in eq.variables]
            for shared_eq in shared_equations:
                DG.add_edge(eq, shared_eq)

        sccs = list(nx.strongly_connected_components(DG))
        sccs.reverse()
        return sccs
