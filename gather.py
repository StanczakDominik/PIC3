def interpolateField(x_particles, electric_field, x, dx):
    """gathers field from grid to particles

    the reverse of the algorithm from charge_density_deposition

    there is no need to use numpy.bincount as the map is
    not N (number of particles) to M (grid), but M to N, N >> M
    """
    indices_on_grid = (x_particles / dx).astype(int)
    NG = electric_field.size
    field = (x[indices_on_grid] + dx - x_particles) * electric_field[indices_on_grid] +\
        (x_particles - x[indices_on_grid]) * electric_field[(indices_on_grid + 1) % NG]
    return field / dx