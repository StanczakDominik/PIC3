"""Tests the Leapfrog wave PDE solver"""
# coding=utf-8
import matplotlib.pyplot as plt
import numpy as np
import pytest

from algorithms_grid import LeapfrogWaveSolver, LeapfrogWaveInitial
# TODO: use of multigrid methods for wave equation
from helper_functions import l2_test


def plot_all(potential_history, analytical_solution):
    T, X = potential_history.shape
    XGRID, TGRID = np.meshgrid(np.arange(X), np.arange(T))
    for n in range(potential_history.shape[0]):
        plt.plot(potential_history[n])
    fig = plt.figure()
    ax = fig.add_subplot(211)
    CF1 = ax.contourf(TGRID, XGRID, potential_history, alpha=1)
    ax.set_xlabel("time")
    ax.set_ylabel("space")
    plt.colorbar(CF1)
    ax2 = fig.add_subplot(212)
    CF2 = ax2.contourf(TGRID, XGRID, analytical_solution, alpha=1)
    ax2.set_xlabel("time")
    ax2.set_ylabel("space")
    plt.colorbar(CF2)
    plt.show()


@pytest.mark.parametrize(["NX", "NT", "c", "dx", "dt", "initial_potential"],
                         [(1000, 2000, 1 / 2, 0.01, 0.01, lambda x, NX, dx: np.sin(np.pi * x)),
                          (1000, 200, 1 / 2, 0.01, 0.01,
                           lambda x, NX, dx: np.exp(-(x - NX / 2 * dx) ** 2 / (0.1 * NX * dx))),
                          ])
def test_dAlambert(NX, NT, c, dx, dt, initial_potential):
    alpha = c * dt / dx
    print(f"alpha is {alpha}")
    assert alpha <= 1, f"alpha is {alpha}, may not be stable"

    X = np.arange(NX) * dx
    T = np.arange(NT) * dt
    potential = initial_potential(X, NX, dx)
    derivative = np.zeros_like(X)
    potential[0] = potential[-1] = 0
    potential_first = LeapfrogWaveInitial(potential, derivative, c, dx, dt)

    potential_history = np.zeros((NT, NX), dtype=float)
    potential_history[0] = potential
    potential_history[1] = potential_first
    for n in range(2, NT):
        potential_history[n] = LeapfrogWaveSolver(potential_history[n - 1], potential_history[n - 2], c, dx, dt)
    XGRID, TGRID = np.meshgrid(X, T)
    analytical_solution = (initial_potential(XGRID - c * TGRID, NX, dx) + initial_potential(XGRID + c * TGRID, NX,
                                                                                            dx)) / 2

    assert l2_test(analytical_solution, potential_history), plot_all(potential_history, analytical_solution)
    # assert False, plot_all(potential_history, analytical_solution)
