from icetcore import TCoreAPI, QuoteEvent, TradeEvent
from functools import partial
from numpy import ndarray, array, arange, zeros, ones, argmin, minimum, maximum, log, exp
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from numpy.linalg import norm
from numpy.random import normal
from scipy.optimize import minimize
from pylab import mpl
import matplotlib.pyplot as plt
import numpy as np
import warnings
import time
import datetime
import threading
import tkinter as tk


mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
tick_spacing = 0.1
und = 'SSE.510050'
warnings.simplefilter('ignore')
TODAY_STR = datetime.date.today().strftime('%Y%m%d')


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

    def ongreeksreal(self, datatype, symbol, data: dict):
        df_dict[data['Symbol']] = data

    def onquote(self, data):
        synf_dict[data['Symbol']] = data['Last']


class wing_model_fit_realtime():
    def __init__(self):
        self.window = tk.Tk()
        self.canvas = tk.Canvas()
        self.row_num = 0
        self.figure = self.create_figure()
        self.show_canvas(self.figure)
        self.und = '510050'

    @staticmethod
    def fit_wing(month: int = 0, dc: float = -0.12, uc: float = 0.12, dsm: float = 0.5, usm: float = 0.5):
        temp_synf = synf_dict[underlying_dict[month]]
        wing_strike_array[month] = np.array(
            [float(a) for a in strike_dict[month]])
        symbol_list = symbol_dict[month]
        call_and_put_iv_list = [df_dict[symbol]['IV']
                                for symbol in symbol_list]
        wing_iv_array[month] = (np.array(call_and_put_iv_list[:int(len(
            call_and_put_iv_list)/2)])+np.array(call_and_put_iv_list[int(len(call_and_put_iv_list)/2):]))/2
        vega_array = np.array([df_dict[symbol]['Vega']
                              for symbol in symbol_list[:int(len(symbol_list)/2)]])*100
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

    def create_figure(self):
        fig = plt.figure(figsize=(20, 12))
        self.fig11 = plt.subplot(2, 2, 1)
        self.line111, = self.fig11.plot([], [])
        self.line112, = self.fig11.plot([], [])
        self.fig12 = plt.subplot(2, 2, 2)
        self.line121, = self.fig12.plot([], [])
        self.line122, = self.fig12.plot([], [])
        self.fig21 = plt.subplot(2, 2, 3)
        self.line211, = self.fig21.plot([], [])
        self.line212, = self.fig21.plot([], [])
        self.fig22 = plt.subplot(2, 2, 4)
        self.line221, = self.fig22.plot([], [])
        self.line222, = self.fig22.plot([], [])
        fig.tight_layout()
        return fig

    def update_figure(self):
        self.line111.set_xdata(wing_strike_array[list(symbol_dict.keys())[0]])
        self.line111.set_ydata(wing_iv_array[list(symbol_dict.keys())[0]])
        self.line112.set_xdata(wing_x[list(symbol_dict.keys())[0]])
        self.line112.set_ydata(wing_fit_points[list(symbol_dict.keys())[0]])

        self.line121.set_xdata(wing_strike_array[list(symbol_dict.keys())[1]])
        self.line121.set_ydata(wing_iv_array[list(symbol_dict.keys())[1]])
        self.line122.set_xdata(wing_x[list(symbol_dict.keys())[1]])
        self.line122.set_ydata(wing_fit_points[list(symbol_dict.keys())[1]])

        self.line211.set_xdata(wing_strike_array[list(symbol_dict.keys())[2]])
        self.line211.set_ydata(wing_iv_array[list(symbol_dict.keys())[2]])
        self.line212.set_xdata(wing_x[list(symbol_dict.keys())[2]])
        self.line212.set_ydata(wing_fit_points[list(symbol_dict.keys())[2]])

        self.line221.set_xdata(wing_strike_array[list(symbol_dict.keys())[3]])
        self.line221.set_ydata(wing_iv_array[list(symbol_dict.keys())[3]])
        self.line222.set_xdata(wing_x[list(symbol_dict.keys())[3]])
        self.line222.set_ydata(wing_fit_points[list(symbol_dict.keys())[3]])
        self.fig11.relim()
        self.fig11.autoscale_view()
        self.fig12.relim()
        self.fig12.autoscale_view()
        self.fig21.relim()
        self.fig21.autoscale_view()
        self.fig22.relim()
        self.fig22.autoscale_view()
        plt.draw()

    def show_canvas(self, figure):
        self.canvas = FigureCanvasTkAgg(figure, self.window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP)
        toolbar = NavigationToolbar2Tk(self.canvas, self.window)
        toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def show_figure(self):
        '''
        '''
        global df_dict
        global symbol_dict
        global strike_dict
        global synf_dict
        global maturity_dict
        global wing_strike_array
        global wing_iv_array
        global wing_fit_vol
        global wing_fit_atm_iv
        global wing_board
        global wing_x
        global wing_fit_points
        global underlying_dict
        synf_dict = {}
        df_dict = {}
        wing_strike_array = {}
        wing_iv_array = {}
        wing_fit_vol = {}
        wing_fit_atm_iv = {}
        wing_board = {}
        wing_fit_points = {}
        wing_x = {}
        symbol_dict = {}
        strike_dict = {}
        underlying_dict = {}
        maturity_dict = {}
        all_symbol = api.getallsymbol('OPT', und.split('.')[0])
        for symbol in all_symbol:
            if und in symbol:
                if symbol.split('.')[4] in symbol_dict.keys():
                    symbol_dict[symbol.split('.')[4]] += [symbol]
                    if '.'.join(symbol.split('.')[6:]) not in strike_dict[symbol.split('.')[4]]:
                        strike_dict[symbol.split(
                            '.')[4]] += ['.'.join(symbol.split('.')[6:])]
                else:
                    symbol_dict[symbol.split('.')[4]] = [symbol]
                    strike_dict[symbol.split('.')[4]] = [
                        '.'.join(symbol.split('.')[6:])]
        for key in symbol_dict.keys():
            for symbol in symbol_dict[key]:
                api.subgreeksreal(symbol)
        for i, month in enumerate(symbol_dict.keys()):
            maturity_dict[month] = api.getexpirationdate(
                symbol_dict[month][0])
            underlying_dict[month] = 'TC.F.U_' + und + '.' + month
            api.subquote(underlying_dict[month])
        self.window.title('wing_model实时拟合主窗口')
        time.sleep(1)

        def update():
            while True:
                time.sleep(1)
                for i, month in enumerate(symbol_dict.keys()):
                    self.fit_wing(month=month)
                self.update_figure()

        def monitor(window):
            window.after(100, update())

        t1 = threading.Thread(target=update)
        t2 = threading.Thread(target=monitor, args=(self.window))
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
        self.window.mainloop()


if __name__ == '__main__':
    api = TCoreAPI(APIEvent)
    re = api.connect()
    realtime = wing_model_fit_realtime()
    realtime.show_figure()
