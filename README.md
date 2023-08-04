# Python-integrated Equation Solver
Solves linear and non-linear systems of equations



# Installation

1. Clone the repository:

git clone https://github.com/jonathanwww/equation-solver.git

2. Install the dependencies:

pip install -r requirements.txt

# Usage
Run the app: python main.py

## How does it work?
The equation editor is connected to an equation system.

The equation system is an object which consists of five things:

    a set of equations
    a set of parameters
    a set of variables
    a set of functions
    a namespace

    * The equation system cannot contain duplicate equations or redeclared parameters.

## What are the different objects?

#### Equations:
    A valid equation has a comparison =, !=, <=, >=, <, > and evaluates to a numeric value (int/float/complex)
    The equation is written with python syntax, and any object in the namespace can be referenced

#### Parameters: attributes(unit)
    A valid parameter evaluates to a string, numeric value or a list of any of those.
    If the parameter evaluates to a list, it will be used as a grid which is solved over.

#### Variables: attributes(x0, lb, ub, unit)
    The free variables in the system.
    Any name defined in the equations is a variable, if it's not occupied by the namespace or a parameter.
    If you reference an empty list like so; x[n], it will also be turned into a variable

#### Functions: attributes(unit)
    The functions which is used in the equations
	
** Units are used for validation


## What's special about the equation window?
We swap the operators in the equation window to make it more intuitive for you:

	Python's = is swapped for :=
	Python's == is swapped for =
	
#### It means that under the hood an equation is actually just a comparison expression:
    a-1=b+1 is a python expression on the form: a-1==b+1

#### And a parameter is actually just an assignment:
    a:=1+func() is a python assignment on the form: a=1+func()

#### Other than that, there is a few limits to the equation window:
    - Each line is parsed independently, so you cannot have multi line code
    - a line must consist solely of one of the below objects:
        a comment
        an assignment (Parameter)
        an expression (Equation)
        a function (which outputs ...?)
        a list (of expressions)
            a list comp (of expressions)
            a variable (referring to a list of expressions)

## What is the namespace?
In here you can define objects, such as functions, lists, values etc, which you can use in the equation window.

For example, you can define a=[a-1==2, b+1==3] in the namespace window, and insert it into python window with a.

The namespace is controlled by the namespace window.


## How does solve work?
All equations is sent to the solver and evaluated in the order specified by the blocking heuristic.

The evaluation happens in a namespace which consists of the namespace from the namespace window and the parameters defined in the equation system.

	- blocking
	- differential equation solver
	- complex numbers
	- residual transform
	- picking a solver
	- inequalities