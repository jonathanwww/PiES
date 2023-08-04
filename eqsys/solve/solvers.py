import autograd.numpy as np
from autograd import jacobian
import logging
import scipy.optimize as sio

# Use a method selector to enable different solvers for debugging
# method = -1: compare SciPy least squares and the internal solver
# method =  0: use the internal solver (default)
# method =  1: use SciPy least squares
# method =  2: use SciPy minimizer


def solver_wrapper(residual_func, initial_guesses: np.ndarray, bounds=None, tol=1e-6, max_iter=500, verbose=False, method=0):
    if method == 0:
        return newton_raphson(residual_func, initial_guesses, bounds=bounds, tol=tol, max_iter=max_iter, verbose=verbose)
    elif method == 1:
        res_sio = sio.least_squares(residual_func, initial_guesses, jac='2-point', bounds=bounds, method='trf', ftol=1e-08, xtol=1e-08, gtol=1e-08, x_scale=1.0, loss='linear', f_scale=1.0, diff_step=None, tr_solver=None, tr_options={}, jac_sparsity=None, max_nfev=max_iter*5, verbose=verbose, args=(), kwargs={})
        return res_sio.x
    elif method == 2:
        sio_bounds = [(lo, hi) for lo, hi in zip(*bounds)]
        sio_residual = lambda x: np.sum(np.power(residual_func(x), 2))
        res_sio = sio.minimize(sio_residual, initial_guesses, args=(), method=None, jac=None, hess=None, hessp=None, bounds=sio_bounds, constraints=(), tol=tol, callback=None, options=None)
        return res_sio.x
    elif method == -1:
        res_int = solver_wrapper(residual_func, initial_guesses, bounds=bounds, tol=tol, max_iter=max_iter, verbose=verbose, method=0)
        res_sio = solver_wrapper(residual_func, initial_guesses, bounds=bounds, tol=tol, max_iter=max_iter, verbose=verbose, method=1)
        logging.error("Difference vs scipy: %s", str(res_sio - res_int))
        return res_int
    logging.error("No solver selected, returning an invalid result.")
    return np.full_like(initial_guesses, np.NaN)


def newton_raphson(residual_func, initial_guesses: np.ndarray, bounds=None, tol=1e-6, max_iter=500, verbose=False):
    x = np.array(initial_guesses, dtype=float)
    res = residual_func(x)

    jacobian_func = jacobian(residual_func)

    for i in range(max_iter):
        J = jacobian_func(x)
        if verbose:
            print(f"Jacobian at iteration {i + 1}:\n", J)
        delta_x = np.linalg.solve(J, res)
        x_new = x - delta_x

        if bounds is not None:
            x_new = np.maximum(x_new, bounds[0])
            x_new = np.minimum(x_new, bounds[1])
        res = residual_func(x_new)
        x = x_new

        if verbose:
            print(f"Iteration {i + 1}: x = {x}, delta_x = {delta_x}")
        if np.linalg.norm(res) < tol:
            break
    else:
        raise RuntimeError(f"newton_raphson did not converge after {max_iter} iterations")

    return x
