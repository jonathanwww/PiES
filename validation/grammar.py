GRAMMAR = """
?start: equation
?equation: expression "=" expression
?expression: term
           | expression "+" term -> add
           | expression "-" term -> sub
?term: factor
     | term "*" factor -> mul
     | term "/" factor -> div
?factor: atom
       | function_call
       | "(" expression ")"
       | factor ("^" | POW) factor -> pow
       | "-" factor        -> neg
atom: NUMBER
    | CNAME
function_call: (CNAME | DOTTED_NAME) "(" call_args? ")"
call_args: call_arg ("," call_arg)*
call_arg: expression
        | CNAME "=" (expression | STRING)
        | STRING

POW: "**"
STRING: ESCAPED_STRING | SINGLE_QUOTED_STRING
SINGLE_QUOTED_STRING: "\'" /.*?/ "\'"
DOTTED_NAME: CNAME "." CNAME
COMMENT: /#[^\\n]*/

%import common.CNAME
%import common.NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore COMMENT
%ignore WS
"""
