# coding=utf-8
import numpy as np
import pytest
import matplotlib.pyplot as plt

from Grid import Grid
from Species import Species
from algorithms_interpolate import longitudinal_current_deposition


@pytest.mark.parametrize("power", range(2, 8))
def test_longitudinal_deposition(power):
    N = 10 ** power
    s = Species(1 / N, 1, N, "test particles", 1, 1, 1)
    g = Grid()
    s.distribute_uniformly(g.L, 1e-6, g.L / 4, g.L / 4)
    # s.v[:, 0] = np.random.normal(scale=0.1, size=N)
    # s.v[:,0] = s.c*0.9
    s.v[:, 0] = g.dx / 3
    dt = g.dx

    longitudinal_current_deposition(g.current_density[:, 0], s.v[:, 0], s.x, dt, g.dx, dt, s.q)
    # plt.plot(g.x, g.current_density[1:-1, 0], label=N)
    # print(g.dx * g.current_density[:,0].sum())

    total_gathered_current = (g.current_density[1:-1, 0].sum() / (s.v[:, 0].mean()))
    assert np.isclose(total_gathered_current, 1, rtol=1e-1), "Longitudinal current deposition seems off!"
    # expected_current = np.zeros_like(g.x)
    # inside_moat = (g.x > g.L / 4) & (g.x < g.L * 3 / 4)
    # average_current = 1 / (g.L / (inside_moat.sum() / g.NG)) * s.v[:, 0].mean()
    # expected_current[inside_moat] = average_current
    # print(g.dx * expected_current.sum())
    # plt.plot(g.x, expected_current, "--", label="expected")
    # plt.xticks(g.x)
    # plt.legend()
    # plt.figure()
    # plt.plot(g.x, expected_current - g.current_density[1:-1,0])
    # plt.show()


def test_single_particle_deposition():
    s = Species(1, 1, 1, "test particle", 1, 1, 1)
    g = Grid(NG = 9)
    s.x[:] = g.L/2
    s.v[:, 0] = -1/3
    dt = s.c * g.dx
    plt.scatter(s.x, np.zeros_like(s.x))
    plt.xticks(g.x)
    plt.grid()
    longitudinal_current_deposition(g.current_density[:, 0], s.v[:, 0], s.x, dt, g.dx, dt, s.q)
    plt.plot(g.x, g.current_density[1:-1, 0])
    plt.show()

if __name__ == '__main__':
    test_single_particle_deposition()