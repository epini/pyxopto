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

from typing import List

from xopto.mcvox import mcobject
from xopto.mcvox import cltypes
from xopto.mcvox import mcpf


class Material(mcobject.McObject):
    '''
    Class that represents a single material.
    '''

    def cl_type(self, mc: mcobject.McObject) -> cltypes.Structure:
        '''
        Returns a structure data type that is used to represent one material
        instance in the OpenCL kernel of the Monte Carlo simulator.

        Parameters
        ----------
        mc: mcobject.McObject
            Monte Carlo simulator instance.

        Returns
        -------
        opencl_t: ClMaterial
            OpenCL Structure that represents a material. 
        '''
        T = mc.types
        class ClMaterial(cltypes.Structure):
            _fields_ = [
                ('n', T.mc_fp_t),
                ('mus', T.mc_fp_t),
                ('mua', T.mc_fp_t),
                ('inv_mut', T.mc_fp_t),
                ('mua_inv_mut', T.mc_fp_t),
                ('pf', self.pf.fetch_cl_type(mc))
            ]

        return ClMaterial

    def cl_declaration(self, mc: mcobject.McObject) -> str:
        '''
        Structure that defines material in the Monte Carlo simulator and the
        related API calls. This is a minimal implementation. All the field
        are required!
        '''
        return '\n'.join((
            self.pf.fetch_cl_declaration(mc),
            '',
            'struct MC_STRUCT_ATTRIBUTES McMaterial {',
            '	mc_fp_t n;           /**< @brief Refractive index. */',
            '	mc_fp_t mus;         /**< @brief Scattering coefficient. */',
            '	mc_fp_t mua;         /**< @brief Absorption coefficient. */',
            '	mc_fp_t inv_mut;     /**< @brief Precalculated 1/mua. */',
            '	mc_fp_t mua_inv_mut; /**< @brief Precalculated mua/(mua + mut). */',
            '	McPf pf;             /**< @brief Custom phase function parameters. */',
            '};'
            '',
            '/**',
            ' * @brief Evaluates to the material refractive index.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' */',
            ' #define mc_material_n(pmaterial) ((pmaterial)->n)',
            '',
            '/**',
            ' * @brief Evaluates to the material reduced scattering coefficient.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' * @param[in] pdir Propagation direction vector.',
            ' */',
            '#define mc_material_mus(pmaterial, pdir) ((pmaterial)->mus)',
            '',
            '/**',
            ' * @brief Evaluates to the material absorption coefficient.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' * @param[in] pdir Propagation direction vector.',
            ' */',
            '#define mc_material_mua(pmaterial, pdir) ((pmaterial)->mua)',
            '',
            '/**',
            ' * @brief Evaluates to the inverse of the material absorption coefficient.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' * @param[in] pdir Propagation direction vector.',
            ' */',
            '#define mc_material_inv_mua(pmaterial, pdir) \\',
            '	(((pmaterial)->mua > FP_0) ? \\',
            '	mc_fdiv(FP_1, (pmaterial)->mua) : FP_INF)',
            '',
            '/**',
            ' * @brief Evaluates to the total attenuation coefficient, i.e. sum of the',
            ' *		  material absorption and scattering coefficients.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' * @param[in] pdir Propagation direction vector.',
            ' */',
            '#define mc_material_mut(pmaterial, pdir) ((pmaterial)->mua + (pmaterial)->mus)',
            '',
            '/**',
            ' * @brief Evaluates to the reciprocal of the total attenuation coefficient, i.e.',
            ' *		  reciprocal of the sum of the material absorption and scattering coefficients.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' * @param[in] pdir Propagation direction vector.',
            ' */',
            '#define mc_material_inv_mut(pmaterial, pdir) ((pmaterial)->inv_mut)',
            '',
            '/**',
            ' * @brief Evaluates to the absorption coefficient multiplied by the reciprocal',
            ' *			of the total attenuation coefficient.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' * @param[in] pdir Propagation direction vector.',
            ' */',
            '#define mc_material_mua_inv_mut(pmaterial, pdir) ((pmaterial)->mua_inv_mut)',
            '',
            '/**',
            ' * @brief Evaluates to the scattering phase function of the material.',
            ' * @param[in] pmaterial Pointer to a material object.',
            ' */',
            '#define mc_material_pf(pmaterial) (&((pmaterial)->pf))',
        ))

    def cl_options(self, mc: mcobject.McObject) -> str:
        '''
        OpenCL options of the Material type.
        '''
        return self.pf.fetch_cl_options(mc)

    def cl_implementation(self, mc: mcobject.McObject) -> str:
        '''
        OpenCL implementation of the Material type.
        '''
        return '\n'.join((
            self.pf.fetch_cl_implementation(mc),
            '',
            '#if MC_ENABLE_DEBUG || defined(__DOXYGEN__)',
            'void dbg_print_material(__mc_material_mem McMaterial const *material){',
            '	dbg_print("McMaterial:");',
            '	dbg_print_float(INDENT "n:", material->n);',
            '	dbg_print_float(INDENT "mus:", material->mus);',
            '	dbg_print_float(INDENT "mua:", material->mua);',
            '	dbg_print_float(INDENT "inv_mut:", material->inv_mut);',
            '	dbg_print_float(INDENT "mua_inv_mut:", material->mua_inv_mut);',
            '	McPf const dbg_pf = material->pf;',
            '	dbg_print_pf(&dbg_pf);',
            '};',
            '#endif',
        ))

    def __init__(self, n: float, mua: float, mus: float, pf: mcpf.PfBase):
        '''
        Material object constructor.

        Parameters
        ----------
        n: float
            Index of refraction.
        mua: float
            Absorption coefficient (1/m).
        mus: float
            Scattering (NOT reduced) coefficient (1/m).
        pf: mcpf.PfBase
            Phase function object.


        The physical properties of the material can be read or changed through
        the member properties:

            - n: float - 
              Index of refraction.
            - mua: float - 
              Absorption coefficient (1/m).
            - mus: float - 
              Scattering (NOT reduced) coefficient (1/m).
            - pf: mcpf.PfBase -
              Scattering phase function object that is derived from PhBase class.
        '''
        self._n = float(n)
        self._mua = float(mua)
        self._mus = float(mus)
        self._pf = pf

    def _set_n(self, n: float):
        self._n = float(n)
    def _get_n(self) -> float:
        return self._n
    n = property(_get_n, _set_n, None, 'Refractive index.')

    def _set_mua(self, mua: float):
        self._mua = float(mua)
    def _get_mua(self) -> float:
        return self._mua
    mua = property(_get_mua, _set_mua, None, 'Absorption coefficient (1/m).')

    def _set_mus(self, mus: float):
        self._mus = float(mus)
    def _get_mus(self) -> float:
        return self._mus
    mus = property(_get_mus, _set_mus, None, 'Scattering coefficient (1/m).')

    def _get_pf(self) -> mcpf.PfBase:
        return self._pf
    def _set_pf(self, pf: mcpf.PfBase):
        if type(self._pf) != type(pf):
            raise ValueError('The scattering phase function type '\
                             'must not change!')
        self._pf = pf
    pf = property(_get_pf, _set_pf, None, 'Phase function object.')

    def todict(self) -> dict:
        '''
        Export object to a dict.
        '''
        return {'n':self._n, 'mua':self._mua, 'mus':self._mus,
                'pf':self._pf.todict(), 'type':'Material'}

    @classmethod
    def fromdict(cls, data: dict) -> 'Material':
        '''
        Create a new object from dict. The dict keys must match
        the parameter names defined by the constructor.
        '''
        data_ = dict(data)
        t = data_.pop('type')
        if t != 'Material':
            raise ValueError('Cannot create a Material instance from the data!')
        pf_data = data_.pop('pf')
        if not hasattr(mcpf, pf_data['type']):
            raise TypeError('Scattering phase function "{}" '
                            'not implemented'.format(pf_data['type']))
        pf_type = getattr(mcpf, pf_data['type'])
        return cls(pf=pf_type.fromdict(pf_data), **data_)

    def __str__(self):
        return 'Material(n={}, mua={}, mus={}, pf={})'.format(
            self._n, self._mua, self._mus, self._pf)

    def __repr__(self):
        return '{:s} # id 0x{:>08X}.'.format(self.__str__(), id(self))


class Materials(mcobject.McObject):
    '''
    Class that represents all materials used in the simulator core.

    Note
    ----
    The first material of the stack describes the medium that surrounds the
    sample. Therefore, at least one material must be always specified.
    '''
    def __init__(self, materials: List[Material] or 'Materials'):
        '''
        Constructs a managed list of sample materials.

        Note
        ----
        The first material in the list represents the medium that surrounds
        the sample.

        Note that all materials must use the same scattering phase function
        model.

        Parameters
        ----------
        materials: List[Material] or Materials
            A list of sample materials. At least 1 material is required!
        '''
        self._pf_type = None

        if isinstance(materials, Materials):
            self._materials = materials.tolist()
            self._pf_type = type(self._materials[0].pf)
        else:
            self._materials = list(materials)
            self.check()

    def check(self):
        '''
        Check if the materials are consistent and using the same
        scattering phase function model.
        Raises exception on error.
        '''
        if len(self._materials) < 1:
                ValueError('At least one material is required, '
                           'but got an empty list!')

        if self._pf_type is None:
            self._pf_type = type(self._materials[0].pf)

        for material in self._materials:
            if not isinstance(material, Material):
                raise TypeError('All materials must be instances of Material '
                                'but found {:s}!'.format(type(material).__name__))
            if type(material.pf) != self._pf_type:
                raise TypeError(
                    'All the materials must use the same scattering phase '
                    'function model! Found {} and {}!'.format(
                        self._pf_type.__name__, type(material.pf).__name__))

    def _get_material_type(self):
        return type(self._materials[0])
    material_type = property(_get_material_type, None, None,
                             'Data type that represents a material.')

    def material(self, index: int) -> Material:
        '''
        Returns the material at the specified index. Note that the first
        material (index 0) represents the medium that surrounds the sample.
        '''
        return self._materials[index]

    def cl_options(self, mc: mcobject.McObject) -> str:
        '''
        OpenCL options of the scattering phase function.
        '''
        return self._materials[0].fetch_cl_options(mc)

    def cl_declaration(self, mc: mcobject.McObject) -> str:
        '''
        OpenCL declarations of the scattering phase function.
        '''
        return self._materials[0].fetch_cl_declaration(mc)

    def cl_implementation(self, mc: mcobject.McObject) -> str:
        '''
        OpenCL implementation of the scattering phase function.
        '''
        return self._materials[0].fetch_cl_implementation(mc)

    def cl_type(self, mc: mcobject.McObject) -> cltypes.Array:
        '''
        Returns an OpenCL array of ClMaterial structures that is used to
        represent one instance of a material stack.

        Parameters
        ----------
        mc: mcobject.McObject
            Monte Carlo simulator instance.

        Returns
        ------- 
        clarray: cltypes.Structure*len(self)
            Array of ClMaterial.
        '''
        return self._materials[0].fetch_cl_type(mc)*len(self._materials)

    def cl_pack(self, mc: mcobject.McObject, target: cltypes.Array = None) \
            -> cltypes.Array:
        '''
        Pack the materials into an OpenCL data type. The OpenCL data
        type is returned by the :py:meth:`Materials.cl_type` method.

        Parameters
        ----------
        mc: mcobject.McObject
            Monte Carlo simulator instance.
        target: cltypes.Structure*len(self)
            A structure representing an array of Materials.

        Returns
        -------
        materials: cltypes.Array
            Filled array of ctypes structures received as an input argument
            or a new instance if the input argument target is None.
        '''

        num_materials = len(self._materials)

        if target is None or len(target) != num_materials:
            target_type = self.fetch_cl_type(mc)
            target = target_type()

        for index, material in enumerate(self._materials):

            mut = material.mua + material.mus

            if mut > 0.0:
                inv_mut = 1.0/mut
            else:
                inv_mut = float('inf')

            if material.mus == 0.0:
                mua_inv_mut = 1.0
            else:
                mua_inv_mut = material.mua*inv_mut

            target[index].n = material.n
            target[index].mua = material.mua
            target[index].mus = material.mus
            target[index].inv_mut = inv_mut
            target[index].mua_inv_mut = mua_inv_mut

            material.pf.cl_pack(mc, target[index].pf)

        return target

    def __getitem__(self, what):
        return self._materials[what]

    def __setitem__(self, what, value):
        self._materials[what] = value

    def todict(self) -> dict:
        '''
        Export object to a dict.
        '''
        return {
            'type': 'Materials',
            'materials': [material.todict() for material in self._materials] 
        }

    @classmethod
    def fromdict(cls, data: dict) -> 'Materials':
        '''
        Create a new instance of :py:class:`Materials` from a dict.

        Parameters
        ----------
        data: dict
            A dict with instance data.

        Returns
        -------
        instance: Materials
            A new instance of :py:class:`Materials`.
        '''
        data_ = dict(data)
        type_name = data_.pop('type')
        if type_name != cls.__name__:
            raise TypeError('Expected data of instance Materials '
                            'but got "{}"!'.format(type_name))
        materials = data_.pop('materials')
        return Materials(
            [Material.fromdict(material) for material in materials],
            **data_
        )

    def __len__(self):
        return len(self._materials)

    def __str__(self):
        items = []
        if len(self) > 10:
            for index, material in enumerate(self._materials[:7]):
                item = str(material)
                if index == 0:
                    item += ", # surrounding medium"
                items.append(item)
            return 'Materials([\n   {}\n   ...\n   ...\n   {}\n])'.format(
                ',\n   '.join(items), str(self._materials[-1]))
        else:
            for index, material in enumerate(self._materials):
                item = str(material)
                if index == 0:
                    item += ", # surrounding medium"
                items.append(item)
            return 'Materials([\n   {}\n])'.format(',\n   '.join(items))

    def tolist(self) -> List[Material]:
        '''
        Return the list of materials.

        Returns
        -------
        materials: List[Material]
            List of materials.
        '''
        return self._materials

    def __repr__(self):
        return self.__str__() + ' # id 0x{:>08X}.'.format(id(self))
