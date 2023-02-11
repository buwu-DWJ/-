from functools import partial
from numpy import ndarray, array, arange, zeros, ones, argmin, minimum, maximum, log, exp
from numpy.linalg import norm
from numpy.random import normal
from scipy.interpolate import interp1d
from scipy.optimize import minimize
import dwj_tools.read_hdf as r
import pandas as pd
import numpy as np
from tqdm import tqdm


class WingModel(object):
    @staticmethod
    def skew(moneyness: ndarray, vc: float, sc: float, pc: float, cc: float, dc: float, uc: float, dsm: float,
             usm: float) -> ndarray:
        """
        :param moneyness: converted strike, moneyness
        :param vc:
        :param sc:
        :param pc:
        :param cc:
        :param dc:
        :param uc:
        :param dsm:
        :param usm:
        :return:
        """
        assert -1 < dc < 0
        assert dsm > 0
        assert 1 > uc > 0
        assert usm > 0
        # assert 1e-6 < vc < 50  # 数值优化过程稳定
        # assert -1e6 < sc < 1e6
        assert dc * (1 + dsm) <= dc <= 0 <= uc <= uc * (1 + usm)
        # volatility at this converted strike, vol(x) is then calculated as follows:
        vol_list = []
        for x in moneyness:
            # volatility at this converted strike, vol(x) is then calculated as follows:
            if x < dc * (1 + dsm):
                vol = vc + dc * (2 + dsm) * (sc / 2) + \
                    (1 + dsm) * pc * pow(dc, 2)
            elif dc * (1 + dsm) < x <= dc:
                vol = vc - (1 + 1 / dsm) * pc * pow(dc, 2) - sc * dc / (2 * dsm) + (1 + 1 / dsm) * (
                    2 * pc * dc + sc) * x - (pc / dsm + sc / (2 * dc * dsm)) * pow(x, 2)
            elif dc < x <= 0:
                vol = vc + sc * x + pc * pow(x, 2)
            elif 0 < x <= uc:
                vol = vc + sc * x + cc * pow(x, 2)
            elif uc < x <= uc * (1 + usm):
                vol = vc - (1 + 1 / usm) * cc * pow(uc, 2) - sc * uc / (2 * usm) + (1 + 1 / usm) * (
                    2 * cc * uc + sc) * x - (cc / usm + sc / (2 * uc * usm)) * pow(x, 2)
            elif uc * (1 + usm) < x:
                vol = vc + uc * (2 + usm) * (sc / 2) + \
                    (1 + usm) * cc * pow(uc, 2)
            else:
                raise ValueError("x value error!")
            vol_list.append(vol)
        return array(vol_list)

    @classmethod
    def loss_skew(cls, params: [float, float, float, float], x: ndarray, iv: ndarray, vega: ndarray, dc: float, uc: float, dsm: float, usm: float):
        """
        :param params:vc sc, pc, cc
        :param x:
        :param iv:
        :param vega:
        :param dc:
        :param uc:
        :param dsm:
        :param usm:
        :return:
        """
        vc, sc, pc, cc = params
        vega = vega / vega.max()
        value = cls.skew(x, vc, sc, pc, cc, dc, uc, dsm, usm)
        return norm((value - iv) * vega, ord=2, keepdims=False)

    @classmethod
    def calibrate_skew(cls, x: ndarray, iv: ndarray, vega: ndarray, dc: float = -0.2, uc: float = 0.2, dsm: float = 0.5,
                       usm: float = 0.5, is_bound_limit: bool = False,
                       epsilon: float = 1e-16, inter: str = "cubic"):
        """

        :param x: moneyness
        :param iv:
        :param vega:
        :param dc:
        :param uc:
        :param dsm:
        :param usm:
        :param is_bound_limit:
        :param epsilon:
        :param inter: cubic inter
        :return:
        """

        # vc = interp1d(x, iv, kind=inter, fill_value="extrapolate")([0])[0]

        # init guess for va, sc, pc, cc
        if is_bound_limit:
            bounds = [(-1e3, 1e3), (-1e3, 1e3), (-1e3, 1e3), (-1e3, 1e3)]
        else:
            bounds = [(None, None), (None, None), (None, None), (None, None)]
        initial_guess = normal(size=4)

        args = (x, iv, vega, dc, uc, dsm, usm)
        residual = minimize(cls.loss_skew, initial_guess,
                            args=args, bounds=bounds, tol=epsilon, method="SLSQP")
        assert residual.success
        return residual.x, residual.fun

    @staticmethod
    def sc(sr: float, scr: float, ssr: float, ref: float, atm: ndarray or float) -> ndarray or float:
        return sr - scr * ssr * ((atm - ref) / ref)

    @classmethod
    def loss_scr(cls, x: float, sr: float, ssr: float, ref: float, atm: ndarray, sc: ndarray) -> float:
        return norm(sc - cls.sc(sr, x, ssr, ref, atm), ord=2, keepdims=False)

    @classmethod
    def fit_scr(cls, sr: float, ssr: float, ref: float, atm: ndarray, sc: ndarray,
                epsilon: float = 1e-16) -> [float, float]:
        init_value = array([0.01])
        residual = minimize(cls.loss_scr, init_value, args=(
            sr, ssr, ref, atm, sc), tol=epsilon, method="SLSQP")
        assert residual.success
        return residual.x, residual.fun

    @staticmethod
    def vc(vr: float, vcr: float, ssr: float, ref: float, atm: ndarray or float) -> ndarray or float:
        return vr - vcr * ssr * ((atm - ref) / ref)

    @classmethod
    def loss_vc(cls, x: float, vr: float, ssr: float, ref: float, atm: ndarray, vc: ndarray) -> float:
        return norm(vc - cls.vc(vr, x, ssr, ref, atm), ord=2, keepdims=False)

    @classmethod
    def fit_vcr(cls, vr: float, ssr: float, ref: float, atm: ndarray, vc: ndarray,
                epsilon: float = 1e-16) -> [float, float]:
        init_value = array([0.01])
        residual = minimize(cls.loss_vc, init_value, args=(
            vr, ssr, ref, atm, vc), tol=epsilon, method="SLSQP")
        assert residual.success
        return residual.x, residual.fun

    @classmethod
    def wing(cls, x: ndarray, ref: float, atm: float, vr: float, vcr: float, sr: float, scr: float, ssr: float,
             pc: float, cc: float, dc: float, uc: float, dsm: float, usm: float) -> ndarray:
        """
        wing model

        :param x:
        :param ref:
        :param atm:
        :param vr:
        :param vcr:
        :param sr:
        :param scr:
        :param ssr:
        :param pc:
        :param cc:
        :param dc:
        :param uc:
        :param dsm:
        :param usm:
        :return:
        """
        vc = cls.vc(vr, vcr, ssr, ref, atm)
        sc = cls.sc(sr, scr, ssr, ref, atm)
        return cls.skew(x, vc, sc, pc, cc, dc, uc, dsm, usm)


class ArbitrageFreeWingModel(WingModel):
    @classmethod
    def calibrate(cls, x: ndarray, iv: ndarray, vega: ndarray, dc: float = -0.2, uc: float = 0.2, dsm: float = 0.5,
                  usm: float = 0.5, is_bound_limit: bool = False, epsilon: float = 1e-16, inter: str = "cubic",
                  level: float = 0, method: str = "SLSQP", epochs: int = None, show_error: bool = False,
                  use_constraints: bool = False) -> ([float, float, float, float], float):
        """
        :param x:
        :param iv:
        :param vega:
        :param dc:
        :param uc:
        :param dsm:
        :param usm:
        :param is_bound_limit:
        :param epsilon:
        :param inter:
        :param level:
        :param method:
        :param epochs:
        :param show_error:
        :param use_constraints:
        :return:
        """
        # vega = clip(vega, 1e-6, 1e6)
        # iv = clip(iv, 1e-6, 10)
        # init guess for sc, pc, cc
        if is_bound_limit:
            bounds = [(-1e3, 1e3), (-1e3, 1e3), (-1e3, 1e3), (-1e3, 1e3)]
        else:
            bounds = [(None, None), (None, None), (None, None), (None, None)]
        # vc = interp1d(x, iv, kind=inter, fill_value="extrapolate")([0])[0]
        constraints = dict(type='ineq', fun=partial(
            cls.constraints, args=(x, dc, uc, dsm, usm), level=level))
        args = (x, iv, vega, dc, uc, dsm, usm)
        if epochs is None:
            if use_constraints:
                residual = minimize(cls.loss_skew, normal(size=4), args=args, bounds=bounds, constraints=constraints,
                                    tol=epsilon, method=method)
            else:
                residual = minimize(cls.loss_skew, normal(
                    size=4), args=args, bounds=bounds, tol=epsilon, method=method)

            if residual.success:
                vc, sc, pc, cc = residual.x
                arbitrage_free = cls.check_butterfly_arbitrage(
                    sc, pc, cc, dc, dsm, uc, usm, x, vc)
                return residual.x, residual.fun, arbitrage_free
            else:
                epochs = 10
                if show_error:
                    print(
                        "calibrate wing-model wrong, use epochs = 10 to find params! params: {}".format(residual.x))
        if epochs is not None:
            params = zeros([epochs, 4])
            loss = ones([epochs, 1])
            for i in range(epochs):
                if use_constraints:
                    residual = minimize(cls.loss_skew, normal(size=4), args=args, bounds=bounds,
                                        constraints=constraints,
                                        tol=epsilon, method="SLSQP")
                else:
                    residual = minimize(cls.loss_skew, normal(size=4), args=args, bounds=bounds, tol=epsilon,
                                        method="SLSQP")
                if not residual.success and show_error:
                    print(
                        "calibrate wing-model wrong, wrong @ {} /10! params: {}".format(i, residual.x))
                params[i] = residual.x
                loss[i] = residual.fun
            min_idx = argmin(loss)
            vc, sc, pc, cc = params[min_idx]
            loss = loss[min_idx][0]
            arbitrage_free = cls.check_butterfly_arbitrage(
                sc, pc, cc, dc, dsm, uc, usm, x, vc)
            return (vc, sc, pc, cc), loss, arbitrage_free

    @classmethod
    def constraints(cls, x: [float, float, float, float], args: [ndarray, float, float, float, float],
                    level: float = 0) -> float:
        """蝶式价差无套利约束

        :param x: guess values, sc, pc, cc
        :param args:
        :param level:
        :return:
        """
        vc, sc, pc, cc = x
        moneyness, dc, uc, dsm, usm = args

        if level == 0:
            pass
        elif level == 1:
            moneyness = arange(-1, 1.01, 0.01)
        else:
            moneyness = arange(-1, 1.001, 0.001)

        return cls.check_butterfly_arbitrage(sc, pc, cc, dc, dsm, uc, usm, moneyness, vc)

    """蝶式价差无套利约束条件
    """

    @staticmethod
    def left_parabolic(sc: float, pc: float, x: float, vc: float) -> float:
        """
        :param sc:
        :param pc:
        :param x:
        :param vc:
        :return:
        """
        return pc - 0.25 * (sc + 2 * pc * x) ** 2 * (0.25 + 1 / (vc + sc * x + pc * x * x)) + (
            1 - 0.5 * x * (sc + 2 * pc * x) / (vc + sc * x + pc * x * x)) ** 2

    @staticmethod
    def right_parabolic(sc: float, cc: float, x: float, vc: float) -> float:
        """
        :param sc:
        :param cc:
        :param x:
        :param vc:
        :return:
        """
        return cc - 0.25 * (sc + 2 * cc * x) ** 2 * (0.25 + 1 / (vc + sc * x + cc * x * x)) + (
            1 - 0.5 * x * (sc + 2 * cc * x) / (vc + sc * x + cc * x * x)) ** 2

    @staticmethod
    def left_smoothing_range(sc: float, pc: float, dc: float, dsm: float, x: float, vc: float) -> float:
        a = - pc / dsm - 0.5 * sc / (dc * dsm)
        b1 = -0.25 * ((1 + 1 / dsm) * (2 * dc * pc + sc) - 2 *
                      (pc / dsm + 0.5 * sc / (dc * dsm)) * x) ** 2
        b2 = -dc ** 2 * (1 + 1 / dsm) * pc - 0.5 * dc * sc / dsm + vc + (1 + 1 / dsm) * (2 * dc * pc + sc) * x - (
            pc / dsm + 0.5 * sc / (dc * dsm)) * x ** 2
        b2 = (0.25 + 1 / b2)
        b = b1 * b2
        c1 = x * ((1 + 1 / dsm) * (2 * dc * pc + sc) - 2 *
                  (pc / dsm + 0.5 * sc / (dc * dsm)) * x)
        c2 = 2 * (-dc ** 2 * (1 + 1 / dsm) * pc - 0.5 * dc * sc / dsm + vc + (1 + 1 / dsm) * (2 * dc * pc + sc) * x - (
            pc / dsm + 0.5 * sc / (dc * dsm)) * x ** 2)
        c = (1 - c1 / c2) ** 2
        return a + b + c

    @staticmethod
    def right_smoothing_range(sc: float, cc: float, uc: float, usm: float, x: float, vc: float) -> float:
        a = - cc / usm - 0.5 * sc / (uc * usm)
        b1 = -0.25 * ((1 + 1 / usm) * (2 * uc * cc + sc) - 2 *
                      (cc / usm + 0.5 * sc / (uc * usm)) * x) ** 2
        b2 = -uc ** 2 * (1 + 1 / usm) * cc - 0.5 * uc * sc / usm + vc + (1 + 1 / usm) * (2 * uc * cc + sc) * x - (
            cc / usm + 0.5 * sc / (uc * usm)) * x ** 2
        b2 = (0.25 + 1 / b2)
        b = b1 * b2
        c1 = x * ((1 + 1 / usm) * (2 * uc * cc + sc) - 2 *
                  (cc / usm + 0.5 * sc / (uc * usm)) * x)
        c2 = 2 * (-uc ** 2 * (1 + 1 / usm) * cc - 0.5 * uc * sc / usm + vc + (1 + 1 / usm) * (2 * uc * cc + sc) * x - (
            cc / usm + 0.5 * sc / (uc * usm)) * x ** 2)
        c = (1 - c1 / c2) ** 2
        return a + b + c

    @staticmethod
    def left_constant_level() -> float:
        return 1

    @staticmethod
    def right_constant_level() -> float:
        return 1

    @classmethod
    def _check_butterfly_arbitrage(cls, sc: float, pc: float, cc: float, dc: float, dsm: float, uc: float, usm: float,
                                   x: float, vc: float) -> float:
        """检查是否存在蝶式价差套利机会，确保拟合time-slice iv-curve 是无套利（无蝶式价差静态套利）曲线

        :param sc:
        :param pc:
        :param cc:
        :param dc:
        :param dsm:
        :param uc:
        :param usm:
        :param x:
        :param vc:
        :return:
        """
        # if x < dc * (1 + dsm):
        #     return cls.left_constant_level()
        # elif dc * (1 + dsm) < x <= dc:
        #     return cls.left_smoothing_range(sc, pc, dc, dsm, x, vc)
        # elif dc < x <= 0:
        #     return cls.left_parabolic(sc, pc, x, vc)
        # elif 0 < x <= uc:
        #     return cls.right_parabolic(sc, cc, x, vc)
        # elif uc < x <= uc * (1 + usm):
        #     return cls.right_smoothing_range(sc, cc, uc, usm, x, vc)
        # elif uc * (1 + usm) < x:
        #     return cls.right_constant_level()
        # else:
        #     raise ValueError("x value error!")

        if dc < x <= 0:
            return cls.left_parabolic(sc, pc, x, vc)
        elif 0 < x <= uc:
            return cls.right_parabolic(sc, cc, x, vc)
        else:
            return 0

    @classmethod
    def get_curve_points(cls, moneyness, vc, sc, pc, cc, dc, uc, dsm, usm):
        curve_points = []
        for x in moneyness:
            if x < dc * (1 + dsm):
                curve_points += [cls.left_constant_level()]
            elif dc * (1 + dsm) < x <= dc:
                curve_points += [cls.left_smoothing_range(
                    sc, pc, dc, dsm, x, vc)]
            elif dc < x <= 0:
                curve_points += [cls.left_parabolic(sc, pc, x, vc)]
            elif 0 < x <= uc:
                curve_points += [cls.right_parabolic(sc, cc, x, vc)]
            elif uc < x <= uc * (1 + usm):
                curve_points += [cls.right_smoothing_range(
                    sc, cc, uc, usm, x, vc)]
            elif uc * (1 + usm) < x:
                curve_points += [cls.right_constant_level()]
        return curve_points

    @classmethod
    def check_butterfly_arbitrage(cls, sc: float, pc: float, cc: float, dc: float, dsm: float, uc: float, usm: float,
                                  moneyness: ndarray, vc: float) -> float:
        """

        :param sc:
        :param pc:
        :param cc:
        :param dc:
        :param dsm:
        :param uc:
        :param usm:
        :param moneyness:
        :param vc:
        :return:
        """
        con_arr = []
        for x in moneyness:
            con_arr.append(cls._check_butterfly_arbitrage(
                sc, pc, cc, dc, dsm, uc, usm, x, vc))
        con_arr = array(con_arr)
        if (con_arr >= 0).all():
            return minimum(con_arr.mean(), 1e-7)
        else:
            return maximum((con_arr[con_arr < 0]).mean(), -1e-7)


def fit_wing(date: str, symbol: str, month: int = 0, dc: float = -0.12, uc: float = 0.12, dsm: float = 0.5, usm: float = 0.5):
    option, _, synf = r.read_data_dogsk(symbol, date, min_range='all')
    synf_array = synf.iloc[:, month*9+4].values
    aiyang_atm_iv = synf.iloc[:, month*9+3].values
    crt_tau = option['tau'].drop_duplicates(keep='first').tolist()[month]
    true_option = option.iloc[list(option['tau'] == crt_tau)]
    aiyang_vol = pd.DataFrame()
    fit_vol = pd.DataFrame()
    fit_atm_iv = []
    board = pd.DataFrame()
    is_arbitrage_free = []
    fit_points = pd.DataFrame()
    for i in tqdm(range(240)):
        temp_synf = synf_array[i]
        temp_option = true_option.iloc[(true_option.index == i).tolist()]
        true_option_call = temp_option.loc[list(
            temp_option['flag'] == 'C'), :].reset_index(drop=True)
        iv_array = true_option_call['iv'].values
        vega_array = true_option_call['vega'].values*100
        strike_list = [float(temp_symbol.split('.C.')[1].replace('A', ''))
                       for temp_symbol in true_option_call['symbol'].values]
        strike_array = array(strike_list)
        param, loss, arbitrage_free = ArbitrageFreeWingModel.calibrate(
            x=log(strike_array/temp_synf), iv=iv_array, vega=vega_array, dc=dc, uc=uc, dsm=dsm, usm=usm)
        vol_list = WingModel.skew(moneyness=log(
            strike_array/temp_synf), vc=param[0], sc=param[1], pc=param[2], cc=param[3], dc=dc, uc=uc, dsm=dsm, usm=usm)
        fit_vol = fit_vol.append(pd.Series(vol_list), ignore_index=True)
        aiyang_vol = aiyang_vol.append(pd.Series(iv_array), ignore_index=True)
        fit_atm_iv += [param[0]]
        temp_board = [temp_synf*exp(dc*(1+dsm)), temp_synf*exp(dc),
                      temp_synf, temp_synf*exp(uc), temp_synf*exp(uc*(1+usm))]
        board = board.append(pd.Series(temp_board), ignore_index=True)
        x = np.linspace(strike_array[0], strike_array[-1], 300)
        fit_points = fit_points.append(pd.Series(WingModel.skew(moneyness=log(
            x/temp_synf), vc=param[0], sc=param[1], pc=param[2], cc=param[3], dc=dc, uc=uc, dsm=dsm, usm=usm)), ignore_index=True)
        is_arbitrage_free += [arbitrage_free]
    return strike_array, aiyang_vol, fit_vol, aiyang_atm_iv, fit_atm_iv, board, is_arbitrage_free, fit_points
