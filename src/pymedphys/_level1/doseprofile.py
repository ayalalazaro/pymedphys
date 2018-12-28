# Copyright (C) 2018 Paul King

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version (the "AGPL-3.0+").

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License and the additional terms for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# ADDITIONAL TERMS are also included as allowed by Section 7 of the GNU
# Affrero General Public License. These aditional terms are Sections 1, 5,
# 6, 7, 8, and 9 from the Apache License, Version 2.0 (the "Apache-2.0")
# where all references to the definition "License" are instead defined to
# mean the AGPL-3.0+.

# You should have received a copy of the Apache-2.0 along with this
# program. If not, see <http://www.apache.org/licenses/LICENSE-2.0>.


from scipy import interpolate

import numpy as np


from .._level0.libutils import get_imports
IMPORTS = get_imports(globals())


# DISTANCE FUNCTIONS

def make_dist_vals(dist_strt, dist_stop, dist_step):
    """
    Return a list of distance-values; beginning at distance-start,
    ending at distance-stop, and spaced at increments of distance-step.
    """

    num_steps = int(np.ceil((dist_stop - dist_strt) / dist_step))
    dist_vals = dist_strt + dist_step * np.array(range(num_steps + 1))

    num_digits = len(str(dist_step).split('.')[-1])
    dist_vals = list(np.round(dist_vals, num_digits))
    return dist_vals


def get_dist_vals(dose_prof):
    """
    Return a list of distance-values, from a dose-profile.
    """

    try:
        dist_vals = [float(i[0]) for i in dose_prof]
    except:
        dist_vals = None

    return dist_vals


# DOSE FUNCTIONS

def make_dose_vals(dist_vals, dose_func):
    """
    Return a list of dose-values; for doses corresponding to distance-values,
    and created using a generating dose-function.
    """
    dose_vals = []
    for x in dist_vals:
        try:
            dose_vals.append(float(dose_func(x)))
        except ValueError:
            dose_vals.append(0.0)
    return dose_vals


def get_dose_vals(dose_prof):
    """
    Return a list of dose-values, from a dose-profile.
    """

    try:
        dose_vals = [float(i[1]) for i in dose_prof]
    except:
        dose_vals = None

    return dose_vals


# PROFILE FUNCTIONS

def make_dose_prof(dist_vals, dose_vals):
    """
    Return a dose-profile, from provided distance-values and dose-values.
    """

    result = list(
        zip([float(i) for i in dist_vals],
            [float(i) for i in dose_vals]))
    return result


def is_even_spaced(dose_prof):
    """
    Return True iff the distance locations of a dose-profile are evenly spaced.
    """

    diffs = np.diff(get_dist_vals(dose_prof))
    avg_diff = np.mean(diffs)
    if(np.allclose(diffs, avg_diff)):
        return True
    else:
        return False


def shift_dose_prof(dose_prof, dist):
    """
    Return a dose-profile where distance values are shifted by the indicated amount.
    """
    dist_vals = np.add(get_dist_vals(dose_prof), dist)
    dose_vals = get_dose_vals(dose_prof)
    return make_dose_prof(dist_vals, dose_vals)


def make_pulse_dose_prof(centre=0.0, width=10.0, dist_strt=-20.0, dist_stop=20.0, dist_step=0.1):
    """
    make_pulse_dose_prof is not implemented
    """
    return "make_pulse_dose_prof is not implemented"


def resample(dose_prof, dist_strt=-np.inf, dist_stop=np.inf, dist_step=0.1):
    """
    Return a dose-profile from a supplied profile, extending from
    distance-start to distance-stop, and resampled at the supplied
    distance-step.
    """

    dose_func = interpolate.interp1d(
        get_dist_vals(dose_prof),
        get_dose_vals(dose_prof),
        kind='linear')
    dist_strt, dist_stop = find_strt_stop(dose_prof, dist_strt, dist_stop)

    dist_vals = make_dist_vals(dist_strt, dist_stop, dist_step)
    dose_vals = make_dose_vals(dist_vals, dose_func)

    resampled = make_dose_prof(dist_vals, dose_vals)

    return resampled


def align_to(dose_prof_moves, dose_prof_fixed, dist_step=0.1):  # STUB  ######
    """ align_to is not yet implemented """  # WRITE DOCSTRING !!!!!!!!

    dist_vals_moves = get_dist_vals(dose_prof_moves)
    dose_vals_moves = get_dose_vals(dose_prof_moves)

    dist_vals_fixed = get_dist_vals(dose_prof_fixed)
    dose_vals_fixed = get_dose_vals(dose_prof_fixed)

    min_possible_offset = max(min(dist_vals_moves), min(dist_vals_fixed))
    max_possible_offset = min(max(dist_vals_moves), max(dist_vals_fixed))
    inc_possible_offset = 0.5 * min(min(np.diff(dist_vals_moves)),
                                    min(np.diff(dist_vals_fixed)))
    possible_offsets = (make_dist_vals
                        (min_possible_offset,
                         max_possible_offset,
                         inc_possible_offset))

    dose_func_fixed = interpolate.interp1d(dist_vals_fixed, dose_vals_fixed)

    dose_func_moves = interpolate.interp1d(dist_vals_moves, dose_vals_moves)

    best_correlation_factor = 0
    best_offset = -np.inf

    new_coords = make_dist_vals(3 * min(min(dist_vals_moves), min(dist_vals_fixed)),
                                3 * max(max(dist_vals_moves),
                                        max(dist_vals_fixed)),
                                dist_step)
    ref_fixed = make_dose_vals(new_coords, dose_func_fixed)

    for offset in possible_offsets:
        moved_profile = shift_dose_prof(dose_prof_moves, offset)
        moved_x_vals = get_dist_vals(moved_profile)
        moved_d_vals = get_dose_vals(moved_profile)
        dose_func_moves = interpolate.interp1d(moved_x_vals, moved_d_vals)

        correl = np.correlate(ref_fixed,
                              make_dose_vals(new_coords, dose_func_moves))
        if max(correl) > best_correlation_factor:
            best_correlation_factor = max(correl)
            best_offset = offset

    return(best_offset)


def is_wedged(dose_prof):  # STUB  ######
    """ Return True iff dose-profile has significant gradient in the umbra. """
    wedginess = np.average(np.diff(get_dose_vals(find_umbra(dose_prof))))
    if wedginess > 0.05:  # threshold, this is a 'magic number'
        return True
    else:
        return False
    # return('is_wedge is not yet implemented')

# SLICING FUNCTIONS


def find_strt_stop(dose_prof, dist_strt, dist_stop):
    """
    Return as a tuple, the distance-to-start and distance-to-stop, which are the
    end-points of a dose-profile or, optionally, suggested start and stop
    distances, which ever is more restrictive.
    """

    dist_vals = get_dist_vals(dose_prof)

    if not dist_strt:
        dist_strt = -np.inf
    dist_strt = max(dist_strt, min(dist_vals))

    if not dist_stop:
        dist_stop = np.inf
    dist_stop = min(dist_stop, max(dist_vals))

    assert dist_stop > dist_strt
    return (dist_strt, dist_stop)


def slice_dose_prof(dose_prof, dist_strt=-np.inf, dist_stop=np.inf):
    """
    Return a dose-profile, sliced from a supplied profile, including
    only points betwee distance-start and distance-stop.
    """
    return [d for d in dose_prof if d[0] >= dist_strt and d[0] <= dist_stop]


def find_edges(dose_prof):
    """
    Return a tuple, the distance of the two profile edges, calculated
    as the distances of greatest postivie and negative gradient.
    """

    resampled = resample(dose_prof)

    dist_vals = get_dist_vals(resampled)
    dose_vals = get_dose_vals(resampled)

    max_dose = max(dose_vals)
    min_dose = min(dose_vals)
    inc_dose = (max_dose - min_dose)/100
    test_doses = [max_dose - i*inc_dose for i in range(101)]

    for t in test_doses:
        cr = find_dists(dose_prof, t/2.0)

    dydx = list(np.gradient(dose_vals, dist_vals))
    lt_edge = dist_vals[dydx.index(max(dydx))]
    rt_edge = dist_vals[dydx.index(min(dydx))]
    return (lt_edge, rt_edge)


def find_umbra(dose_prof):
    """
    Return a dose-profile from a supplied profile, including only the
    central 80% of the profile between the end-points.
    """
    edges = find_edges(dose_prof)
    umbra = slice_dose_prof(dose_prof, dist_strt=0.8 *
                            edges[0], dist_stop=0.8*edges[-1])
    return umbra

# SCALING FUNCTIONS


def find_dose(dose_prof, dist):
    """
    Return the dose from a dose-profile, corresponding to a provided distance.
    """

    dose_func = interpolate.interp1d(
        get_dist_vals(dose_prof),
        get_dose_vals(dose_prof),
        kind='linear')
    dose = dose_func(dist)

    return(dose)


def find_dists(dose_prof, dose):
    """
    Return a list of distances where dose-profile takes on a value of dose.
    """

    x = get_dist_vals(dose_prof)
    d = get_dose_vals(dose_prof)
    dists = []
    for i in range(1, len(x)):
        val = None
        if d[i] != d[i-1]:
            # bracket threshold
            if (d[i]-dose)*(d[i-1]-dose) < 0:
                # interpolate
                val = (x[i]-((d[i]-dose)/(d[i]-d[i-1]))*(x[i]-x[i-1]))
        elif d[i] == dose:
            val = x[i]
        if val and (val not in dists):
            dists.append(val)
    return dists


def norm_dose_vals(dose_prof, dist=0.0, dose=100.0):
    """
    Return a dose-profile from a supplied profile, in which the dose
    values are rescaled so as to yield a specified dose and the
    specified distance.
    """

    norm_fact = dose / find_dose(dose_prof, dist)
    d = [norm_fact * i for i in get_dose_vals(dose_prof)]

    return make_dose_prof(get_dist_vals(dose_prof), d)


def norm_dist_vals(dose_prof):
    """
    Return a dose-profile from a supplied profile, in which the distance
    values are rescaled to 2X/W so as to position the beam edges at
    distances of +/-1.

        | (1) Milan & Bentley, BJR Feb-74, The Storage and manipulation
              of radiation dose data in a small digital computer
        | (2) Heintz, King, & Childs, May-95, User Manual,
              Prowess 3000 CT Treatment Planning
    """

    x = get_dist_vals(dose_prof)
    d = get_dose_vals(dose_prof)

    lt_edge, rt_edge = find_edges(dose_prof)
    cax = (lt_edge + rt_edge)/2.0

    result = []
    for i, dist in enumerate(x):
        if dist < cax:
            result.append((dist/lt_edge, d[i]))
        elif dist == cax:
            result.append((0.0, d[i]))
        elif dist > cax:
            result.append((dist/rt_edge, d[i]))
    return result


def cent_dose_prof(dose_prof):
    """
    Return a dose-profile from a supplied profile, in which the distance values
    are translated so as to place the central-axis, midway between the edges,
    at zero distance.
    """

    dist_vals = get_dist_vals(dose_prof)
    dose_vals = get_dose_vals(dose_prof)
    cax = np.mean(find_edges(dose_prof))

    cent_prof = []
    for i, dist in enumerate(dist_vals):
        cent_prof.append((dist - cax, dose_vals[i]))
    return cent_prof

# FLATNESS & SYMMETRY FUNCTIONS


def flatness(dose_prof):
    """
    Return float value of flatness for a supplied dose-profile.
    """
    dose = get_dose_vals(find_umbra(dose_prof))
    flat = (max(dose)-min(dose))/np.average(dose)
    return flat


def symmetry(dose_prof):
    """
    Return float value of symmetry for a supplied dose-profile.
    """
    dose = get_dose_vals(find_umbra(dose_prof))
    avg_dose = np.average(dose)
    dose_rev = dose[::-1]
    symmetry = max(np.abs(np.subtract(dose, dose_rev)/avg_dose))
    return symmetry


def make_dose_prof_sym(dose_prof, dist_step=0.1):  # STUB  ######
    """
    Return a dose-profile from a supplied profile, which has been made
    symmetric by averaging dose values over corresponding distances across
    the central axis, and resampled at increments of distance-step.
    """
    dist_vals = get_dist_vals(dose_prof)

    start = -min(-dist_vals[0], dist_vals[-1])
    stop = min(-dist_vals[0], dist_vals[-1])

    dose_prof = resample(dose_prof, dist_strt=start,
                         dist_stop=stop, dist_step=dist_step)

    rev = dose_prof[::-1]

    result = [(dose_prof[i][0], (dose_prof[i][1]+rev[i][1])/2.0)
              for i, _ in enumerate(dose_prof)]

    return result
