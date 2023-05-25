# -*- coding: utf-8 -*-
################################ Begin license #################################
# Copyright (C) Laboratory of Imaging technologies,
#               Faculty of Electrical Engineering,
#               University of Ljubljana.
#
# This file is part of PyXOpto.
#
# PyXOpto is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyXOpto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyXOpto. If not, see <https://www.gnu.org/licenses/>.
################################# End license ##################################

import os.path

import numpy as np

from .base import Absorption, Interpolator
from xopto import DATA_PATH

class Carotenoid(Absorption):
    material = 'carotenoid'

    def __init__(self):
        super().__init__()
        filename = os.path.join(
            DATA_PATH, 'materials', 'absorption', 'carotenoid_absorption.npy')
        data = np.load(filename)

        self._interpolator = Interpolator.fromfile(
            filename, bounds_error=False, fill_value=(data[0, 1], data[-1, 1])) 

    def __call__(self, wavelength: float or np.ndarray, t: float = None) \
            -> np.ndarray or float:
        '''
        Computes the absorption coefficient of carotenoid.

        Parameters
        ----------
        wavelength: float, np.ndarray
            Wavelength of light (m) at which to compute the absorption
            coefficient of carotenoid.

        t: float
            Temperature not supported by this model.

        Returns
        -------
        mua: float, np.ndarray
            Absorption coefficient (1/m) at the specified wavelength (m).
        '''
        self._interpolator.check_range(wavelength)

        return self._interpolator(wavelength)

    def plot(self, wavelength: np.ndarray = None, show: bool = True):
        '''
        Plot the absorption coefficient at the given wavelengths.

        Parameters
        ----------
        wavelength: np.ndarray
            Wavelengths of light. If None, use the reference values.
        '''
        self._interpolator.plot(wavelength, label=self.material, show=show)


default = Carotenoid()
