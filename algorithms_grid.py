"""Numerical algorithms for the grid - interpolation to and from the grid, PDE solvers"""
# coding=utf-8
import numpy as np
from scipy import fftpack as fft

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
    left_fractions = 1 - right_fractions
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


def PoissonSolver(rho, k, NG, epsilon_0=1, neutralize=True):
    """solves the Poisson equation spectrally, via FFT

    the Poisson equation can be written either as
    (in position space)
    $$\nabla \cdot E = \rho/\epsilon_0$$
    $$\nabla^2 V = -\rho/\epsilon_0$$

    Assuming that all functions in fourier space can be represented as
    $$\exp{i(kx - \omega t)}$$
    It is easy to see that upon Fourier transformation $\nabla \to ik$, so

    (in fourier space)
    $$E = \rho /(ik \epsilon_0)$$
    $$V = \rho / (-k^2 \epsilon_0)$$

    Calculate that, fourier transform back to position space
    and both the field and potential pop out easily

    The conceptually problematic part is getting the $k$ wave vector right
    # DOCUMENTATION: finish this description
    """

    rho_F = fft.fft(rho)
    if neutralize:
        rho_F[0] = 0
    field_F = rho_F / (1j * k * epsilon_0)
    potential_F = field_F / (-1j * k * epsilon_0)
    field = fft.ifft(field_F).real
    # TODO: check for differences with finite difference field gotten from potential
    energy_presum = (rho_F * potential_F.conjugate()).real[:int(NG / 2)] / 2
    return field, energy_presum


def BunemanSolver(field, current, dt, epsilon_0):
    dE = - dt * current / epsilon_0
    result = field + dE
    # result[-1] = result[0] # TODO: check boundary condition
    return result



def LeapfrogWaveInitial(field, derivative, c, dx, dt):
    alpha = abs(c * dt / dx)
    field_first = dt * derivative[1:-1] + \
                        field[1:-1] * (1 - alpha ** 2) + \
                        0.5 * alpha ** 2 * (field[:-2] + field[2:])
    return field_first


def LeapfrogWaveSolver(field_current, field_previous, c, dx, dt, epsilon_0=1):
    """
    Solves the Laplace equation for a wave with boundary condition at field[0].
    d_dt V - d2_d2x V = 0
    """
    alpha = c * dt / dx
    alpha2 = (alpha) ** 2
    Q = (1 - alpha) / (1 + alpha)
    field_result = np.zeros_like(field_current)
    field_result[1:-1] = -field_previous[1:-1] + \
                         alpha2 * (field_current[:-2] + field_current[2:]) + \
                         2 * (1 - alpha2) * field_current[1:-1]
    # field_result[0] = field_current[1] + Q * (field_current[0] - field_previous[1])
    field_result[-1] = field_current[-2] + Q * (field_current[-1] - field_result[-2])

    energy = 0.5 * epsilon_0 * dx * (field_result[1:-1] ** 2).sum()  # TODO: this is no longer at half intervals!
    return field_result, energy


def BunemanWaveSolver(electric_field, magnetic_field, current, dt, dx, c, epsilon_0):
    # dt = dx/c
    Fplus = 0.5 * (electric_field[:, 1] + c * magnetic_field[:, 1])
    Fminus = 0.5 * (electric_field[:, 1] - c * magnetic_field[:, 1])
    Gplus = 0.5 * (electric_field[:, 2] + c * magnetic_field[:, 0])
    Gminus = 0.5 * (electric_field[:, 2] - c * magnetic_field[:, 0])

    Fplus[1:] = Fplus[:-1] - 0.5 * dt * (current[:-1, 1]) / epsilon_0
    Fminus[:-1] = Fminus[1:] - 0.5 * dt * (current[1:, 1]) / epsilon_0  # TODO: verify the index on current here
    Gplus[1:] = Gplus[:-1] - 0.5 * dt * (current[:-1, 2]) / epsilon_0
    Gminus[:-1] = Gminus[1:] - 0.5 * dt * (current[1:, 2]) / epsilon_0  # TODO: verify the index on current here

    new_electric_field = np.zeros_like(electric_field)
    new_magnetic_field = np.zeros_like(magnetic_field)

    new_electric_field[:, 1] = Fplus + Fminus
    new_electric_field[:, 2] = Gplus + Gminus
    new_magnetic_field[:, 0] = (Gplus - Gminus) / c
    new_magnetic_field[:, 1] = (Fplus - Fminus) / c


    new_electric_field[:,0] = electric_field[:, 0] - dt / epsilon_0 * current[:,0] # TODO: verify indices here
    electric_energy = 0.5 * epsilon_0 * dx * (new_electric_field ** 2).sum()
    magnetic_energy = 0.5 * dx * (new_magnetic_field ** 2).sum()
    return new_electric_field, new_magnetic_field, electric_energy + magnetic_energy


def laser_boundary_condition(t, t_0, tau_e, n, *args):
    return np.exp(-(t - t_0) ** n / tau_e)


def sine_boundary_condition(t, omega, *args):
    return np.sin(omega * t)
