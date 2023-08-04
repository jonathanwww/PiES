import operator
from pint import DimensionalityError
from lark import Transformer, Tree, Token
from eqsys.variable import Variable


class ValidateUnits(Transformer):
    """
    Use by sending a lark.Tree to the validate method
    requires:
            dictionary with the variables present
                ex: var_dict = {'var_name': var: Variable ... }
            dictionary with the function names and units
                If the function is not decorated with an output unit, it defaults to dimensionless 
                ex: func_dict = {'func_name': func unit ... }
    Returns potential unit errors
        if there is an error in an operation, the output defaults to dimensionless 
    """
    def __init__(self, unit_registry):
        super().__init__()
        self.unit_registry = unit_registry
        self.variables = {}
        self.functions = {}
        self.errors = []
    
    def validate(self, tree, var_dict, func_dict):
        self.variables = var_dict
        self.functions = func_dict
        self.errors = []
        self.transform(tree)
        return self.errors

    def add(self, args):
        return self.process_operation(operator.add, args)

    def sub(self, args):
        return self.process_operation(operator.sub, args)

    def mul(self, args):
        return self.process_operation(operator.mul, args)

    def div(self, args):
        return self.process_operation(operator.truediv, args)

    def atom(self, args):
        # case1: Number. Create dimensionless variable
        if args[0].type == 'NUMBER':
            if args[0].value == '0':
                # If the value is 0, skip checking unit operations with that variable
                return Variable("zero", None)
            else:
                return Variable("number", self.unit_registry.dimensionless)
        # case2: Variable object
        elif args[0].type == 'CNAME':
            return self.variables[args[0].value]
        else:
            raise ValueError(f"Invalid argument type: {args[0].type}")
    
    def function_call(self, function):
        func_name = function[0].value
        unit = self.functions[func_name]
        return Variable(func_name, unit)

    def factor(self, args):
        if args[0].type == 'FUNCTION_CALL':
            return self.function_call(args[0])
        return args[0]

    def neg(self, args):
        return args[0]
    
    def term(self, args):
        return args[0]

    def expression(self, args):
        return args[0]

    def equation(self, args):
        # perform operation between lhs/rhs
        left, right = args
        # we don't care about operations involving 0
        if not (left.name == "zero" or right.name == "zero"):
            # since a=b == a-b=0
            try:
                if left.unit != right.unit:
                    raise DimensionalityError(left.unit, right.unit)
            except DimensionalityError as e:
                self.errors.append((f"{left.name} = +({right.name})", str(e)))  # store error

    def process_operation(self, op, args):
        operand1, operand2 = args
        if operand1 is None or operand2 is None:
            return None
        
        # If either operand is our special "zero" Variable, don't process the operation
        if operand1.name == "zero" or operand2.name == "zero":
            return operand1 if operand2.name == "zero" else operand2
        
        # Perform the operation on unit quantities to get the unit of the result
        try:
            result_unit = op(1 * operand1.unit, 1 * operand2.unit).units
        except DimensionalityError as e:
            self.errors.append((f"{operand1.name} {op.__name__} {operand2.name}", str(e)))  # store error
            # If error occurs, the resulting unit will default unit to dimensionless
            result_unit = self.unit_registry.dimensionless
        return Variable("result", result_unit)
    
