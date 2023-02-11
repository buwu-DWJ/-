#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   utility.py
@Time    :   2023/01/17 13:33:01
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   None
'''

from icetcore import TCoreAPI, QuoteEvent, TradeEvent
import pandas as pd
from functools import partial
from numpy import ndarray, array, arange, zeros, ones, argmin, minimum, maximum, log, exp
from numpy.linalg import norm
from numpy.random import normal
from scipy.optimize import minimize
import os
import numpy as np
import warnings
import time
import datetime
import threading
import tkinter as tk
from tkinter import ttk
from scipy import sqrt, special


'''Canvas布局示例
https://blog.csdn.net/qq_33934427/article/details/123980987
'''


warnings.simplefilter('ignore')
thisDir = os.path.dirname(__file__)
tradingday = pd.read_hdf(os.path.join(
    thisDir, 'tradingday.h5'))
date_str_list = [csd_date.strftime('%Y%m%d') for csd_date in tradingday.index]
RAW_TRADINGDAY_PER_DAY = 240
ADJUSTED_TRADINGDAY_PER_YEAR = 250
R = 0  # 计算iv的无风险利率
TODAY_STR = datetime.date.today().strftime('%Y%m%d')
YESTERDAY_STR = date_str_list[date_str_list.index(TODAY_STR)-1]
UND_TUPLE = ('0', 'CZCE.CF', 'CZCE.MA', 'CZCE.OI', 'CZCE.PK', 'CZCE.RM', 'CZCE.SR', 'CZCE.TA', 'CZCE.ZC', 'SHFE.al', 'SHFE.au', 'SHFE.cu',
             'SHFE.ru', 'SHFE.zn', 'INE.sc', 'DCE.a', 'DCE.b', 'DCE.c', 'DCE.i', 'DCE.l', 'DCE.m', 'DCE.p', 'DCE.pg', 'DCE.pp', 'DCE.v', 'DCE.y')


class BS_CALCULATOR():
    '''
    func: bs_call
    func: bs_put
    '''
    @staticmethod
    def bs_call(S, X, T, r, sigma):
        d1 = (log(S/X)+(r+sigma*sigma/2.0)*T)/(sigma*sqrt(T))
        d2 = d1-sigma*sqrt(T)
        return S*special.ndtr(d1)-X*exp(-r*T)*special.ndtr(d2)

    @staticmethod
    def bs_put(S, X, T, r, sigma):
        d1 = (log(S/X)+(r+sigma*sigma/2.)*T)/(sigma*sqrt(T))
        d2 = d1-sigma*sqrt(T)
        return X*exp(-r*T)*special.ndtr(-d2)-S*special.ndtr(-d1)


class OPTION_CALCULATOR():
    '''
    func: CalIVCall
    func: CalIVPut
    func: CalDeltaCall
    func: CalDeltaPut
    '''
    @staticmethod
    def CalIVCall(x, S, T, r):
        # x[0]:c, x[1]:K
        preciselevel = 0.00001
        i = 1
        sigma1 = 0.0001
        sigma2 = 2
        sigma = sigma1
        while i < 1000:
            i += 1
            diff = x[0]-BS_CALCULATOR.bs_call(S, x[1], T, r, sigma)
            if diff > 0:
                sigma1 = sigma
                sigma = (sigma1+sigma2)/2
            else:
                sigma2 = sigma
                sigma = (sigma1+sigma2)/2
            if abs(diff) < preciselevel:
                break
            if sigma2 == sigma1:
                break
        return(round(sigma, 4))

    @staticmethod
    def CalIVPut(x, S, T, r):
        preciselevel = 0.00001
        i = 1
        sigma1 = 0.0001
        sigma2 = 2
        sigma = sigma1
        while i < 1000:
            i += 1
            diff = x[0]-BS_CALCULATOR.bs_put(S, x[1], T, r, sigma)
            if diff > 0:
                sigma1 = sigma
                sigma = (sigma1+sigma2)/2
            else:
                sigma2 = sigma
                sigma = (sigma1+sigma2)/2
            if abs(diff) < preciselevel:
                break
            if sigma2 == sigma1:
                break
        return(round(sigma, 4))

    @staticmethod
    def CalDeltaCall(S, K, T, r, iv):
        change = 0.0000001
        price1 = BS_CALCULATOR.bs_call(S+change, K, T, r, iv)
        price2 = BS_CALCULATOR.bs_call(S-change, K, T, r, iv)
        delta = (price1-price2)/(2*change)
        return(delta)

    @staticmethod
    def CalDeltaPut(S, K, T, r, iv):
        change = 0.0000001
        price1 = BS_CALCULATOR.bs_put(S+change, K, T, r, iv)
        price2 = BS_CALCULATOR.bs_put(S-change, K, T, r, iv)
        delta = (price1-price2)/(2*change)
        return(delta)


class WingModel(object):
    @staticmethod
    def skew(moneyness: ndarray, vc: float, sc: float, pc: float, cc: float, dc: float, uc: float, dsm: float,
             usm: float) -> ndarray:
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
        vc, sc, pc, cc = params
        vega = vega / vega.max()
        value = cls.skew(x, vc, sc, pc, cc, dc, uc, dsm, usm)
        return norm((value - iv) * vega, ord=2, keepdims=False)

    @classmethod
    def calibrate_skew(cls, x: ndarray, iv: ndarray, vega: ndarray, dc: float = -0.2, uc: float = 0.2, dsm: float = 0.5,
                       usm: float = 0.5, is_bound_limit: bool = False,
                       epsilon: float = 1e-16, inter: str = "cubic"):
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
        vc = cls.vc(vr, vcr, ssr, ref, atm)
        sc = cls.sc(sr, scr, ssr, ref, atm)
        return cls.skew(x, vc, sc, pc, cc, dc, uc, dsm, usm)


class ArbitrageFreeWingModel(WingModel):
    @classmethod
    def calibrate(cls, x: ndarray, iv: ndarray, vega: ndarray, dc: float = -0.2, uc: float = 0.2, dsm: float = 0.5,
                  usm: float = 0.5, is_bound_limit: bool = False, epsilon: float = 1e-16, inter: str = "cubic",
                  level: float = 0, method: str = "SLSQP", epochs: int = None, show_error: bool = False,
                  use_constraints: bool = False) -> ([float, float, float, float], float):
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

    @staticmethod
    def left_parabolic(sc: float, pc: float, x: float, vc: float) -> float:
        return pc - 0.25 * (sc + 2 * pc * x) ** 2 * (0.25 + 1 / (vc + sc * x + pc * x * x)) + (
            1 - 0.5 * x * (sc + 2 * pc * x) / (vc + sc * x + pc * x * x)) ** 2

    @staticmethod
    def right_parabolic(sc: float, cc: float, x: float, vc: float) -> float:
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
        con_arr = []
        for x in moneyness:
            con_arr.append(cls._check_butterfly_arbitrage(
                sc, pc, cc, dc, dsm, uc, usm, x, vc))
        con_arr = array(con_arr)
        if (con_arr >= 0).all():
            return minimum(con_arr.mean(), 1e-7)
        else:
            return maximum((con_arr[con_arr < 0]).mean(), -1e-7)


class APIEvent(TradeEvent, QuoteEvent):
    def __init__(self) -> None:
        super().__init__()

    def onconnected(self, apitype: str):
        pass

    def ondisconnected(self, apitype: str):
        pass

    def onbar(self, datatype, interval, symbol, data: list, isreal: bool):
        pass

    def onquote(self, data):
        global df_dict
        try:
            df_dict[data['Symbol']] = data
        except NameError:
            df_dict = {}
            df_dict[data['Symbol']] = data


class CTA_OPT_MONITOR():
    def __init__(self):
        self.window = tk.Tk()
        self.row_num = 0
        pass

    @staticmethod
    def get_adjusted_tau():
        for i, month in enumerate(maturity_dict):
            extra_date = 0
            end_index = date_str_list.index(maturity_dict[month])
            start_index = end_index - tradingday_dict[month] + 2
            for i, date in enumerate(tradingday.index[start_index:end_index+1]):
                gap_date = (date-tradingday.index[start_index+i-1]).days
                if gap_date == 3:
                    extra_date += 0.2*2
                elif gap_date > 3:
                    extra_date += 0.3*(gap_date-1)
            # print(extra_date)
            adjusted_tradingday_dict[month] = tradingday_dict[month] + extra_date
            # print(adjusted_tau_dict[month])
            adjusted_tau_dict[month] = adjusted_tradingday_dict[month] / \
                ADJUSTED_TRADINGDAY_PER_YEAR

    @staticmethod
    def fit_wing(month: int = 0, dc: float = -0.12, uc: float = 0.12, dsm: float = 0.5, usm: float = 0.5):
        temp_synf = df_dict[underlying_dict[month]]['Last']
        wing_strike_array[month] = np.array([float(a) for a in strike_dict[month][max(strike_dict[month].index(
            atm_strike_dict[month])-9, 0): strike_dict[month].index(atm_strike_dict[month])+10]])
        wing_iv_array[month] = np.array([float(a) for a in np.array(tabledata_iv_dict[month][7][max(strike_dict[month].index(
            atm_strike_dict[month])-8, 1): strike_dict[month].index(atm_strike_dict[month])+11])])
        vega_array = np.array([1]*len(wing_iv_array[month]))
        param, loss, arbitrage_free = ArbitrageFreeWingModel.calibrate(
            x=log(wing_strike_array[month]/temp_synf), iv=wing_iv_array[month], vega=vega_array, dc=dc, uc=uc, dsm=dsm, usm=usm)
        wing_fit_vol[month] = WingModel.skew(moneyness=log(
            wing_strike_array[month]/temp_synf), vc=param[0], sc=param[1], pc=param[2], cc=param[3], dc=dc, uc=uc, dsm=dsm, usm=usm)
        wing_fit_atm_iv[month] = param[0]
        wing_board[month] = [temp_synf*exp(dc*(1+dsm)), temp_synf*exp(dc),
                             temp_synf, temp_synf*exp(uc), temp_synf*exp(uc*(1+usm))]
        wing_x[month] = np.linspace(
            wing_strike_array[month][0], wing_strike_array[month][-1], 300)
        wing_fit_points[month] = WingModel.skew(moneyness=log(
            wing_x[month]/temp_synf), vc=param[0], sc=param[1], pc=param[2], cc=param[3], dc=dc, uc=uc, dsm=dsm, usm=usm)

    @staticmethod
    def convert_df_dict_to_tabledata_given_month(month, tabledata_price_dict, tabledata_iv_dict):
        '''
        '''
        tabledata_iv = [
            ['iv栏']+strike_dict[month]] + [['call_ask_iv'], ['call_bid_iv'], ['call_iv'],
                                           ['put_ask_iv'], ['put_bid_iv'], ['put_iv'], ['iv']]
        tabledata_price = [['报价栏']+strike_dict[month]] + \
            [['call_ask'], ['call_bid'], ['put_ask'], ['put_bid']]
        und_str = underlying_dict[month]
        crt_session = symbol_session['.'.join(und_str.split('.')[2:4])]
        crt_intraday_tau = get_intraday_tau(crt_session)
        adjusted_tau_dict[month] += crt_intraday_tau
        for k in strike_dict[month]:
            tabledata_price[1] += [df_dict['TC.O.' +
                                   '.'.join(und_str.split('.')[2:4])+'.'+month+'.C.'+k]['Ask']]
            tabledata_price[2] += [df_dict['TC.O.' +
                                   '.'.join(und_str.split('.')[2:4])+'.'+month+'.C.'+k]['Bid']]
            tabledata_price[3] += [df_dict['TC.O.' +
                                   '.'.join(und_str.split('.')[2:4])+'.'+month+'.P.'+k]['Ask']]
            tabledata_price[4] += [df_dict['TC.O.' +
                                   '.'.join(und_str.split('.')[2:4])+'.'+month+'.P.'+k]['Bid']]
        tabledata_price_dict[month] = tabledata_price
        und_close = df_dict[underlying_dict[month]]['Last']
        strike_list = [float(a) for a in strike_dict[month]]
        tabledata_iv[1] += list(np.round(np.apply_along_axis(OPTION_CALCULATOR.CalIVCall, 0, np.array(
            [[0.0001 if type(a) != float else a for a in tabledata_price[1][1:]], strike_list]), und_close, adjusted_tau_dict[month], float(R))*100, 2))
        tabledata_iv[2] += list(np.round(np.apply_along_axis(OPTION_CALCULATOR.CalIVCall, 0, np.array(
            [[0.0001 if type(a) != float else a for a in tabledata_price[2][1:]], strike_list]), und_close, adjusted_tau_dict[month], float(R))*100, 2))
        tabledata_iv[3] += [round((tabledata_iv[1][1+i]+tabledata_iv[2][1+i])/2, 2) if (tabledata_iv[1][1+i]
                                                                                        > 0.01 and tabledata_iv[2][1+i] > 0.01) else max(tabledata_iv[1][1+i], tabledata_iv[2][1+i]) for i in range(len(strike_list))]
        tabledata_iv[4] += list(np.round(np.apply_along_axis(OPTION_CALCULATOR.CalIVPut, 0, np.array(
            [[0.0001 if type(a) != float else a for a in tabledata_price[3][1:]], strike_list]), und_close, adjusted_tau_dict[month], float(R))*100, 2))
        tabledata_iv[5] += list(np.round(np.apply_along_axis(OPTION_CALCULATOR.CalIVPut, 0, np.array(
            [[0.0001 if type(a) != float else a for a in tabledata_price[4][1:]], strike_list]), und_close, adjusted_tau_dict[month], float(R))*100, 2))
        tabledata_iv[6] += [round((tabledata_iv[4][1+i]+tabledata_iv[5][1+i])/2, 2) if (tabledata_iv[4][1+i]
                                                                                        > 0.0001 and tabledata_iv[5][1+i] > 0.01) else max(tabledata_iv[4][1+i], tabledata_iv[5][1+i]) for i in range(len(strike_list))]
        tabledata_iv[7] += [round((tabledata_iv[3][1+i]+tabledata_iv[6][1+i])/2, 2) if (tabledata_iv[3][1+i]
                                                                                        > 0.0001 and tabledata_iv[6][1+i] > 0.01) else max(tabledata_iv[3][1+i], tabledata_iv[6][1+i]) for i in range(len(strike_list))]
        tabledata_iv_dict[month] = tabledata_iv

    def convert_df_dice_to_tabledata(self):
        '''
        '''
        global tabledata_price_dict
        global tabledata_iv_dict
        try:
            tabledata_price_dict
        except NameError:
            tabledata_price_dict = {}
            tabledata_iv_dict = {}
        for month in csd_month_list:
            self.convert_df_dict_to_tabledata_given_month(
                month, tabledata_price_dict, tabledata_iv_dict)

    def main_window(self):
        '''
        '''

        def get_allsymbol_given_und_and_quote():
            '''
            '''
            global symbol_dict
            global strike_dict
            global underlying_dict
            global atm_strike_dict
            global tradingday_dict
            global tau_dict
            global adjusted_tradingday_dict
            global adjusted_tau_dict
            global maturity_dict
            global csd_session
            global wing_strike_array
            global wing_iv_array
            global wing_fit_vol
            global wing_fit_atm_iv
            global wing_board
            global wing_x
            global wing_fit_points
            wing_strike_array = {}
            wing_iv_array = {}
            wing_fit_vol = {}
            wing_fit_atm_iv = {}
            wing_board = {}
            wing_fit_points = {}
            wing_x = {}
            tau_dict = {}
            adjusted_tau_dict = {}
            tradingday_dict = {}
            adjusted_tradingday_dict = {}
            atm_strike_dict = {}
            symbol_dict = {}
            strike_dict = {}
            underlying_dict = {}
            maturity_dict = {}
            adjusted_tau_dict = {}
            und = get_und.get()
            csd_session = symbol_session[und]
            all_symbol = api.getallsymbol('OPT', und.split('.')[0])

            for symbol in all_symbol:
                if und in symbol:
                    if symbol.split('.')[4] in symbol_dict.keys():
                        symbol_dict[symbol.split('.')[4]] += [symbol]
                        if symbol.split('.')[-1] not in strike_dict[symbol.split('.')[4]]:
                            strike_dict[symbol.split(
                                '.')[4]] += [symbol.split('.')[-1]]
                    else:
                        symbol_dict[symbol.split('.')[4]] = [symbol]
                        strike_dict[symbol.split('.')[4]] = [
                            symbol.split('.')[-1]]
            for key in symbol_dict.keys():
                for symbol in symbol_dict[key]:
                    api.subquote(symbol)
            for i, month in enumerate(symbol_dict.keys()):
                tradingday_dict[month] = api.gettradeingdays(
                    symbol_dict[month][0])
                tau_dict[month] = tradingday_dict[month]/RAW_TRADINGDAY_PER_DAY
                maturity_dict[month] = api.getexpirationdate(
                    symbol_dict[month][0])
                underlying_dict[month] = 'TC.F.' + und + '.' + month
                api.subquote(underlying_dict[month])
                try:
                    atm_strike_dict[month] = (api.getATM(
                        symbol_dict[month][round(len(symbol_dict[month])/2)], atmindex=0)).split('.')[-1]
                except AttributeError:
                    atm_strike_dict[month] = strike_dict[month][round(
                        len(strike_dict[month])/2)]
                globals()[f'checkvar{i}'] = tk.IntVar()
                globals()[f'check{i}'] = tk.Checkbutton(self.window, text=month, variable=globals()[
                    f'checkvar{i}']).grid(row=self.row_num, column=0)
                self.row_num += 1
            for i, month in enumerate(strike_dict.keys()):
                strike_dict[month] = strike_dict[month][max(strike_dict[month].index(
                    atm_strike_dict[month])-15, 0): strike_dict[month].index(atm_strike_dict[month])+15]
            return

        self.window.title('商品期权监控主窗口')

        def cpt_iv_and_skew():
            '''iv/skew子窗口
            '''
            global iv_dict
            global delta_dict
            global atm_iv_dict
            global csd_month_list
            iv_dict = {}
            delta_dict = {}
            atm_iv_dict = {}
            csd_month_list = []
            for i, month in enumerate(symbol_dict.keys()):
                if globals()[f'checkvar{i}'].get() == 1:
                    csd_month_list += [month]
            if len(csd_month_list) == 0:
                return
            window_iv = tk.Tk()
            window_iv.title(f'{get_und.get()}期权实时监控')
            screenwidth = window_iv.winfo_screenwidth()
            screenheight = window_iv.winfo_screenheight()
            # width = 1500
            # height = 1000
            # x = int((screenwidth - width) / 2)
            # y = int((screenheight - height) / 2)
            # window_iv.geometry('{}x{}+{}+{}'.format(width, height, x, y))
            window_iv.geometry('{}x{}'.format(screenwidth, screenheight))

            for i, month in enumerate(csd_month_list):
                globals()[f'STRIKE_LIST_{month}'] = [
                    f'K{i+1}' for i in range(len(strike_dict[month]))]
                globals()[f'table_price{i}'] = ttk.Treeview(
                    master=window_iv,
                    height=5,
                    columns=[month]+globals()[f'STRIKE_LIST_{month}'],
                    selectmode='none',
                    show='headings')
                globals()[f'table_price{i}'].heading(
                    column=month, text=month, command=lambda: print(month))
                for col in globals()[f'STRIKE_LIST_{month}']:
                    globals()[f'table_price{i}'].heading(
                        col, text=col, command=lambda: print(col))
                globals()[f'table_price{i}'].column(
                    month, width=85, minwidth=60, anchor='s')
                for col in globals()[f'STRIKE_LIST_{month}']:
                    globals()[f'table_price{i}'].column(
                        col, width=60, minwidth=60, anchor='s')
                globals()[f'table_price{i}'].grid(
                    row=i*14, column=0, columnspan=min(len(globals()[f'STRIKE_LIST_{month}']), 31))
                globals()[f'table_iv{i}'] = ttk.Treeview(
                    master=window_iv,
                    height=8,
                    selectmode='none',
                    columns=[month]+globals()[f'STRIKE_LIST_{month}'],
                    show='headings')
                globals()[f'table_iv{i}'].heading(
                    column=month, text=month, command=lambda: print(month))
                for col in globals()[f'STRIKE_LIST_{month}']:
                    globals()[f'table_iv{i}'].heading(
                        col, text=col, command=lambda: print(col))
                globals()[f'table_iv{i}'].column(
                    month, width=85, minwidth=60, anchor='s')
                for col in globals()[f'STRIKE_LIST_{month}']:
                    globals()[f'table_iv{i}'].column(
                        col, width=60, minwidth=60, anchor='s')
                globals()[f'table_iv{i}'].grid(
                    row=i*14+6, column=0, columnspan=min(len(globals()[f'STRIKE_LIST_{month}']), 31))
            crt_row = i*14+7
            tk.Label(
                window_iv, text=f'{get_und.get()} 标的价格:').grid(row=crt_row, column=0)
            crt_row += 1
            for i, month in enumerate(csd_month_list):
                globals()[f'label_und_{month}'] = tk.Label(
                    window_iv, text=f'{month}: '+str(df_dict[underlying_dict[month]]['Last']))
                globals()[f'label_und_{month}'].grid(row=crt_row, column=0)
                crt_row += 1
            tk.Label(
                window_iv, text=f'{get_und.get()} 平值iv:').grid(row=crt_row, column=0)
            crt_row += 1
            for i, month in enumerate(csd_month_list):
                pass

            # def delete_all():
            #     for i, month in enumerate(csd_month_list):
            #         obj_price = globals()[f'table_price{i}'].get_children()
            #         for o in obj_price:
            #             globals()[f'table_price{i}'].delete(o)
            #         obj_iv = globals()[f'table_iv{i}'].get_children()
            #         for o in obj_iv:
            #             globals()[f'table_iv{i}'].delete(o)

            def update():
                '''update price&iv data in treeview tables
                '''
                while True:
                    time.sleep(1)
                    self.get_adjusted_tau()
                    self.convert_df_dice_to_tabledata()
                    # delete_all()
                    global first_time
                    try:
                        first_time
                    except NameError:
                        first_time = True
                    if first_time:
                        for i, month in enumerate(csd_month_list):
                            for j, data in enumerate(tabledata_price_dict[month]):
                                globals()[f'table_price{i}'].insert(
                                    '', 'end', iid=f'price_{i}_{j}', values=data)
                            for j, data in enumerate(tabledata_iv_dict[month]):
                                globals()[f'table_iv{i}'].insert(
                                    '', 'end', iid=f'iv_{i}_{j}', values=data)
                            first_time = False
                    else:
                        for i, month in enumerate(csd_month_list):
                            for j, data in enumerate(tabledata_price_dict[month]):
                                globals()[f'table_price{i}'].item(
                                    f'price_{i}_{j}', values=data)
                            for j, data in enumerate(tabledata_iv_dict[month]):
                                globals()[f'table_iv{i}'].item(
                                    f'iv_{i}_{j}', values=data)
                    for i, month in enumerate(csd_month_list):
                        try:
                            globals()[f'label_und_{month}']['text'] = f'{month}: ' + \
                                str(df_dict[underlying_dict[month]]['Last'])
                        except AttributeError or TypeError:
                            pass
                    for i, month in enumerate(csd_month_list):
                        self.fit_wing(month)

            def monitor(window):
                window.after(100, update())

            t1 = threading.Thread(target=update)
            t2 = threading.Thread(target=monitor, args=(window_iv))
            t1.start()
            t2.start()
            window_iv.mainloop()

        tk.Label(self.window, text='选择品种').grid(row=self.row_num, column=0)
        get_und = ttk.Combobox(
            self. window, textvariable=tk.StringVar(), width=10)
        get_und['values'] = UND_TUPLE
        get_und.current(0)
        get_und.grid(row=self.row_num, column=1)
        self.row_num += 1
        tk.Label(self.window, text='获取合约').grid(row=self.row_num, column=0)
        tk.Button(self.window, text='开始获取', width=10, command=get_allsymbol_given_und_and_quote).grid(
            row=self.row_num, column=1, padx=1, pady=1)
        self.row_num += 1
        tk.Button(self.window, text='实时计算', width=10, command=cpt_iv_and_skew).grid(
            row=self.row_num, column=1, padx=1, pady=1)
        self.window.mainloop()


api = TCoreAPI(APIEvent)
re = api.connect()


def get_session_hour_number(session):
    '''get intraday trading period list given symbolsession
    '''
    re = []
    for time_str_couple in session.split(';'):
        for csd_str in time_str_couple.split('~'):
            re += [int(csd_str.split(':')[0])+int(csd_str.split(':')[1])/60]
    return re


def get_intraday_tau(session):
    '''get crt intraday left tau
    '''
    total_time = 0
    left_hour = 0
    jump_tag = False
    if time.localtime().tm_hour < 8:
        crt_hour = time.localtime().tm_hour+24-8+time.localtime().tm_min/60
    else:
        crt_hour = time.localtime().tm_hour-8+time.localtime().tm_min/60
    if crt_hour < 1:  # 早9点前, 今日记1
        return 1
    if 7 <= crt_hour < 13:  # 3点收盘后及晚9点开盘前, 今日记0
        return 0
    for i, csd_period in enumerate(session):
        if i % 2 or csd_period == session[-1]:
            continue
        total_time += session[i+1]-session[i]
        if not jump_tag:
            if session[i] <= crt_hour < session[i+1]:
                jump_tag = True
                left_hour += session[i+1]-crt_hour
            else:
                left_hour += 0
        else:
            left_hour += session[i+1]-session[i]
    return left_hour/total_time


symbol_session = {}
for und in UND_TUPLE[1:]:
    crt_session = api.getsymbol_session('TC.F.'+und+'.HOT')
    symbol_session[und] = get_session_hour_number(crt_session)


if __name__ == "__main__":
    my_com = CTA_OPT_MONITOR()
    my_com.main_window()
