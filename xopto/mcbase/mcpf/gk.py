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

from typing import Tuple
import numpy as np

from .pfbase import PfBase, cltypes, McObject
import xopto.pf


class Gk(PfBase):
    @staticmethod
    def cl_type(mc: McObject) -> cltypes.Structure:
        '''
        Returns an OpenCL structure that can be passed to the Monte carlo
        simulator.

        Parameters
        ----------
        mc: McObject
            A Monte Carlo simulator instance.

        Returns
        -------
        struct: cltypes.Structure
            A structure type that represents the scattering phase function in
            the Monte Carlo kernel.

        Structure fields
        ----------------
        g: mc_fp_t
            Parameter of the Gegenbauer kernel scattering phase function.

        a: mc_fp_t
            Parameter of the Gegenbauer kernel scattering phase function.

        inv_a, a1, a2: mc_fp_t
            Precalculated constants used to speed up the computation.
        '''
        T = mc.types
        class ClGk(cltypes.Structure):
            _fields_ = [
                ('g', T.mc_fp_t),
                ('a', T.mc_fp_t),
                ('inv_a', T.mc_fp_t),
                ('a1', T.mc_fp_t),
                ('a2', T.mc_fp_t)
            ]

        return ClGk

    @staticmethod
    def cl_declaration(mc: McObject) -> str:
        '''
        OpenCL declarations of the scattering phase function.
        '''
        return  '\n'.join((
            'struct MC_STRUCT_ATTRIBUTES McPf{',
            '	mc_fp_t g;',
            '	mc_fp_t a;',
            '	mc_fp_t inv_a;',
            '	mc_fp_t a1;',
            '	mc_fp_t a2;',
            '};',
            'void dbg_print_pf(const McPf *pf);',
        ))

    @staticmethod
    def cl_implementation(mc: McObject) -> str:
        '''
        OpenCL implementation of the scattering phase function.
        '''
        return '\n'.join((
            'void dbg_print_pf(const McPf *pf) {',
            '	dbg_print("Gk scattering phase function:");',
            '	dbg_print_float(INDENT "g:", pf->g);',
            '	dbg_print_float(INDENT "a:", pf->a);',
            '	dbg_print_float(INDENT "inv_a:", pf->inv_a);',
            '	dbg_print_float(INDENT "a1:", pf->a1);',
            '	dbg_print_float(INDENT "a2:", pf->a2);',
            '};',
            '',
            'inline mc_fp_t mcsim_pf_sample_angles(McSim *mcsim, mc_fp_t *azimuth){',
            '	mc_fp_t tmp, cos_theta;',
            '	mc_fp_t g = mcsim_current_pf(mcsim)->g;',
            '	mc_fp_t a = mcsim_current_pf(mcsim)->a;',
            '	mc_fp_t inv_a = mcsim_current_pf(mcsim)->inv_a;',
            '	mc_fp_t a1 = mcsim_current_pf(mcsim)->a1;',
            '	mc_fp_t a2 = mcsim_current_pf(mcsim)->a2;',
            '',
            '	*azimuth = FP_2PI*mcsim_random(mcsim);',
            '',
            '	if (g == FP_0) {',
            '		cos_theta = FP_1 - FP_2*mcsim_random(mcsim);',
            '	} else if(a == FP_0) {',
            '		cos_theta = a1 + mc_pow(',
            '			mc_fdiv(FP_1 - g, FP_1 + g),',
            '			FP_2*mcsim_random(mcsim)',
            '		)*a2;',
            '	} else {',
            '		tmp = a1*mcsim_random(mcsim) + a2;',
            '		tmp = FP_1 + g*g - mc_pow(tmp, -inv_a);',
            '		cos_theta = mc_fdiv(tmp, FP_2*g);',
            '	};',
            '',
            '	return mc_fclip(cos_theta, -FP_1, FP_1);',
            '};'
        ))

    def __init__(self, g: float, a: float):
        '''
        Gegenbauer kernel scattering phase function constructor.

        Parameters
        ----------
        g: float
            Parameter of the Gegenbauer kernel scattering scattering phase
            function.
            :math:`|g| <= 1`
        a: float
            Parameter of the Gegenbauer kernel scattering phase function.
            :math:`a > - 1/2`
            A value of 0.5 produces the Henyey-Greenstein scattering
            phase function.
        '''
        super().__init__()
        self._g = self._a = 0.0
        self._precalculated = None

        self._set_g(g)
        self._set_a(a)
        self._recalculate()

    def _get_g(self) -> float:
        return self._g
    def _set_g(self, g: float):
        self._g = min(max(float(g), -1.0), 1.0)
        self._recalculate()
    g = property(_get_g, _set_g, None, 'Anisotropy factor when a=0.5.')

    def _get_a(self) -> float:
        return self._a
    def _set_a(self, a: float):
        self._a = max(float(a), -0.5)
        self._recalculate()
    a = property(_get_a, _set_a, None, 'Parameter alpha.')

    def _recalculate(self) -> Tuple[float, float, float]:
        # precalculate some values
        g, a = self._g, self._a
        if g == 0:
            # cosTheta = 1 - 2*random
            invA = a1 = a2 = 0
        elif a == 0:
            # cosTheta = (1+g^2)/(2*g) - ((1-g)/(1+g)).^(2*random)*(1+2*g+g^2)/(2*g)
            a1 = (1 + g**2)/(2*g)
            a2 = (1 + 2*g + g**2)/(2*g)
            invA = 0.0
        else:
            # tmp = a1 * random + a2
            # tmp = 1 + g * g - pow(tmp, -inva)
            # cosTheta = tmp / (2*g)

            temp = a*g*(1.0 - g*g)**(2.0*a)
            temp = temp/(np.pi*((1.0 + g)**(2.0*a) - (1.0 - g)**(2.0*a)))
            a1 = 2.0*a*g/(2.0*np.pi*temp)
            a2 = (1 + g)**(-2.0*a)
            invA = 1.0/a

        self._precalculated = [invA, a1, a2]

    def pf(self) -> xopto.pf.Gk:
        '''
        Returns a new instance of the related utility scattering phase function
        class that can be used to compute Legendre moments and other
        scattering phase function quantifiers.

        Returns
        -------
        pf: xopto.pf.Gk
            Instance of the related utility scattering phase function.
        '''
        return xopto.pf.Gk(self.g, self.a)

    def cl_pack(self, mc: McObject, target: cltypes.Structure = None) \
            -> cltypes.Structure:
        '''
        Fills the an OpenCL Structure (target) with the data required by the
        Monte Carlo simulator. See the :py:meth:`~Gk.cl_type` method
        for a detailed list of fields.

        Parameters
        ----------
        mc: McObject
            Simulator instance.
        target: cltypes.Structure
            Target OpenCL structure for packing.

        Returns
        -------
        target: cltypes.Structure
            Target structure received as an input argument or a new
            instance of ClGk if the input argument target is None.
        '''
        if target is None:
            target_type = self.fetch_cl_type(mc)
            target = target_type()

        target.g = self._g
        target.a = self._a
        target.inv_a = self._precalculated[0]
        target.a1 = self._precalculated[1]
        target.a2 = self._precalculated[2]

        return target

    def todict(self) -> dict:
        '''
        Export object to a dict.
        '''
        return {'g': self._g, 'a': self._a, 'type': self.__class__.__name__}

    def __str__(self):
        return 'Gk(g={}, a={})'.format(self._g, self._a)
