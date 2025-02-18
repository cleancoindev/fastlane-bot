"""
optimization library -- Simple Optimizer module [final optimizer class]


The simple optimizer uses a marginal price method in one dimension to find the optimal
solution. It is a predecessor to the marginal price optimizer, and is kept for reference;
however, it is at this stage deprecated and will not longer be updated; use the marginal
price optimizer instead

(c) Copyright Bprotocol foundation 2023. 
Licensed under MIT

This module is still subject to active research, and comments and suggestions are welcome. 
The corresponding author is Stefan Loesch <stefan@bancor.network>
"""
__VERSION__ = "5.0"
__DATE__ = "26/Jul/2023"

from dataclasses import dataclass, field, fields, asdict, astuple, InitVar
#import pandas as pd
import numpy as np

import time
# import math
# import numbers
# import pickle
from ..cpc import ConstantProductCurve as CPC, CPCInverter, CPCContainer
#from sys import float_info

from .dcbase import DCBase
from .base import OptimizerBase
from .cpcarboptimizer import CPCArbOptimizer

class SimpleOptimizer(CPCArbOptimizer):
    """
    implements the simple (marginal price) optimization method
    
    NOTE: this class is now deprecated; user marginal price optimizer instead
    """
    __VERSION__ = __VERSION__
    __DATE__ = __DATE__
    
    @property
    def kind(self):
        return "simple"
    
    @dataclass
    class SimpleOptimizerResult(OptimizerBase.OptimizerResult):
        """
        results of the simple optimizer

        :curves:            list of curves used in the optimization, possibly wrapped in CPCInverter objects*
        :dxdyfromp_vec_f:   vector of tuples (dx, dy), as a function of p
        :dxdyfromp_sum_f:   sum of the above, also as a function of p
        :dxdyfromp_valx_f:  valx = dy/p + dx, also as a function of p
        :dxdyfromp_valy_f:  valy = dy + p*dx/p, also as a function of p
        :p_optimal:         optimal p value

        *the CPCInverter object ensures that all curves in the list correspond to the same quote
        conventions, according to the primary direction of the pair (as determined by the Pair
        object). Accordingly, tknx and tkny are always the same for all curves in the list, regardless
        of the quote direction of the pair. The CPCInverter object abstracts this away, but of course
        only for functions that are accessible through it.
        """

        NONEFUNC = lambda x: None

        curves: list = field(repr=False, default=None)
        dxdyfromp_vec_f: any = field(repr=False, default=NONEFUNC)
        dxdyfromp_sum_f: any = field(repr=False, default=NONEFUNC)
        dxdyfromp_valx_f: any = field(repr=False, default=NONEFUNC)
        dxdyfromp_valy_f: any = field(repr=False, default=NONEFUNC)
        p_optimal: float = field(repr=False, default=None)
        errormsg: str = field(repr=True, default=None)

        def __post_init__(self, *args, **kwargs):
            super().__post_init__(*args, **kwargs)
            # print("[SimpleOptimizerResult] post_init")
            assert (
                self.p_optimal is not None or self.errormsg is not None
            ), "p_optimal must be set unless errormsg is set"
            if self.method is None:
                self.method = "simple"

        @property
        def is_error(self):
            return self.errormsg is not None

        def detailed_error(self):
            return self.errormsg

        def status(self):
            return "error" if self.is_error else "converged"

        def dxdyfromp_vecs_f(self, p):
            """returns dx, dy as separate vectors instead as a vector of tuples"""
            return tuple(zip(*self.dxdyfromp_vec_f(p)))

        @property
        def tknx(self):
            return self.curves[0].tknx

        @property
        def tkny(self):
            return self.curves[0].tkny

        @property
        def tknxp(self):
            return self.curves[0].tknxp

        @property
        def tknyp(self):
            return self.curves[0].tknyp

        @property
        def pair(self):
            return self.curves[0].pair

        @property
        def pairp(self):
            return self.curves[0].pairp

        @property
        def dxdy_vecs(self):
            return self.dxdyfromp_vecs_f(self.p_optimal)

        @property
        def dxvalues(self):
            return self.dxdy_vecs[0]

        dxv = dxvalues

        @property
        def dyvalues(self):
            return self.dxdy_vecs[1]

        dyv = dyvalues

        @property
        def dxdy_vec(self):
            return self.dxdyfromp_vec_f(self.p_optimal)

        @property
        def dxdy_sum(self):
            return self.dxdyfromp_sum_f(self.p_optimal)

        @property
        def dxdy_valx(self):
            return self.dxdyfromp_valx_f(self.p_optimal)

        valx = dxdy_valx

        @property
        def dxdy_valy(self):
            return self.dxdyfromp_valy_f(self.p_optimal)

        valy = dxdy_valy

        def trade_instructions(self, ti_format=None):
            """returns list of TradeInstruction objects"""
            result = (
                CPCArbOptimizer.TradeInstruction.new(
                    curve_or_cid=c, tkn1=self.tknx, amt1=dx, tkn2=self.tkny, amt2=dy
                )
                for c, dx, dy in zip(self.curves, self.dxvalues, self.dyvalues)
                if dx != 0 or dy != 0
            )
            assert ti_format != CPCArbOptimizer.TIF_DFAGGR, "TIF_DFAGGR not implemented for convex optimization"
            assert ti_format != CPCArbOptimizer.TIF_DFPG, "TIF_DFPG not implemented for convex optimization"
            return CPCArbOptimizer.TradeInstruction.to_format(result, ti_format=ti_format)


    SO_DXDYVECFUNC = "dxdyvecfunc"
    SO_DXDYSUMFUNC = "dxdysumfunc"
    SO_DXDYVALXFUNC = "dxdyvalxfunc"
    SO_DXDYVALYFUNC = "dxdyvalyfunc"
    SO_PMAX = "pmax"
    SO_GLOBALMAX = "globalmax"
    SO_TARGETTKN = "targettkn"
    
    def simple_optimizer(self, targettkn=None, result=None, *, params=None):
        """
        a simple optimizer that does not use cvxpy and the works only on curves on one pair

        :result:            determines what to return
                            :SO_DXDYVECFUNC:    function of p returning vector of dx,dy values
                            :SO_DXDYSUMFUNC:    function of p returning sum of dx,dy values
                            :SO_DXDYVALXFUNC:   function of p returning value of dx,dy sum in units of tknx
                            :SO_DXDYVALYFUNC:   ditto tkny
                            :SO_PMAX:           optimal p value for global max
                            :SO_GLOBALMAX:      global max of sum dx*p + dy
                            :SO_TARGETTKN:      optimizes for one token, the other is zero
        :targettkn:         token to optimize for (if result==SO_TARGETTKN); must be None if
                            result==SO_GLOBALMAX; result defaults to the corresponding value
                            depending on whether or not targettkn is None
        :params:            dict of parameters (not currently used)
        """
        start_time = time.time()
        curves_t = CPCInverter.wrap(self.curve_container)
        assert len(curves_t) > 0, "no curves found"
        c0 = curves_t[0]
        pairs = set(c.pair for c in curves_t)
        assert len(pairs) != 0, f"no pairs found, probably empty curves [{curves_t}]"
        assert (len(pairs) == 1), f"simple_optimizer only works on curves of one pair [{pairs}]"
        assert not (targettkn is None and result == self.SO_TARGETTKN), "targettkn must be set if result==SO_TARGETTKN"
        assert not (targettkn is not None and result == self.SO_GLOBALMAX), f"targettkn must be None if result==SO_GLOBALMAX {targettkn}"

        dxdy = lambda r: (np.array(r[0:2]))

        dxdyfromp_vec_f = lambda p: tuple(dxdy(c.dxdyfromp_f(p)) for c in curves_t)
        if result == self.SO_DXDYVECFUNC:
            return dxdyfromp_vec_f

        dxdyfromp_sum_f = lambda p: sum(dxdy(c.dxdyfromp_f(p)) for c in curves_t)
        if result == self.SO_DXDYSUMFUNC:
            return dxdyfromp_sum_f

        dxdyfromp_valy_f = lambda p: np.dot(dxdyfromp_sum_f(p), np.array([p, 1]))
        if result == self.SO_DXDYVALYFUNC:
            return dxdyfromp_valy_f

        dxdyfromp_valx_f = lambda p: dxdyfromp_valy_f(p) / p
        if result == self.SO_DXDYVALXFUNC:
            return dxdyfromp_valx_f

        if result is None:
            if targettkn is None:
                result = self.SO_GLOBALMAX
            else:
                result = self.SO_TARGETTKN

        if not result == self.SO_TARGETTKN:
            p_avg = np.mean([c.p for c in curves_t])
            p_optimal = self.findmax(dxdyfromp_valx_f, p_avg)
            opt_result = dxdyfromp_valx_f(float(p_optimal))
            if result == self.SO_PMAX:
                return p_optimal
            elif result != self.SO_GLOBALMAX:
                raise ValueError(f"unknown result type {result}")
            method = "simple-globalmax"
        else:
            p_min = np.min([c.p for c in curves_t])
            p_max = np.max([c.p for c in curves_t])
            assert targettkn in {
                c0.tknx,
                c0.tkny,
            }, f"targettkn {targettkn} not in {c0.tknx}, {c0.tkny}"
            # we are now running a goalseek == 0 on the token that is NOT the target token
            if targettkn == c0.tknx:
                func = lambda p: dxdyfromp_sum_f(p)[1]
                p_optimal = self.goalseek(func, p_min * 0.99, p_max * 1.01)
                opt_result = dxdyfromp_sum_f(float(p_optimal))[0]
            else:
                func = lambda p: dxdyfromp_sum_f(p)[0]
                p_optimal = self.goalseek(func, p_min * 0.99, p_max * 1.01)
                opt_result = dxdyfromp_sum_f(float(p_optimal))[1]
            method = "simple-targettkn"

        if p_optimal.is_error:
            return self.SimpleOptimizerResult(
                result=None,
                time=time.time() - start_time,
                curves=curves_t,
                dxdyfromp_vec_f=dxdyfromp_vec_f,
                dxdyfromp_sum_f=dxdyfromp_sum_f,
                dxdyfromp_valx_f=dxdyfromp_valx_f,
                dxdyfromp_valy_f=dxdyfromp_valy_f,
                p_optimal=None,
                errormsg=p_optimal.errormsg,
                method=method,
                optimizer=self,
            )
        return self.SimpleOptimizerResult(
            result=opt_result,
            time=time.time() - start_time,
            curves=curves_t,
            dxdyfromp_vec_f=dxdyfromp_vec_f,
            dxdyfromp_sum_f=dxdyfromp_sum_f,
            dxdyfromp_valx_f=dxdyfromp_valx_f,
            dxdyfromp_valy_f=dxdyfromp_valy_f,
            p_optimal=float(p_optimal),
            method=method,
            optimizer=self,
        )
