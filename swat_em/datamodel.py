# -*- coding: utf-8 -*-
"""
Provides a central class for data 
"""
import json
import os
import fractions
import math
import copy
import string
import gzip
import gc
import numpy as np
from swat_em import analyse
from swat_em import report as rep
from swat_em import wdggenerator
from swat_em.config import config, get_phase_color
# from swat_em import plots


class datamodel:
    """
    Provides a central place for all data. All analysis functions are
    connect with this class.
    """

    file_format = 1
    machinedata_keys = ["Q", "p", "m", "phases", "wstep", "Qes"]
    results_keys = [
        "q",
        "nu_el",
        "Ei_el",
        "kw_el",
        "phaseangle_el",
        "nu_mech",
        "Ei_mech",
        "kw_mech",
        "phaseangle_mech",
        "valid",
        "error",
    ]

    def __init__(self):
        self.reset_data()
        self.reset_results()

    def __str__(self):
        txt = []
        txt.append("WINDING DATAMODEL")
        txt.append("=================")
        txt.append("")
        if self.results["kw_el"] != None:
            txt.append("Title: " + self.get_title())
            txt.append("Number of slots:  {}".format(self.get_num_slots()))
            txt.append("Number of poles:  {}".format(2 * self.get_num_polepairs()))
            txt.append("Number of phases: {}".format(self.get_num_phases()))
            txt.append("Number of layers: {}".format(self.get_num_layers()))
            txt.append("Coil span       : {}".format(self.get_coilspan()))

            txt.append("Number of slots per pole per phase: {}".format(self.get_q()))
            wf = [str(round(k, 3)) for k in self.get_fundamental_windingfactor()]
            txt.append("Fundamental winding factor: {}".format(", ".join(wf)))
        else:
            txt.append("-- NO WINDING DEFINED IN THIS MODEL --")
        return "\n".join(txt)

    def __eq__(self, other):
        ret = []
        ret.append(self.machinedata == other.machinedata)
        for rk in self.results_keys:
            if type(self.results[rk]) == type([]):  # lists are filled with numpy arrays
                ret.append(np.allclose(self.results[rk], other.results[rk]))
            else:
                ret.append(self.results[rk] == other.results[rk])
        return np.all(ret)

    def reset_data(self):
        """
        resets all data of the datamodel
        """
        self.title = ""
        self.notes = ""
        self.machinedata = {}
        for key in self.machinedata_keys:
            self.machinedata[key] = None
        self.set_turns(1)
        self.set_machinedata(Qes=0)
        self.generator_info = {}

    def reset_results(self):
        """
        Remove all existing results
        """
        self.results = {}
        for key in self.results_keys:
            self.results[key] = None

    def copy(self):
        """
        Returns a copy of the winding
        """
        return copy.deepcopy(self)

    def set_title(self, title):
        """
        Set the title of the winding 

        Parameters
        ----------
        title : string
                title
        """
        self.title = title

    def get_title(self):
        """
        Get the title of the winding 

        Returns
        ----------
        title : string
                title
        """
        if self.title == "":
            return "Untitled"
        else:
            return self.title

    def get_notes(self):
        """
        Get notes for the winding 

        Returns
        ----------
        notes : string
                Some notes
        """
        return self.notes

    def set_notes(self, notes):
        """
        Set additional notes for the winding 

        Parameters
        ----------
        notes :  string
                 Some notes
        """
        self.notes = notes

    def set_machinedata(self, Q=None, p=None, m=None, Qes=None):
        """
        setting the machine data 

        Parameters
        ----------
        Q :      integer
                 number of slots
        p :      integer
                 number of pole pairs
        m:       integer
                 number of phases
        """
        if Q:
            self.set_num_slots(int(Q))
        if p:
            self.set_num_polepairs(int(p))
        if m:
            self.set_num_phases(int(m))
        if Qes:
            self.set_num_empty_slots(int(Qes))

    def set_phases(self, S, turns=1, w=None):
        """
        setting the winding layout
        
        Parameters
        ----------
        S : list of lists
            winding layout for every phase, for example:
            S = [[1,-2], [3,-4], [5,-6]]. This means there are 3 phases
            with phase 1 in in slot 1 and in slot 2 with negativ winding direction. 
            For double layer windings there must be additional lists:
            S = [[[1, -4], [-3, 6]], [[3, -6], [-5, 2]], [[-2, 5], [4, -1]]]
            Hint: [[[first layer], [second layer]], ... ]
                     
        w : integer
            coil span (slots as unit)
        """
        if not hasattr(S[0][0], "__iter__"):
            for k in range(len(S)):
                S[k] = [S[k], []]
        if hasattr(turns, "__iter__"):
            if not hasattr(turns[0][0], "__iter__"):
                for k in range(len(turns)):
                    turns[k] = [turns[k], []]

        self.machinedata["phases"] = S
        self.set_turns(turns)
        self.set_machinedata(m=len(S))
        self.machinedata["phasenames"] = [
            string.ascii_uppercase[k] for k in range(len(S))
        ]
        if w:
            self.set_coilspan(w)

    def set_valid(self, valid, error, info=""):
        self.generator_info["valid"] = valid
        self.generator_info["error"] = error
        self.generator_info["info"] = info

    def genwdg(self, Q, P, m, layers, w=-1, turns=1, empty_slots=0, analyse=True):
        """
        Generates a winding layout and stores it in the datamodel

        Parameters
        ----------
        Q :      integer
                 number of slots
        P :      integer
                 number of poles
        m :      integer
                 number of phases
        w :      integer
                 coil span (1 for tooth coils)
        layers : integer
                 number of coil sides per slot    
        turns  : integer
                 number of turns per coil
        analyse : Bool
                  If False the generated winding doesn't get analysed
        empty_slots : integer
                    Defines the number of empty slots ("dead coil winding")
                    -1: Choose number of empty slots automatically (the smallest
                      possible number is choosen)
                    0: No empty slots
                    >0: Manual defined number of empty slots
        """

        wdglayout = wdggenerator.genwdg(Q, P, m, w, layers, empty_slots)
        if wdglayout is None:
            return
        self.set_machinedata(Q, int(P / 2), m, wdglayout["Qes"])

        self.set_phases(S=wdglayout["phases"], turns=turns, w=wdglayout["wstep"])
        self.set_valid(
            valid=wdglayout["valid"], error=wdglayout["error"], info=wdglayout["info"]
        )
        if analyse:
            self.analyse_wdg()

    def get_num_layers(self):
        """
        Returns the number of layers of the actual winding layout
        """
        l = 1
        for p in self.get_phases():
            if len(p[1]) > 0:
                l = 2
        return l

    def get_basic_characteristics(self):
        """
        Returns the basic charactericits of the winding as 
        dictionary and a html string
        """
        if not "basic_char" in self.results.keys():
            bc = analyse.get_basic_characteristics(
                self.get_num_slots(),
                2 * self.get_num_polepairs(),
                self.get_num_phases(),
                self.get_phases(),
                self.get_turns(),
                self.get_num_empty_slots(),
            )
            bc["r"] = self.get_radial_force_modes(
                num_modes=config["radial_force"]["num_modes"]
            )
            bc["sigma_d"] = self.get_double_linked_leakage()
            bc["t"] = self.get_periodicity_t()
            bc["NL"] = self.get_num_layers()
            self.results["basic_char"] = bc
        else:
            bc = self.results["basic_char"]

        dat = [
            ["Number of slots ", rep.italic("Q: "), str(self.get_num_slots())],
            [
                "Number of empty slots ",
                rep.italic("Qes: "),
                str(self.get_num_empty_slots()),
            ],
            ["Number of poles ", rep.italic("2p: "), str(2 * self.get_num_polepairs())],
            ["Number of phases ", rep.italic("m: "), str(self.get_num_phases())],
            ["slots per 2p per m ", rep.italic("q: "), str(bc["q"])],
            ["Number of layers ", rep.italic("NL"), str(self.get_num_layers())],
            ["coil span ", rep.italic("ws: "), str(self.get_coilspan())],
        ]

        for i, k in enumerate(bc["kw1"]):
            dat.append(
                [
                    "winding factor (m={}) ".format(i + 1),
                    rep.italic("kw1: "),
                    str(round(k, 3)),
                ]
            )
        dat.append(
            [
                "double linked leakage ",
                rep.italic("σ<sub>d: </sub>"),
                str(round(bc["sigma_d"], 3)),
            ]
        )
        dat.append(["lcm(Q, P) ", "", str(bc["lcmQP"])])
        dat.append(["periodic base winding ", rep.italic("t: "), str(bc["t"])])

        a_ = [str(i) for i in analyse.Divisors(bc["a"])]
        dat.append(["parallel connection ", rep.italic("a: "), ",".join(a_)])
        r_ = [str(i) for i in bc["r"]]
        dat.append(["radial force modes ", rep.italic("r: "), ",".join(r_) + ",.."])
        if bc["sym"]:  # and bc['a']:
            dat.append(["symmetric ", "", str(bc["sym"])])
        else:
            dat.append([rep.red("symmetric "), "", rep.red(str(bc["sym"]))])
        #  if 'valid' in self.generator_info.keys():
        #  if self.generator_info['valid']:
        #  dat.append(['valid ', '', 'True'])
        #  else:
        #  dat.append([rep.red('valid '), '', rep.red('False')])

        txt = rep.table(dat)
        if bc["error"]:
            txt.append(rep.red("error: " + str(bc["error"])))

        if len(self.notes) > 0:
            #  txt.append('<br><br>' + rep.bold(Notes) + ':<br>')
            txt.append(rep.bold("<br><br>Notes<br>"))
            txt.append(rep.italic(self.notes))

        txt = "".join(txt)
        return bc, txt

    def get_radial_force_modes(self, num_modes=None):
        """
        Returns the radial force modes caused by the winding.
        The results includes also the modes with a multiple of the 
        phase-number (which aren't there if the machine is star-connected). 

        Parameters
        ----------
        num_modes : integer
                    Max. number of modes. If not given the default value
                    from the config file is used

        Returns
        -------
        MMK: list
             radial force modes
        """
        if num_modes == None:
            num_modes = config["radial_force"]["num_modes"]
        if "MMK" not in self.results.keys():
            self._calc_MMK()
        return analyse.calc_radial_force_modes(
            self.results["MMK"]["MMK"], self.get_num_phases(), num_modes=num_modes
        )

    def get_num_series_turns(self):
        """
        Returns the number of turns in series per phase.
        If the number of coil sides per phase or number of turns per
        phase is not identically than a mean value of turns of all
        phases is returned.

        Returns
        -------
        w: number
           number of turns in series per phase
        """
        S2 = analyse._flatten(self.get_phases())
        turns2 = self.get_turns()
        if hasattr(turns2, "__iter__"):
            turns2 = analyse._flatten(turns2)
        if not hasattr(turns2, "__iter__"):  # constant number of turns
            w = 0
            for k in S2:
                w += len(k)
            w *= turns2
        else:  # variable number of turns
            w = 0
            for k1 in range(len(S2)):
                for k2 in range(len(S2[k1])):
                    w += S2[k1][k2] * turns2[k1][k2]
        w = w / 2 / self.get_num_phases()
        return w

    def get_MMF_harmonics(self, threshold=False):
        """
        Returns the harmonics of the MMF curve 
        
        Parameters
        ----------
        threshold: float
                   Relative threshold for cutting off small amplit>udes
                   0 < threshold <= 1.0
               
        Returns
        -------
        nu: 1D numpy array
            ordinal number (mechanical)
        Cnu: 1D numpy array
             amplitude corresponding to nu
        phase: 1D numpy array
               phaseangle of the harmonic corresponding to nu in
               range between -pi and +pi
        """
        if "MMK" not in self.results.keys():
            self._calc_MMK()
        nu = np.array(self.results["MMK"]["nu"])
        Cnu = np.abs(self.results["MMK"]["HA"])
        phase = np.angle(self.results["MMK"]["HA"])
        if threshold:
            idx = Cnu > np.max(Cnu) * threshold
            nu = nu[idx]
            Cnu = Cnu[idx]
            phase = phase[idx]
        return nu, Cnu, phase

    def get_double_linked_leakage(self):
        """
        Returns the coefficient of the double linkead leakage flux.
        This number is a measure of the harmonic content of the 
        MMF in the airgap caused by the winding. As higher the number
        as higher the harmonics.

        Returns
        -------
        sigma_d: float
                 coefficient of the double linkead leakage flux
        """
        nu, Cnu, _ = self.get_MMF_harmonics()
        if nu[0] == 0:
            nu = nu[1:]
            Cnu = Cnu[1:]
        p = self.get_num_polepairs()
        I = 1  # current for MMK
        w = self.get_num_series_turns()
        if w != 0:
            kw = Cnu * np.pi * nu / (3 * np.sqrt(2) * I * w)
            sigma_d = analyse.double_linked_leakage(kw, nu, p)
        else:
            sigma_d = -1
        return sigma_d

    def calc_num_basic_windings_t(self):
        """
        Calculates and returns the number of basic windings 't' for the actual
        winding layout

        Returns
        -------
        t: integer
           Periodicity for the winding layout
        """
        l, ls, lcol = self.get_layers()
        layers, Q = l.shape

        t = 1
        i = 2
        while i <= Q // 2:
            if Q % i == 0:
                length = Q // i
                is_t = True
                for k in range(i - 1):
                    if not np.all(
                        l[:, k * length : (k + 1) * length]
                        == l[:, (k + 1) * length : (k + 2) * length]
                    ):
                        is_t = False
                if is_t:
                    t = i
            i += 1
        return t

    def get_num_slots(self):
        """
        Returns the number of slots Q

        Returns
        -------
        Q: integer
           number of slots
        """
        return self.machinedata["Q"]

    def set_num_slots(self, Q):
        """
        Sets the number of slots Q 

        Parameters
        ----------
        Q : integer
            number of slots
        """
        self.machinedata["Q"] = Q

    def get_num_polepairs(self):
        """
        Returns the number of pole-pairs p

        Returns
        -------
        p: integer
           number of pole-pairs
        """
        return self.machinedata["p"]

    def set_num_polepairs(self, p):
        """
        Sets the number of pole pairs p 

        Parameters
        ----------
        p : integer
            number of pole pairs
        """
        self.machinedata["p"] = p

    def get_num_phases(self):
        """
        Returns the number of phases m 

        Returns
        -------
        m: integer
           number of phases
        """
        return self.machinedata["m"]

    def set_num_phases(self, m):
        """
        Sets the number of phases m 

        Parameters
        ----------
        m : integer
            number of phases
        """
        self.machinedata["m"] = m

    def get_coilspan(self):
        """
        Returns the coil span

        Returns
        -------
        w: integer
           coil span
        """
        return self.machinedata["wstep"]

    def set_coilspan(self, w):
        """
        Sets the coil span w

        Parameters
        ----------
        w : integer
            coil span
        """
        self.machinedata["wstep"] = w

    def set_num_empty_slots(self, Qes):
        self.machinedata["Qes"] = Qes

    def get_num_empty_slots(self):
        if self.machinedata["Qes"] is not None:
            return self.machinedata["Qes"]
        else:
            return 0

    def get_phases(self, flatten=False):
        """
        Returns the definition of the winding layout. For every phase
        there is a sublist which contains the slot number which are 
        allocated to the phase.
        phases

        phases[0] contains the slot numbers for the first phase
        phases[1] contains the slot numbers for the second phase
        phases[m-1] contains the slot numbers for the last phase

        Returns
        -------
        phases: list of lists
                winding layout
        """
        if flatten:
            return analyse._flatten(self.machinedata["phases"])
        else:
            return self.machinedata["phases"]

    def get_layers(self):
        """
        Returns the definition of the winding layout alternative to the
        'get_phases' function. For every layer (with the length of the
        number of slots) there is a sublist which contains the phase-number.
        
        layers[0][0] contains the phase number for first layer and first slot
        layers[0][1] contains the phase number for first layer and second slot
        layers[0][Q-1] contains the phase number for first layer and last slot
        layers[1][0] contains the phase number for second layer and first slot

        Returns
        -------
        layers:     numpy array 
                    winding layout
        slayers:    numpy array 
                    same as 'layers' but as string
        layers_col: numpy array 
                    phase colors
        """
        N = self.get_num_layers()
        Q = self.get_num_slots()
        layers = np.zeros([N, Q], dtype=int)
        layers_s = np.array(layers, dtype=str)
        layers_col = np.array(layers, dtype=str)
        layers_col[:] = "#FFFFFF"
        m = self.get_num_phases()
        for kl in range(N):
            for km in range(m):
                col = get_phase_color(km)
                for kcs in range(len(self.machinedata["phases"][km][kl])):
                    slot = self.machinedata["phases"][km][kl][kcs]
                    if slot > 0:
                        layers[kl, abs(slot) - 1] = km + 1
                        layers_s[kl, abs(slot) - 1] = "+" + str(km + 1)
                    elif slot < 0:
                        layers[kl, abs(slot) - 1] = -(km + 1)
                        layers_s[kl, abs(slot) - 1] = "-" + str(km + 1)
                    layers_col[kl, abs(slot) - 1] = col
        return layers, layers_s, layers_col

    def get_phasenames(self):
        """
        Returns the names of the phases as a series of characters
        'A', 'B', 'C', ... with length of the number of phases
        
        Returns
        -------
        phasenames: list
                    names of the phases

        Examples
        --------
        if there are m = 3 phases:
        >>> data.get_phasenames()
        ['A', 'B', 'C']
        """
        return self.machinedata["phasenames"]

    def get_windingfactor_el(self):
        """
        Returns the windings factors with respect to the electrical
        ordinal numbers
        
        Returns
        -------
        nu: numpy array
            ordinal numbers
        kw: 2D numpy array
            windings factors, (one column for each phase)
        """
        return np.array(self.results["nu_el"]), np.array(self.results["kw_el"])

    def get_windingfactor_el_by_nu(self, nu):
        """
        Returns the windings factors with respect to the electrical
        ordinal numbers for the given ordinal number
        
        Parameters
        ----------
        nu: integer
            ordinal number 
               
        Returns
        -------
        kw: 1D numpy array
            windings factors, (one column for each phase)
        """
        kw = analyse.calc_kw_by_nu(
            self.get_num_slots(),
            self.get_phases(),
            self.get_turns(),
            self.get_num_polepairs(),
            nu,
        )
        return kw

    def get_windingfactor_mech(self):
        """
        Returns the windings factors with respect to the mechanicl
        ordinal numbers
        
        Returns
        -------
        nu: numpy array
            ordinal numbers
        kw: 2D numpy array
            windings factors, (one column for each phase)
        """
        return np.array(self.results["nu_mech"]), np.array(self.results["kw_mech"])

    def get_windingfactor_mech_by_nu(self, nu):
        """
        Returns the windings factors with respect to the mechanical
        ordinal numbers for the given ordinal number
        
        Parameters
        ----------
        nu: integer
            ordinal number 
               
        Returns
        -------
        kw: 1D numpy array
            windings factors, (one column for each phase)
        """
        kw = analyse.calc_kw_by_nu(
            self.get_num_slots(), self.get_phases(), self.get_turns(), 1, nu
        )
        return kw

    def get_fundamental_windingfactor(self):
        """
        Returns the fundamental winding factors for each phase
        
        Returns
        -------
        kw: list
            windings factors, (one entry for each phase)
        """
        wf = self.get_windingfactor_el_by_nu(1)
        if wf is None:
            return None
        else:
            return [abs(kw) for kw in wf]
        #  return self.results['kw_el'][0]

    def get_turns(self):
        """
        Returns the number of turns. If all coil sides has the same
        number of turns, the return value is a scalar. If every coil
        side has an individual number of turns, the return value
        consists of lists with the same shape as the winding layout
        (phases)
        
        Returns
        -------
        turns: integer, float or list of lists
               number of turns 
        """
        return self.machinedata["turns"]

    def get_is_symmetric(self):
        """
        Returns the symmetry of the winding
        
        Returns
        -------
        is_symmetric: Boolean
                      True if the winding is symmetric
                      False if the winding is not symmetric 
        """
        return self.results["wdg_is_symmetric"]

    def get_periodicity_t(self):
        """
        Returns the periodicity of the winding. In most cases 
        t = gcd(Q,p). For user defined windings this may be different.
        
        Returns
        -------
        t: integer
           Number of periodic base windings
        """
        if "t" not in self.results:
            try:
                self.results["t"] = self.calc_num_basic_windings_t()
            except:
                self.results["t"] = -1
        return self.results["t"]

    def get_parallel_connections(self):
        """
        Returns all possible parallel connections of the winding.
        
        Returns
        -------
        a: list
           Number of possible parallel connections
        """
        return [i for i in analyse.Divisors(self.results["a"])]

    def get_lcmQP(self):
        """
        Returns the lowest common multiple of the slot number Q and
        the number of Poles. For permanent-magnet machines this value
        represents the first ordinal number for the cogging torque.
        
        Returns
        -------
        lcmQP: integer
               Lowest common multiple lcm(Q, P)
        """
        return self.results["lcmQP"]

    def set_turns(self, turns):
        """
        Sets the number of turns. If all coil sides has the same
        number of turns, the parameter should be an scalar. If every coil
        side has an individual number of turns, the parameter value
        have to consist of lists with the same shape as the winding layout
        (phases)
        
        Parameters
        ----------
        turns: integer, float or list of lists
               number of turns 
        """
        self.machinedata["turns"] = turns

    def get_q(self):
        """
        Returns the number of slots per pole per phase.

        Returns
        -------
        layers: Fraction
                number of slots per pole per phase
        """
        if "q" not in self.results.keys():
            q = fractions.Fraction(
                (self.get_num_slots() - self.get_num_empty_slots())
                / (self.get_num_phases() * 2 * self.get_num_polepairs())
            ).limit_denominator(100)
            self.results["q"] = q
        return self.results["q"]

    def _set_q(self, q):
        """
        Sets the number of slots per pole per phase q 

        Parameters
        ----------
        q : integer
            number of slots per pole per phase
        """
        self.results["q"] = q

    def analyse_wdg(self):
        """
        Do a detailled analyses of the winding. This includes
        winding factors, detection of periodicity and symmetry, 
        radial force modes and so on. Use the get_* functions for 
        getting the results.
        """
        self.reset_results()

        # number of slots per pole and phase
        q = fractions.Fraction(
            (self.get_num_slots() - self.get_num_empty_slots())
            / (self.get_num_phases() * 2 * self.get_num_polepairs())
        ).limit_denominator(100)
        self._set_q(q)

        # base winding
        #  self.results['t'] = math.gcd(self.machinedata['Q'], self.machinedata['p'])
        self.results["t"] = self.calc_num_basic_windings_t()

        # electrical winding factor
        a, b, c, d = analyse.calc_kw(
            self.machinedata["Q"],
            self.machinedata["phases"],
            self.machinedata["turns"],
            self.machinedata["p"],
            config["N_nu_el"],
            config,
        )
        self.results["nu_el"] = a
        self.results["Ei_el"] = b
        self.results["kw_el"] = c
        self.results["phaseangle_el"] = d

        # mechanical winding factor
        a, b, c, d = analyse.calc_kw(
            self.machinedata["Q"],
            self.machinedata["phases"],
            self.machinedata["turns"],
            1.0,
            config["N_nu_mech"],
            config,
        )
        self.results["nu_mech"] = a
        self.results["Ei_mech"] = b
        self.results["kw_mech"] = c
        self.results["phaseangle_mech"] = d

        # winding symmetric?
        self.results["wdg_is_symmetric"] = analyse.wdg_is_symmetric(
            self.results["Ei_el"], self.machinedata["m"]
        )

        # periodicity of the winding (radial force, parallel connection)?
        self.results["wdg_periodic"] = analyse.wdg_get_periodic(
            self.results["Ei_el"], self.machinedata["phases"]
        )

        # MMK
        if "MMK" not in self.results.keys():
            self._calc_MMK()

        bc, bc_txt = self.get_basic_characteristics()
        self.results["basic_char"] = bc
        self.results["t"] = bc["t"]
        self.results["a"] = bc["a"]
        self.results["lcmQP"] = bc["lcmQP"]

    def _calc_MMK(self):
        phi, MMK, theta = analyse.calc_MMK(
            self.get_num_slots(),
            self.get_num_phases(),
            self.get_phases(),
            self.get_turns(),
            N=config["num_MMF_points"],
        )
        HA = analyse.DFT(MMK[:-1])
        nu = list(range(len(HA)))

        self.results["MMK"] = {}
        self.results["MMK"]["MMK"] = MMK
        self.results["MMK"]["phi"] = phi
        self.results["MMK"]["theta"] = theta
        self.results["MMK"]["nu"] = nu
        self.results["MMK"]["HA"] = HA

    # def plot_layout(self, filename, res=None, show=False):
    #     """
    #     Generates a figure of the winding layout
        
    #     Parameters
    #     -------
    #     filename: string
    #               file-name with extension to save the figure
    #     res: list 
    #          Resolution for the figure in pixes for x and y direction
    #          example: res = [800, 600]
    #     show: Bool
    #           If true the window pops up for interactive usage
    #     """
    #     if res == None:
    #         res = config["plt"]["res"]
    #     plt = plots._slot_plot(None, None, self)
    #     plt.plot_slots(self.get_num_slots())
    #     plt.plot(self, show=show)
    #     plt.save(fname=filename, res=res)

    # def plot_overhang(self, filename, res=None, show=False, optimize_overhang=False):
    #     """
    #     Generates a figure of the winding layout
        
    #     Parameters
    #     -------
    #     filename: string
    #               file-name with extension to save the figure
    #     res: list 
    #          Resolution for the figure in pixes for x and y direction
    #          example: res = [800, 600]
    #     show: Bool
    #           If true the window pops up for interactive usage
    #     optimize_overhang: Bool
    #           If true swat-em tries to identify shorter winding overhangs
    #     """
    #     if res == None:
    #         res = config["plt"]["res"]
    #     plt = plots._overhang_plot(None, None, self)
    #     plt.plot(show=show, optimize_overhang=optimize_overhang)
    #     plt.save(fname=filename, res=res)

    # def plot_star(self, filename, res=None, ForceX=True, show=False):
    #     """
    #     Generates a figure of the star voltage phasors
        
    #     Parameters
    #     -------
    #     filename: string
    #               file-name with extension to save the figure
    #     res: list 
    #          Resolution for the figure in pixes for x and y direction
    #          example: res = [800, 600]
    #     ForceX: Bool
    #             If true the voltage phasors are rotated in such way, that
    #             the resulting phasor of the first phase matches the 
    #             x-axis
    #     show: Bool
    #           If true the window pops up for interactive usage
    #     """
    #     if res == None:
    #         res = config["plt"]["res"]
    #     plt = plots._slot_star(None, None, self, None)
    #     plt.plot(self, harmonic_idx=0, ForceX=ForceX, show=show)
    #     plt.save(fname=filename, res=res)

    # def plot_windingfactor(self, filename, res=None, mechanical=True, show=False):
    #     """
    #     Generates a figure of the winding layout
        
    #     Parameters
    #     -------
    #     filename: string
    #               file-name with extension to save the figure
    #     m: list 
    #          Resolution for the figure in pixes for x and y direction
    #          example: res = [800, 600]
    #     mechanical: Bool
    #                 If true the winding factor is plotted with respect to the
    #                 mechanical ordinal numbers. If false the electrical 
    #                 ordinal numbers are used
    #     show: Bool
    #           If true the window pops up for interactive usage
    #     """
    #     if res == None:
    #         res = config["plt"]["res"]
    #     plt = plots._windingfactor(None, None, self, None)
    #     plt.plot(self, mechanical=mechanical, show=show)
    #     plt.save(fname=filename, res=res)

    # def plot_MMK(self, filename, res=None, phase=0, show=False):
    #     """
    #     Generates a figure of the winding layout
        
    #     Parameters
    #     -------
    #     filename: string
    #               file-name with extension to save the figure
    #     res: list 
    #          Resolution for the figure in pixes for x and y direction
    #          example: res = [800, 600]
    #     phase: float
    #            phase angle for the current system in electical degree
    #            in the range 0..360°
    #     show: Bool
    #           If true the window pops up for interactive usage
    #     """
    #     if res == None:
    #         res = config["plt"]["res"]
    #     plt = plots._mmk(None, None, self, None)
    #     plt.plot(self, phase=phase, show=show)
    #     plt.save(fname=filename, res=res)

    # def plot_polar_layout(
    #     self, filename, res=None, optimize_overhang=False, draw_poles=False, show=False
    # ):
    #     """
    #     Generates a figure of the winding layout
        
    #     Parameters
    #     -------
    #     filename: string
    #               file-name with extension to save the figure
    #     res: list 
    #          Resolution for the figure in pixes for x and y direction
    #          example: res = [800, 600]
    #     optimize_overhang: Bool
    #           If true swat-em tries to identify shorter winding overhangs
    #     draw_poles: Bool
    #           If true the poles of the rotor are drawn
    #     show: Bool
    #           If true the window pops up for interactive usage
    #     """
    #     if res == None:
    #         res = config["plt"]["res"]
    #     plt = plots._polar_layout_plot(None, None, self)
    #     plt.plot(
    #         self, show=show, optimize_overhang=optimize_overhang, draw_poles=draw_poles
    #     )
    #     plt.save(fname=filename, res=res)

    def save_to_file(self, fname):
        """
        Saves the data to file. 

        Parameters
        ----------
        fname :  string
                 file name
        """
        save_models_to_file(self, fname)

    def load_from_file(self, fname, idx_in_file=0):
        """
        Load data from file. 

        Parameters
        ----------
        fname :  string
                 file name
        """
        data = load_models_from_file(fname)
        if idx_in_file > len(data):
            raise Exception(
                "defined index in greater than the available number of models in the *.wdg file"
            )
        else:
            data = data[idx_in_file]
            self.machinedata = data.machinedata
            self.results = data.results

    def export_xlsx(self, fname):
        """
        Export the results to Excel xlsx file. 

        Parameters
        ----------
        fname :  string
                 file name
        """
        rep.export_xlsx(fname, self)

    def export_text_report(self, fname):
        """
        Export winding report as a text file. 

        Parameters
        ----------
        fname :  string
                 file name
        """
        txt_rep = rep.TextReport(self)
        txt_rep.save(fname)

    def export_html_report(self, fname=None):
        """
        Returns a winding report. 
        
        Parameters
        ----------
        fname :  string
                 file name for html file. If not given a file is created
                 in the temp dir of the file system (the file name ist
                 returned by this function)
                 
        Returns
        -------
        filnename : string
                    The file name of the html-file which is stored in tmp directory
        """
        html_rep = rep.HtmlReport(self)
        return html_rep.create(fname)

    def get_text_report(self):
        """
        Returns a winding report. 

        Return
        ----------
        report :  string
                  Report
        """
        txt_rep = rep.TextReport(self)
        return txt_rep.get_report()

    def get_wdg_overhang(self, optimize_overhang=False):
        """
        Returns the winding overhang (connection of the coil sides).

        Parameters
        ----------
        optimize_overhang : Bool 
                            Optimize for short winding connection (experimental!)
                 
        Returns
        -------
        return : list 
                 Winding connections for all phases, len = num_phases,
                 format: [[(from_slot, to_slot), stepwidth, direction, (from_layer, to_layer)], [(), ()], ...]
                 from_to_slot: tuple of (from_slot (positive coil side), to_slot (negative coil side))
                 stepwidth: distance between from_slot to to_slot
                 direction: winding direction (1: from left to right, -1: from right to left)
                 layer: tuple of the layer of 'from_slot' and 'to_slot' 
        """
        S = self.get_phases()
        Q = self.get_num_slots()
        w = self.get_coilspan()
        num_layers = self.get_num_layers()

        # TODO: Test if wdg_overhang is already calculated

        ovh = analyse.create_wdg_overhang(S, Q, num_layers)
        if optimize_overhang:
            head = ovh.get_overhang(w=None)
        else:
            head = ovh.get_overhang(w=w)

        return head


class project:
    """
    Provides all data-objects (all winding in workspace)
    """

    file_format = 2

    def __init__(self):
        self.models = []
        self.filename = None
        self.undo_state = []
        self.redo_state = []
        self._is_saved = False

    def get_save_state(self):
        return self._is_saved

    def set_save_state(self, state):
        self._is_saved = state

    def save_undo_state(self):
        """saves the actual state of the models for undo function"""
        self.undo_state.append(copy.deepcopy([self.models, self._is_saved]))
        self.set_save_state(False)

    def save_redo_state(self):
        """saves the actual state of the models for redo function"""
        self.redo_state.append(copy.deepcopy([self.models, self._is_saved]))

    def reset_undo_state(self):
        """delete all existings undo state saves - no undo possible any more"""
        self.undo_state = []

    def reset_redo_state(self):
        """delete all existings redo state saves - no redo possible any more"""
        self.redo_state = []

    def reset_save_state(self):
        """set the save state to False for all redo and undo actions"""
        for k in range(len(self.undo_state)):
            self.undo_state[k][1] = False
        for k in range(len(self.redo_state)):
            self.redo_state[k][1] = False

    def get_num_undo_state(self):
        """return the number of undo state saves = number of possible undo opserations"""
        return len(self.undo_state)

    def get_num_redo_state(self):
        """return the number of redo state saves = number of possible redo opserations"""
        return len(self.redo_state)

    def undo(self):
        """restores the last state"""
        if self.get_num_undo_state() > 0:
            self.models, self._is_saved = self.undo_state.pop(-1)
            gc.collect()  # force to free memory

    def redo(self):
        """restores the last state"""
        if self.get_num_redo_state() > 0:
            self.models, self._is_saved = self.redo_state.pop(-1)
            gc.collect()  # force to free memory

    def set_filename(self, filename):
        """saves the filename if a the data is load from file or
        stored to a file"""
        self.filename = filename

    def get_filename(self):
        """returns the *.wdg filename if the project ist saved.
        Otherwise None is returned"""
        return self.filename

    def gen_model_name(self):
        """
        creates an unique title for a model
        """
        titles = [data.title for data in self.models]
        i = 0
        while True:
            name = "untitled" + str(i)
            if name not in titles:
                return name
            i += 1

    def add_model(self, data):
        """
        adds 'data' model to project. Generates a unique title if there
        is no title in 'data'
        """
        if data.title == "":
            name = self.gen_model_name()
            data.set_title(name)
        self.models.append(data)

    def get_titles(self):
        """returns the title of all models"""
        return [data.title for data in self.models]

    def get_num_models(self):
        """returns the number of models in this project"""
        return len(self.models)

    def get_model_by_index(self, idx):
        """returns the model with the index 'idx' """
        return self.models[idx]

    def delete_model_by_index(self, idx):
        """deletes the model with the index 'idx' """
        del self.models[idx]

    def move_model(self, idx_from, idx_to):
        mod = self.models.pop(idx_from)
        self.models.insert(idx_to, mod)

    def clone_by_index(self, idx):
        """duplicates the model with the index 'idx' """
        data = copy.deepcopy(self.models[idx])
        data.set_title(data.get_title() + "_copy")
        self.add_model(data)

    def rename_by_index(self, idx, newname):
        """change the title of the model with the index 'idx' 
        with name 'newname' """
        self.models[idx].set_title(newname)

    def replace_model_by_index(self, newmodel, idx):
        """replaces the model of index 'idx' with 'newmodel' """
        self.models[idx] = newmodel

    def analyse_all_models(self):
        """analyse/recalculate all existing models"""
        for m in self.models:
            m.analyse_wdg()

    def save_to_file(self, fname):
        """
        Saves the data to file. 

        Parameters
        ----------
                 
        fname :  string
                 file name
        """
        save_models_to_file(self.models, fname, file_format=self.file_format)
        self.reset_save_state()
        self.set_save_state(True)

    def load_from_file(self, fname):
        """
        Load data from file. 

        Parameters
        ----------
        fname :  string
                 file name
        """
        models = load_models_from_file(fname)
        if len(models) > 0:
            self.models = []
            for m in models:
                self.add_model(m)
            self.set_filename(fname)
            self.reset_undo_state()
            self.reset_redo_state()
            self.reset_save_state()
            self.set_save_state(True)


def save_models_to_file(models, fname, file_format=2):
    """
    Saves winding models to file. 
    The data is stored as a json file.

    Parameters
    ----------
    models:  datamodel object or list of datamodel objects
             models to save
             
    fname :  string
             file name
    """
    if not hasattr(models, "__iter__"):
        models = [models]
    M = {}
    M["file_format"] = file_format
    M["models"] = []
    for data in models:
        N = {}
        N["machinedata"] = data.machinedata
        if type(N["machinedata"]["wstep"]) == type(fractions.Fraction()):
            N["machinedata"]["wstep"] = str(N["machinedata"]["wstep"])
        N["title"] = data.title
        N["notes"] = data.notes
        M["models"].append(N)

    # save as ASCII file
    with open(fname, "w") as f:
        json.dump(M, f, indent=2)


def load_models_from_file(fname):
    """
    Load winding models from file. 

    Parameters
    ----------
    fname :  string
             file name
    """
    try:
        if os.path.isfile(fname):
            with open(fname) as f:
                M = json.load(f)
    except:
        # file_format 1 is saved compressed
        import gzip

        with gzip.GzipFile(fname) as f:  # gzip
            s = f.read()  # bytes
            s = s.decode("utf-8")  # string
            M = json.loads(s)  # data

    if M["file_format"] == 1:
        models = []
        data = datamodel()
        data.machinedata = M["machinedata"]
        if "turns" not in data.machinedata.keys():
            data.machinedata["turns"] = 1
        data.analyse_wdg()
        models = [data]

    elif M["file_format"] == 2:
        models = []
        for m in M["models"]:
            data = datamodel()
            for key, value in m["machinedata"].items():
                data.machinedata[key] = value
            if type(data.get_coilspan()) == type(""):
                data.set_coilspan(fractions.Fraction(data.get_coilspan()))
            data.set_title(m["title"])
            data.set_notes(m["notes"])
            data.analyse_wdg()
            models.append(data)

    return models
