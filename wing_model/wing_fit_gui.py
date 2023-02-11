import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from wing_model import fit_wing
from pylab import mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import warnings
import matplotlib.ticker as ticker
import numpy as np
mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False
warnings.simplefilter('ignore')


WIDTH_OF_ENTRY = 10
tick_spacing = 0.1
width = 1850
height = 600
strike_len = 30
window = tk.Tk()
window.title('wing model拟合')
screenwidth = window.winfo_screenwidth()
screenheight = window.winfo_screenheight()
size_geo = '%dx%d+%d+%d' % (width, height,
                            (screenwidth-width)/2, (screenheight-height)/2)
window.geometry(size_geo)

tk.Label(window, text="标的代码:").grid(row=0)
tk.Label(window, text="日期:").grid(row=1)
tk.Label(window, text="月份:").grid(row=2)
tk.Label(window, text="分钟节点:").grid(row=4)
tk.Label(window, text="dc(-0.05):").grid(row=6)
tk.Label(window, text="uc(0.08):").grid(row=7)
tk.Label(window, text="dsm(1):").grid(row=8)
tk.Label(window, text="usm(1):").grid(row=9)
# 创建输入框控件
# get_symbol = tk.Entry(window)


def go(*args):
    print(get_symbol.get())


get_symbol = ttk.Combobox(
    window, textvariable=tk.StringVar(), width=7)
get_symbol['values'] = ('510050', '510300', '510500', '159915')
get_symbol.current(0)
get_symbol.bind('<<ComboboxSelected>>', go)
get_date = tk.Entry(window, width=WIDTH_OF_ENTRY)
get_month = tk.Entry(window, width=WIDTH_OF_ENTRY)
get_min = tk.Entry(window, width=WIDTH_OF_ENTRY)
get_dc = tk.Entry(window, width=WIDTH_OF_ENTRY)
get_uc = tk.Entry(window, width=WIDTH_OF_ENTRY)
get_dsm = tk.Entry(window, width=WIDTH_OF_ENTRY)
get_usm = tk.Entry(window, width=WIDTH_OF_ENTRY)
# is_done = tk.Entry(window)
# get_symbol.grid(row=0, column=1)  # , padx=10, pady=5)
get_symbol.grid(row=0, column=1)
get_date.grid(row=1, column=1)  # , padx=10, pady=5)
get_month.grid(row=2, column=1)  # , padx=10, pady=5)
get_min.grid(row=4, column=1)
lb = tk.Label(window, text='iv拟合完毕!')
get_dc.grid(row=6, column=1)
get_uc.grid(row=7, column=1)
get_dsm.grid(row=8, column=1)
get_usm.grid(row=9, column=1)


def process_data():
    if get_dc.get() != '':
        globals()['dc'] = float(get_dc.get())
        globals()['uc'] = float(get_uc.get())
        globals()['dsm'] = float(get_dsm.get())
        globals()['usm'] = float(get_usm.get())
    else:
        globals()['dc'] = -0.05
        globals()['uc'] = 0.08
        globals()['dsm'] = 1
        globals()['usm'] = 1
    symbol = get_symbol.get()
    date = get_date.get()
    month = get_month.get()
    strike_array, aiyang_vol, fit_vol, aiyang_atm_iv, fit_atm_iv, board, is_arbitrage_free, fit_points = fit_wing(
        date=date, symbol=symbol, month=int(month), uc=uc, dc=dc, usm=usm, dsm=dsm)
    globals()['strike_array'] = strike_array
    globals()['aiyang_vol'] = aiyang_vol
    globals()['fit_vol'] = fit_vol
    globals()['aiyang_atm_iv'] = aiyang_atm_iv
    globals()['fit_atm_iv'] = fit_atm_iv
    globals()['board'] = board
    globals()['is_arbitrage_free'] = is_arbitrage_free
    globals()['fit_points'] = fit_points
    lb.grid(row=3, column=1)


def draw_iv():
    temp_min = get_min.get()
    globals()['crt_min'] = int(temp_min)
    f = Figure(figsize=(15, 6), dpi=100)
    a = f.add_subplot(1, 2, 1)
    temp_board = board.iloc[int(crt_min), :]
    temp_arbitrage = is_arbitrage_free[crt_min]
    a.plot(strike_array, aiyang_vol.iloc[int(temp_min), :], label='权分析iv')
    # a.plot(strike_array, fit_vol.iloc[int(
    #     temp_min), :], label='wing model拟合iv')
    x = np.linspace(strike_array[0], strike_array[-1], 300)
    temp_fit_points = fit_points.iloc[crt_min, :]
    a.plot(x, temp_fit_points, label='wing model拟合iv')
    a.set_title(
        f'{get_date.get()}第 {crt_min} 分钟, 艾扬iv与wing_model拟合iv对比, 无套利拟合{temp_arbitrage>0}\n当前合成期货: {temp_board[2]:.3f}, 艾扬atm_iv:{aiyang_atm_iv[crt_min]}, wing_model拟合atm_iv:{fit_atm_iv[crt_min]:.2f}')
    a.axvline(x=temp_board[0], ls="dotted", c="grey")
    a.axvline(x=temp_board[1], ls="dotted", c="green")
    a.axvline(x=temp_board[2], ls="-.", c="red")
    a.axvline(x=temp_board[3], ls="dotted", c="green")
    a.axvline(x=temp_board[4], ls="dotted", c="grey")
    a.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    a.legend()
    a.grid()
    b = f.add_subplot(1, 2, 2)
    b.plot(range(240), aiyang_atm_iv, label='权分析atm_iv', color='orange')
    b.plot(range(240), fit_atm_iv, label='wing_model拟合atm_iv', color='dodgerblue')
    b.axvline(x=crt_min, ls="-.", c="red")
    b.axhline(y=aiyang_atm_iv[crt_min], ls='--', c='orange')
    b.axhline(y=fit_atm_iv[crt_min], ls='--', c='dodgerblue')
    b.set_title(f'{get_date.get()}全天艾扬atm-iv与wing-model拟合atm-iv对比')
    b.legend()
    b.grid()
    canvas = FigureCanvasTkAgg(f, master=window)
    canvas.draw()  # 注意show方法已经过时了,这里改用draw
    # canvas.get_tk_widget().grid(row=10, column=3)  # 随窗口大小调整而调整
    canvas.get_tk_widget().grid(row=0, column=3, rowspan=400)  # 随窗口大小调整而调整


def next_min():
    get_min.delete(0, 10)
    globals()['crt_min'] = globals()['crt_min'] + 1
    temp_board = board.iloc[int(crt_min), :]
    f = Figure(figsize=(15, 6), dpi=100)
    a = f.add_subplot(1, 2, 1)
    temp_arbitrage = is_arbitrage_free[crt_min]
    a.plot(strike_array, aiyang_vol.iloc[int(
        globals()['crt_min']), :], label='权分析iv')
    # a.plot(strike_array, fit_vol.iloc[int(
    #     crt_min), :], label='wing model拟合iv')
    x = np.linspace(strike_array[0], strike_array[-1], 300)
    temp_fit_points = fit_points.iloc[crt_min, :]
    a.plot(x, temp_fit_points, label='wing model拟合iv')
    a.set_title(
        f'{get_date.get()}第 {crt_min} 分钟, 艾扬iv与wing_model拟合iv对比, 无套利拟合{temp_arbitrage>0}\n当前合成期货: {temp_board[2]:.3f}, 艾扬atm_iv:{aiyang_atm_iv[crt_min]}, wing_model拟合atm_iv:{fit_atm_iv[crt_min]:.2f}')
    a.axvline(x=temp_board[0], ls="dotted", c="grey")
    a.axvline(x=temp_board[1], ls="dotted", c="green")
    a.axvline(x=temp_board[2], ls="-.", c="red")
    a.axvline(x=temp_board[3], ls="dotted", c="green")
    a.axvline(x=temp_board[4], ls="dotted", c="grey")
    a.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    a.legend()
    a.grid()
    b = f.add_subplot(1, 2, 2)
    b.plot(range(240), aiyang_atm_iv, label='权分析atm_iv', color='orange')
    b.plot(range(240), fit_atm_iv, label='wing_model拟合atm_iv', color='dodgerblue')
    b.axvline(x=crt_min, ls="-.", c="red")
    b.axhline(y=aiyang_atm_iv[crt_min], ls='--', c='orange')
    b.axhline(y=fit_atm_iv[crt_min], ls='--', c='dodgerblue')
    b.set_title(f'{get_date.get()}全天艾扬atm-iv与wing-model拟合atm-iv对比')
    b.legend()
    b.grid()
    canvas = FigureCanvasTkAgg(f, master=window)
    canvas.draw()  # 注意show方法已经过时了,这里改用draw
    canvas.get_tk_widget().grid(row=0, column=3, rowspan=400)
    get_min.insert(0, str(crt_min))


def pre_min():
    get_min.delete(0, 10)
    globals()['crt_min'] = globals()['crt_min'] - 1
    temp_board = board.iloc[int(crt_min), :]
    f = Figure(figsize=(15, 6), dpi=100)
    a = f.add_subplot(1, 2, 1)
    temp_arbitrage = is_arbitrage_free[crt_min]
    a.plot(strike_array, aiyang_vol.iloc[int(
        globals()['crt_min']), :], label='权分析iv')
    x = np.linspace(strike_array[0], strike_array[-1], 300)
    temp_fit_points = fit_points.iloc[crt_min, :]
    a.plot(x, temp_fit_points, label='wing model拟合iv')
    a.set_title(
        f'{get_date.get()}第 {crt_min} 分钟, 艾扬iv与wing_model拟合iv对比, 无套利拟合{temp_arbitrage>0}\n当前合成期货: {temp_board[2]:.3f}, 艾扬atm_iv:{aiyang_atm_iv[crt_min]}, wing_model拟合atm_iv:{fit_atm_iv[crt_min]:.2f}')
    a.axvline(x=temp_board[0], ls="dotted", c="grey")
    a.axvline(x=temp_board[1], ls="dotted", c="green")
    a.axvline(x=temp_board[2], ls="-.", c="red")
    a.axvline(x=temp_board[3], ls="dotted", c="green")
    a.axvline(x=temp_board[4], ls="dotted", c="grey")
    a.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    a.legend()
    a.grid()
    b = f.add_subplot(1, 2, 2)
    b.plot(range(240), aiyang_atm_iv, label='权分析atm_iv', color='orange')
    b.plot(range(240), fit_atm_iv, label='wing_model拟合atm_iv', color='dodgerblue')
    b.axvline(x=crt_min, ls="-.", c="red")
    b.axhline(y=aiyang_atm_iv[crt_min], ls='--', c='orange')
    b.axhline(y=fit_atm_iv[crt_min], ls='--', c='dodgerblue')
    b.set_title(f'{get_date.get()}全天艾扬atm-iv与wing-model拟合atm-iv对比')
    b.legend()
    b.grid()
    canvas = FigureCanvasTkAgg(f, master=window)
    canvas.draw()  # 注意show方法已经过时了,这里改用draw
    canvas.get_tk_widget().grid(row=0, column=3, rowspan=400)
    get_min.insert(0, str(crt_min))


tk.Button(window, text="处理数据", width=10, command=process_data).grid(
    row=3, column=0, padx=1, pady=1)
tk.Button(window, text="作图", width=10, command=draw_iv).grid(
    row=5, column=0, padx=1, pady=1)
tk.Button(window, text="上一分钟", width=10, command=pre_min).grid(
    row=5, column=1, padx=1, pady=1)
tk.Button(window, text="下一分钟", width=10, command=next_min).grid(
    row=5, column=2, padx=1, pady=1)


window.mainloop()
