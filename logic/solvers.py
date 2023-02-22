import numpy as np
from logic.util import jacobian


def newton_raphson(residual_func, initial_guesses: np.ndarray, bounds=None, tol=1e-6, max_iter=500, verbose=False):
    x = initial_guesses
    res = residual_func(x)
    
    for i in range(max_iter):
        delta_x = np.linalg.inv(jacobian(x, residual_func)) @ res
        x_new = x - delta_x
        if bounds is not None:
            x_new = np.maximum(x_new, bounds[0])
            x_new = np.minimum(x_new, bounds[1])
        res = residual_func(x_new)
        x = x_new

        if verbose:
            print(f"Iteration {i + 1}: x = {x}, delta_x = {delta_x}")
        if max(abs(res)) < tol:
            break
    else:
        raise RuntimeError(f"newton_raphson did not converge after {max_iter} iterations")

    return x
