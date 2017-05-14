# coding=utf-8
import numpy as np


def charge_density_deposition(x, dx, x_particles, particle_charge):
    """scatters charge from particles to grid
    uses linear interpolation
    x_i | __________p___| x_i+1
    for a particle $p$ in cell $i$ of width $dx$ the location in cell is defined as
    $$X_p = x_p - x_i$$
    then, $F_r = X_p/dx$ is the fraction of charge going to the right side of the cell
    (as $X_p \to dx$, the particle is closer to the right cell)
    while $F_l = 1-F_r$ is the fraction of charge going to the left

    numpy.bincount is used to count particles in cells
    the weights are the fractions for each cell

    to change the index for the right going  (keeping periodic boundary conditions)
    numpy.roll is used
    """
    logical_coordinates = (x_particles / dx).astype(int)
    right_fractions = x_particles / dx - logical_coordinates
    left_fractions = 1 - right_fractions
    charge_to_right = particle_charge * right_fractions
    charge_to_left = particle_charge * left_fractions
    charge_hist_to_right = np.roll(np.bincount(logical_coordinates, charge_to_right, minlength=x.size), +1)
    charge_hist_to_left = np.bincount(logical_coordinates, charge_to_left, minlength=x.size)
    return charge_hist_to_right + charge_hist_to_left


def longitudinal_current_deposition(j_x, x_velocity, x_particles, time, dx, dt, q):
    """
    :param x_velocity: particle x velocities
    :type x_velocity: ndarray
    :param x_particles: particle locations
    :type x_particles: ndarray
    :param time: dt by default
    :type time: float
    :param dx: grid size
    :type dx: float
    :param q: particle charge
    :type q: float
    :return: 
    :rtype:
    """

    # print(j_x, x_velocity, x_particles, time, dx, dt, q)
    epsilon = 1e-4 * dx
    logical_coordinates_n = (x_particles / dx).astype(int)

    particle_in_left_half = x_particles / dx - logical_coordinates_n <= 0.5
    particle_in_right_half = ~particle_in_left_half
    velocity_to_left = x_velocity < 0
    velocity_to_right = ~velocity_to_left

    case1 = particle_in_left_half & velocity_to_left
    case2 = particle_in_right_half & velocity_to_left
    case3 = particle_in_right_half & velocity_to_right
    case4 = particle_in_left_half & velocity_to_right

    t1 = np.empty_like(x_particles)
    logical_coordinates_depo = logical_coordinates_n.copy()
    logical_coordinates_depo[case2 | case3] += 1
    # case1
    t1[case1] = -(x_particles[case1] - (logical_coordinates_n[case1]) * dx) / x_velocity[case1]
    t1[case2] = -(x_particles[case2] - (logical_coordinates_n[case2] + 0.5) * dx) / x_velocity[case2]
    t1[case3] = ((logical_coordinates_n[case3] + 1) * dx - x_particles[case3]) / x_velocity[case3]
    t1[case4] = ((logical_coordinates_n[case4] + 1.5) * dx - x_particles[case4]) / x_velocity[case4]
    switches_cells = t1 < time


    if (~switches_cells).any():
        nonswitching_current_contribution = q * x_velocity[~switches_cells] * time[~switches_cells]
        # print(f"nonswitching {nonswitching_current_contribution}")
        j_x += np.bincount(logical_coordinates_depo[~switches_cells] + 1, nonswitching_current_contribution,
                            minlength=j_x.size)

    new_time = time - t1
    switching_current_contribution = q * x_velocity[switches_cells] * t1[switches_cells] / dt
    # print(f"switching {switching_current_contribution}")
    j_x += np.bincount(logical_coordinates_depo[switches_cells] + 1, switching_current_contribution, minlength=j_x.size)

    new_locations = np.empty_like(x_particles)
    new_locations[case1] = logical_coordinates_n[case1] * dx - epsilon
    new_locations[case2] = (logical_coordinates_n[case2] + 0.5) * dx - epsilon
    new_locations[case3] = (logical_coordinates_n[case3] + 1) * dx
    new_locations[case4] = (logical_coordinates_n[case4] + 0.5) * dx

    if switches_cells.any():
        # print(f"Switching at {switches_cells}")
        longitudinal_current_deposition(j_x, x_velocity[switches_cells], new_locations[switches_cells],
                                        new_time[switches_cells], dx, dt, q)

def transversal_current_deposition(j_yz, velocity, x_particles, time, dx, dt, q):
    x_velocity = velocity[:, 0]
    yz_velocity = velocity[:, 1:]
    print(f"x0: {x_particles}\t v: {velocity}\t x1: {x_particles + velocity[:,0]*time} \t time: {time}")

    epsilon = 1e-4 * dx
    logical_coordinates_n = (x_particles / dx).astype(int)
    particle_in_left_half = x_particles / dx - logical_coordinates_n <= 0.5
    particle_in_right_half = ~particle_in_left_half

    # stationary_x_particle = np.isclose(x_velocity, 0)
    velocity_to_left = x_velocity < 0
    velocity_to_right = ~velocity_to_left

    t1 = np.empty_like(x_particles)
    s = np.empty_like(x_particles)

    case1 = particle_in_left_half & velocity_to_left
    case2 = particle_in_left_half & velocity_to_right
    case3 = particle_in_right_half & velocity_to_right
    case4 = particle_in_right_half & velocity_to_left
    t1[case1] = - (x_particles[case1] - logical_coordinates_n[case1] * dx) / x_velocity[case1]
    s[case1] = logical_coordinates_n[case1] * dx - epsilon

    t1[case2] = ((logical_coordinates_n[case2] + 0.5) * dx - x_particles[case2])/x_velocity[case2]
    s[case2] = (logical_coordinates_n[case2] + 0.5) * dx

    t1[case3] = ((logical_coordinates_n[case3] + 1) * dx - x_particles[case3])/x_velocity[case3]
    s[case3] = (logical_coordinates_n[case3] + 1) * dx

    t1[case4] = -(x_particles[case4] - (logical_coordinates_n[case4] + 0.5) * dx)/x_velocity[case4]
    s[case4] = (logical_coordinates_n[case4] + 0.5)*dx - epsilon

    #debug
    cases = np.zeros_like(x_particles, dtype=int)
    cases[case1] = 1
    cases[case2] = 2
    cases[case3] = 3
    cases[case4] = 4
    print("cases", cases)
    print("t1", t1)

    switches_cells = t1 < time
    w = np.empty_like(x_particles)
    case1[:] = particle_in_left_half & switches_cells
    case2[:] = particle_in_left_half & ~switches_cells
    case3[:] = particle_in_right_half & ~switches_cells
    case4[:] = particle_in_right_half & switches_cells

    A = q * yz_velocity / dt
    if switches_cells.any():
        A[switches_cells,:] *= t1[switches_cells]
    if (~switches_cells).any():
        A[~switches_cells,:] *= time[~switches_cells]

    w[case1] = 2.5 - logical_coordinates_n[case1] + (x_particles[case1] + 0.5 * x_velocity[case1] * t1[case1]) / dx
    w[case2] = 2.5 - logical_coordinates_n[case2] + (x_particles[case2] + 0.5 * x_velocity[case2] * time[case2]) / dx
    w[case3] = logical_coordinates_n[case3] - 0.5 - (x_particles[case3] + 0.5 * x_velocity[case3] * time[case3]) / dx
    w[case4] = logical_coordinates_n[case4] - 0.5 - (x_particles[case4] + 0.5 * x_velocity[case4] * t1[case4]) / dx

    j_yz[:,0] += np.bincount(logical_coordinates_n+1, w*A[:,0], minlength=j_yz[:,1].size)
    j_yz[:,1] += np.bincount(logical_coordinates_n+1, w*A[:,1], minlength=j_yz[:,1].size)

    logical_coordinates_depo = logical_coordinates_n.copy()
    logical_coordinates_depo[particle_in_left_half] -= 1
    logical_coordinates_depo[particle_in_right_half] += 1
    j_yz[:,0] += np.bincount(logical_coordinates_depo+1, (1-w)*A[:,0], minlength=j_yz[:,1].size)
    j_yz[:,1] += np.bincount(logical_coordinates_depo+1, (1-w)*A[:,1], minlength=j_yz[:,1].size)


    if switches_cells.any():
        new_time = time - t1
        transversal_current_deposition(j_yz, velocity[switches_cells], s[switches_cells],
                                      new_time[switches_cells], dx, dt, q)

def current_density_deposition(x, dx, x_particles, particle_charge, velocity):
    """scatters charge from particles to grid
    uses linear interpolation
    x_i | __________p___| x_i+1
    for a particle $p$ in cell $i$ of width $dx$ the location in cell is defined as
    $$X_p = x_p - x_i$$
    then, $F_r = X_p/dx$ is the fraction of charge going to the right side of the cell
    (as $X_p \to dx$, the particle is closer to the right cell)
    while $F_l = 1-F_r$ is the fraction of charge going to the left

    numpy.bincount is used to count particles in cells
    the weights are the fractions for each cell

    to change the index for the right going  (keeping periodic boundary conditions)
    numpy.roll is used
    """
    logical_coordinates = (x_particles / dx).astype(int)
    right_fractions = x_particles / dx - logical_coordinates
    left_fractions = -right_fractions + 1.0
    current_to_right = particle_charge * velocity * right_fractions.reshape(x_particles.size, 1)
    current_to_left = particle_charge * velocity * left_fractions.reshape(x_particles.size, 1)
    # OPTIMIZE: use numba with this
    current_hist = np.zeros((x.size, 3))
    for dim in range(3):
        current_hist[:, dim] += np.bincount(logical_coordinates, current_to_left[:, dim], minlength=x.size)
        current_hist[:, dim] += np.roll(np.bincount(logical_coordinates, current_to_right[:, dim], minlength=x.size),
                                        +1)
    return current_hist


def interpolateField(x_particles, scalar_field, x, dx):
    """gathers field from grid to particles

    the reverse of the algorithm from charge_density_deposition

    there is no need to use numpy.bincount as the map is
    not N (number of particles) to M (grid), but M to N, N >> M
    """
    logical_coordinates = (x_particles / dx).astype(int)
    NG = scalar_field.size
    right_fractions = x_particles / dx - logical_coordinates
    field = (1 - right_fractions) * scalar_field[logical_coordinates] + \
            (right_fractions) * scalar_field[(logical_coordinates + 1) % NG]
    return field
