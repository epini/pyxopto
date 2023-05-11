from typing import Callable, Tuple

from xopto import pf
from xopto.materials import ri
from xopto.materials import density
from xopto.mcbase.mcutil import cache

import xopto.mcbase.mcpf

import numpy as np

DEFAULT_TEMPERATURE = 293.15


class Suspension:
    def __init__(
            self,
            pd: Callable[[float], float] or 'Suspension',
            particle_ri: float or Callable[[float, float], float] = None,
            medium_ri: float or Callable[[float, float], float] = None,
            particle_density: float or Callable[[float], float] = None,
            solid_content: float = 0.1, nd: int or None = 100):
        '''
        Suspension of spherical particles that follows the provided size
        distribution function.

        pd: Callable[[float], float] or Suspension
            Particle size distribution that takes diameter and returns
            probability. The object must implement raw_moment method
            that computes the requested statistical moment of the distribution.
            The object must also implement range method that returns a
            tuple with full range of size/diameter covered by the distribution
            as (dmin, dmax). 
            Use one of the distributions implemented in
            :py:mod:`xopto.pf.distribution`.
            If this parameter is a Suspension instance, a new copy is
            created, which inherits all the properties of the original
            suspension including the cache.
        particle_ri: float or Callable[[float, float], float]
            Refractive index of the suspended particles.
            A callable that takes wavelength and temperature or a fixed
            floating-point value that is independent of wavelength and
            temperature.
            Default implementation of the polystyrene refractive index
            is used by default.
        medium_ri: float or Callable[[float, float], float]
            Refractive index of the medium surrounding the suspended particles.
            A callable that takes wavelength and temperature or a fixed
            floating-point value that is independent of wavelength and
            temperature.
            Default implementation of the water refractive index
            is used by default.
        particle_density: float or Callable[[float], float]
            Density of the suspended particles (kg/m3).
            A callable that takes temperature or a fixed
            floating-point value that is independent of temperature.
            Default implementation of the polystyrene density
            is used by default.
        solid_content: float
            Solid content of the suspension given as a decimal
            number (e.g. 0.1 for 10%). The value represents mass
            volume fraction, e.g. mg/ml, which has to be divided by
            the density of the bulk material in order to obtain the
            volume fraction.
        nd: int or None
            If an integer, the number of nodes to use when integrating
            the Mie scattering phase functions. If None, adaptive step
            is used (slow).

        Note
        ----
        The scattering properties of the suspension can be adjusted through
        the :py:meth:`~Suspension.set_mus`, :py:meth:`~Suspension.set_musr`,
        :py:meth:`~Suspension.set_number_density` or
        :py:meth:`~Suspension.set_solid_content` methods.
        This class uses :py:class:`xopto.pf.MiePd` scattering phase function
        to make the required computations.
        '''
        if isinstance(pd, Suspension):
            obj = pd
            pd = obj._pd
            particle_ri = obj._particle_ri
            medium_ri = obj._medium_ri
            particle_density = obj._particle_density
            solid_content = obj.solid_content()
            nd = obj._nd
            self._pf_cache = obj._pf_cache
            self._mcpf_lut_cache = obj._mcpf_lut_cache
        else:
            self._pf_cache = cache.ObjCache()
            self._mcpf_lut_cache = cache.LutCache()

        if nd is not None:
            nd = int(nd)

        self._number_density = None
        self._nd = nd

        if particle_ri is None:
            particle_ri = ri.polystyrene.default

        if medium_ri is None:
            medium_ri = ri.water.default

        if particle_density is None:
            particle_density = density.polystyrene.default

        if isinstance(particle_ri, (float, int)):
            particle_ri_value = float(particle_ri)
            particle_ri = lambda w, t: particle_ri_value

        if isinstance(medium_ri, (float, int)):
            medium_ri_value = float(medium_ri)
            medium_ri = lambda w, t: medium_ri_value

        if isinstance(particle_density, (float, int)):
            particle_density_value = float(particle_density)
            particle_density = lambda t: particle_density_value

        self._particle_ri = particle_ri
        self._medium_ri = medium_ri
        self._particle_density = particle_density
        self._pd = pd

        # this will initialize self._number_density
        self.set_solid_content(solid_content)

    def set_musr(self, musr: float, wavelength: float,
                 temperature: float = 293.15):
        '''
        Set the scattering properties of the suspension by specifying the
        reduced scattering coefficient (1/m) at the given wavelength (m).

        Parameters
        ----------
        musr: float
            Reduced scattering coefficient (1/m) at the specified wavelength of
            light.
        wavelength: float
            Wavelength of light (m) at which reduced scattering coefficient is
            specified.
        temperature: float
            Suspension temperature (K).
        '''
        pf_obj = self.pf(wavelength, temperature)
        g, scs = pf_obj.g(1), pf_obj.scs()
        self._number_density = musr/(1.0 - g)/scs

    def set_mus(self, mus: float, wavelength: float,
                temperature: float = 293.15):
        '''
        Set the scattering properties of the suspension by specifying the
        scattering coefficient (1/m) at the given wavelength (m).

        Parameters
        ----------
        mus: float
            Scattering coefficient (1/m) at the specified wavelength of light.
        wavelength: float
            Wavelength of light (m) at which reduced scattering coefficient is
            specified.
        temperature: float
            Suspension temperature (K).
        '''
        self._number_density = mus/self.pf(wavelength, temperature).scs()

    def set_number_density(self, nd: float):
        '''
        Set the scattering properties of the suspension by specifying the
        number density of the particles.

        Parameters
        ----------
        nd: float
            Number density of particles (per cubic metre).
        '''
        self._number_density = nd

    def set_solid_content(self, sc: float, temperature: float = 293.15):
        '''
        Set the scattering properties of the suspension by specifying the
        solid content of the particles in  the suspension.

        Parameters
        ----------
        sc: float
            Solid content of the suspension given as a decimal
            number (e.g. 0.1 for 10%). The value represents mass
            volume fraction, e.g. mg/ml, which has to be divided by
            the density of the bulk material in order to obtain the
            volume fraction.
        temperature: float
            Suspension temperature (K).
        '''
        average_particle_volume = np.pi/6.0*self._pd.raw_moment(3)
        average_particle_weight = \
            average_particle_volume*self._particle_density(temperature)
        self._number_density = sc/average_particle_weight

    def mus(self, wavelength: float, temperature: float = 293.15) -> float:
        '''
        Computes the scattering coefficient of the suspension at
        the given wavelength and temperature.

        Parameters
        ----------
        wavelength: float
            Wavelength of light (m).
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        musr: float
            Scattering coefficient (1/m) of the suspension
            at the given wavelength and temperature.
        '''
        pf_obj = self.pf(wavelength, temperature)
        return self.number_density()*pf_obj.scs()

    def musr(self, wavelength: float, temperature: float = 293.15) -> float:
        '''
        Computes the reduced scattering coefficient of the suspension at
        the given wavelength and temperature.

        Parameters
        ----------
        wavelength: float
            Wavelength of light (m).
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        musr: float
            Reduced scattering coefficient (1/m) of the suspension
            at the given wavelength and temperature.
        '''
        g = self.g(wavelength, temperature)
        return self.mus(wavelength, temperature)*(1.0 - g)

    def number_density(self) -> float:
        '''
        Returns
        -------
        nd: float
            Number density of the particles (1/m3) in the suspension.
        '''
        return self._number_density

    def solid_content(self, temperature: float = 293.15) -> float:
        '''
        Computes and returns the solid content of suspension at the given
        temperature (K)

        Parameters
        ----------
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        sc: float
            Solid content of the suspension given as a decimal
            number (e.g. 0.1 for 10%). The value represents mass
            volume fraction, e.g. mg/ml, which has to be divided by
            the density of the bulk material in order to obtain the
            volume fraction.
        '''
        average_particle_volume = np.pi/6.0*self._pd.raw_moment(3)
        average_particle_weight = \
            average_particle_volume*self._particle_density(temperature)
        return self.number_density()*average_particle_weight

    def pf(self, wavelength: float, temperature: float = 293.15) -> pf.MiePd:
        '''
        Computes and returns an instance of the scattering phase function
        that describes the scattering of suspended particles at the given
        wavelength and temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light.
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        pf_obj: pf.MiePd
            Scattering phase function instance at the given wavelength
            and temperature.
        '''
        return self._pf_cache.get(
            pf.MiePd,
            self._particle_ri(wavelength, temperature),
            self._medium_ri(wavelength, temperature),
            wavelength,
            self._pd, self._pd.range, self._nd
        )

    def mcpf(self, wavelength: float, temperature: float = 293.15,
             nd: int or None = 100) \
            -> xopto.mcbase.mcpf.PfBase:
        '''
        Returns a Monte Carlo simulator-compatible scattering phase function
        instance at the given wavelength and temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light (m).
        temperature: float
            Suspension temperature (K).

        Returns
        -------
            Monte Carlo simulator-compatible scattering phase function
            instance at the given wavelength and temperature.
        '''
        return self._mcpf_lut_cache.get(
            pf.MiePd,
            (
                float(self._particle_ri(wavelength, temperature)),
                float(self._medium_ri(wavelength, temperature)),
                wavelength, self._pd, self._pd.range, self._nd
            )
        )

    def scs(self, wavelength: float, temperature: float = 293.15) -> float:
        '''
        Computes and returns the scattering cross section of the suspended
        particles at the given wavelength and temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light.
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        scs: float
            Scattering cross section (m2) of the suspended particles
            at the given wavelength and temperature.
        '''
        return self.pf(wavelength, temperature).scs()

    def g(self, wavelength: float, temperature: float = 293.15, n: int = 1):
        '''
        Computes and returns the specified Legendre moment of the scattering
        phase function that describes the scattering of the suspended particles
        at the given wavelength and temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light.
        temperature: float
            Suspension temperature (K).
        n: int
            Legendre moment (defaults to 1 - anisotropy of the scattering
            phase function).

        Returns
        -------
        scs: float
            The specified Legendre moment of the scattering
            phase function that describes the scattering of
            the suspended particles at the given wavelength and temperature.
        '''
        return self.pf(wavelength, temperature).g(n)

    def particle_ri(self, wavelength: float,
                    temperature: float = 293.15) -> float:
        '''
        Computes and returns the refractive index of suspended particles at
        the given wavelength and temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light.
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        ri: float
            Refractive index of the suspended particles at the given
            wavelength and temperature.
        '''
        return self._particle_ri(wavelength, temperature)

    def medium_ri(self, wavelength: float,
                  temperature: float = 293.15) -> float:
        '''
        Computes and returns the refractive index of medium that surrounds
        the suspended particles at the given wavelength and temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light.
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        ri: float
            Refractive index of the medium that surrounds the suspended
            particles at the given wavelength and temperature.
        '''
        return self._medium_ri(wavelength, temperature)

    def particle_density(self, temperature: float = 293.15) -> float:
        '''
        Computes and returns the density (kg/m3) of the suspended particles at
        the given temperature.

        Parameters
        -----------
        wavelength: float
            Wavelength of light.
        temperature: float
            Suspension temperature (K).

        Returns
        -------
        ri: float
            Density (kg/m3) of the suspended particles at the given temperature.
        '''
        return self._particle_density(temperature)

    def make_mus(self, mus: float, volume: float,
                 wavelength: float, temperature: float = 293.15) \
                    -> Tuple[float, 'Suspension']:
        '''
        Compute the volume that needs to be taken from this suspension to
        prepare a diluted suspension with target volume and target scattering
        coefficient at the given wavelength and temperature.

        Parameters
        ----------
        mus: float
            Target scattering coefficient of the diluted suspension.
        volume: float
            Volume of the target suspension.
        wavelength: float
            Wavelength of light (m).
        temperature: float
            temperature of the suspension (K).

        Returns
        -------
        required_volume: float
            The required volume of this suspension.
        diluted_suspension: Suspension
            Diluted suspension
        '''
        diluted_suspension = Suspension(self)
        diluted_suspension.set_mus(mus, wavelength, temperature)
        solid_mass = diluted_suspension.solid_content()*volume
        required_volume = solid_mass/self.solid_content()

        return required_volume, diluted_suspension

    def make_musr(self, musr: float, volume: float,
                  wavelength: float, temperature: float = 293.15) \
                    -> Tuple[float, 'Suspension']:
        '''
        Compute the volume that needs to be taken from this suspension to
        prepare a diluted suspension with target volume and target
        reduced scattering coefficient at the given wavelength and temperature.

        Parameters
        ----------
        musr: float
            Target reduced scattering coefficient of the diluted suspension.
        volume: float
            Volume of the target suspension.
        wavelength: float
            Wavelength of light (m).
        temperature: float
            temperature of the suspension (K).

        Returns
        -------
        required_volume: float
            The required volume of this suspension.
        diluted_suspension: Suspension
            Diluted suspension
        '''
        diluted_suspension = Suspension(self)
        diluted_suspension.set_musr(musr, wavelength, temperature)
        solid_mass = diluted_suspension.solid_content()*volume
        required_volume = solid_mass/self.solid_content()

        return required_volume, diluted_suspension
