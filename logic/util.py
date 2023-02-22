import networkx as nx
import numpy as np
import matplotlib.pyplot as plt


def create_residual_eq(x) -> str:
    eq = x.split('=')
    return eq[0] if eq[1] == '0' else f"{eq[0]}-({eq[1]})"


def clean_input(x: list) -> list[str]:
    cleaned = list(filter(None, x))  # remove empty entries in case of redudandant newlines
    no_comments = list(filter(lambda line: not line.startswith('#'), cleaned))
    return [create_residual_eq(eq) for eq in no_comments]


def jacobian(x, f):
    n = len(x)
    eps = 1e-6
    J = np.zeros((n, n))
    for i in range(n):
        x_eps = x.copy()
        x_eps[i] += eps
        J[:, i] = (f(x_eps) - f(x)) / eps
    return J


def blocking(eq_sys):
    G = nx.DiGraph()
    for i, eq in enumerate(eq_sys.equations):
        G.add_node(i)
        for var in eq.variables:
            for j, eq2 in enumerate(eq_sys.equations):
                if var in eq2.variables:
                    G.add_edge(j, i)

    sccs = [list(c) for c in nx.strongly_connected_components(G)]
    sccs.reverse()
    # match = {i: eq_sys.variables[i].name for i in range(len(eq_sys.variables))}

    #print(blocking2(eq_sys))  # todo: debug

    return sccs


def blocking_matrix_wip(equation_system):
    variable_names = sorted([var.name for var in equation_system.variables], key=str)
    eq_variables = [sorted(eq.variables, key=str) for eq in equation_system.equations]
    new_eq_variables = [[variable_names.index(var_name) for var_name in eq] for eq in eq_variables]
    n = len(variable_names)
    
    # incidence matrix
    incidence_matrix = np.zeros((n, n), dtype=int)    
    for i, var_list in enumerate(new_eq_variables):   
        incidence_matrix[i, var_list] = 1

    # incidence to adjacency matrix
    adjacency_matrix = (np.dot(incidence_matrix, incidence_matrix.T) > 0).astype(int)
    np.fill_diagonal(adjacency_matrix, 0)  # no self reference
    
    # adjacency matrix to directed adjacency matrix
    directed_adjacency_matrix = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(n):
            if adjacency_matrix[i][j] == 1 and incidence_matrix[j][i] == 0:
                directed_adjacency_matrix[i][j] = 1

    # Digraph from adjacency matrix
    T = nx.from_numpy_matrix(directed_adjacency_matrix, create_using=nx.DiGraph)

    # Get strongly connected components
    sccs = [list(c) for c in nx.strongly_connected_components(T)]
    sccs.reverse()
    
    return sccs
        

def blocking2(eq_sys) -> np.array:
    n = len(eq_sys.equations)
    
    G = nx.DiGraph()
    G.add_nodes_from(list(range(n)))
    
    checked_vars = []
    
    for _ in range(n):
        param_eqs = [(eq_sys.equations.index(eq), eq.variables) for eq in eq_sys.equations
                     if len(set(eq.variables) - set(checked_vars)) == 1]
        
        if param_eqs:
            eq_id, var_name = param_eqs[0][0], param_eqs[0][1][0]  # just pick first entry in the param eqs list
            edges = [(eq_id, eq_sys.equations.index(eq)) for eq in eq_sys.equations 
                     if var_name in eq.variables  # if in
                     and var_name != eq.variables[0]  # no reflexiv  
                     and eq.variables[0] not in checked_vars]  # so we don't get it both ways
            G.add_edges_from(edges)
            checked_vars.append(var_name)

            #print('parameter eqs (eq_num, var_name):', param_eqs)
            #print('currenter iter (eq_num, var_name):', eq_id, var_name)
            #print('edges to be added', edges, '\n\n')
        else:
            pass
            #print('no param left')
            # else pick a random variable and add bi-edges between all eqs
            # actually it is just all else that needs adding
    
    nx.draw_networkx(G)
    plt.savefig("testG.png")
    
    sccs = [list(c) for c in nx.strongly_connected_components(G)]
    return sccs.reverse()


    # variable_names = sorted([var.name for var in eq_sys.variables], key=str)  
    #G = nx.Graph()
#
    ## Add nodes to graph
    #G.add_nodes_from(variable_names, bipartite=0)
    #G.add_nodes_from(equation_numbers, bipartite=1)
#
    ## Add edges to graph
    #for eq_num, eq in enumerate(eq_sys.equations):
    #    for var in eq.variables:
    #        G.add_edge(eq_num, var)
    ### 

