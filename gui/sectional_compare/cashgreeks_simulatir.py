import tkinter as tk
from tkinter import ttk
import dwj_tools.read_hdf as r
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from tkinter import messagebox



width = 1750
height = 850
strike_len = 30
window = tk.Tk()
window.title('cashgreeks模拟')
screenwidth = window.winfo_screenwidth()
screenheight = window.winfo_screenheight()
size_geo = '%dx%d+%d+%d' % (width, height, (screenwidth-width)/2, (screenheight-height)/2)
window.geometry(size_geo)


tk.Label(window, text="标的代码:").grid(row=0)
tk.Label(window, text="日期1:").grid(row=1)
tk.Label(window, text="日期2:").grid(row=2)
tk.Label(window, text="分钟节点1:").grid(row=3)
tk.Label(window, text="分钟节点2:").grid(row=4)
tk.Label(window, text="月份:").grid(row=0, column=2)
# 创建输入框控件
get_symbol = tk.Entry(window)
get_date0 = tk.Entry(window)
get_date1 = tk.Entry(window)
get_range0 = tk.Entry(window)
get_range1 = tk.Entry(window)
get_vega = tk.Entry(window)
get_vanna = tk.Entry(window)
get_gamma = tk.Entry(window)
get_month = tk.Entry(window)
get_symbol.grid(row=0, column=1)#, padx=10, pady=5)
get_date0.grid(row=1, column=1)#, padx=10, pady=5)
get_date1.grid(row=2, column=1)#, padx=10, pady=5)
get_range0.grid(row=3, column=1)#, padx=10, pady=5)
get_range1.grid(row=4, column=1)#, padx=10, pady=5)
get_month.grid(row=0, column=3)
get_vega.grid(row=5, column=1)
tk.Label(window, text="vega:").grid(row=5)
get_vanna.grid(row=5, column=3)
tk.Label(window, text="vanna:").grid(row=5, column=2)
get_gamma.grid(row=5, column=5)
tk.Label(window, text="gamma:").grid(row=5, column=4)


def get_option_code(df, greeks_type, month):
    tol= 0.1
    csd_tau = df['tau'].drop_duplicates().values[month]
    csd_df = df.iloc[df.index[df['tau'] == csd_tau], :]
    true_option_call = csd_df.loc[list(
        csd_df['flag'] == 'C'), :].reset_index(drop=True)
    true_option_put = csd_df.loc[list(
        csd_df['flag'] == 'P'), :].reset_index(drop=True)
    if greeks_type=='vega' or greeks_type=='gamma':
        code_list = ['', '']
        id_call_50 = np.abs(true_option_call['delta']-0.5).argmin()
        id_put_50 = np.abs(true_option_put['delta']+0.5).argmin()
        code_call_50 = true_option_call['symbol'][id_call_50]
        code_put_50 = true_option_put['symbol'][id_put_50]
        globals()['call_50_delta_0'] = true_option_call['delta'].values[id_call_50]
        globals()['put_50_delta_0'] = true_option_put['delta'].values[id_put_50]
        delta_list = [call_50_delta_0, put_50_delta_0]
        if np.abs(call_50_delta_0-0.5)>tol or np.abs(put_50_delta_0+0.5)>tol:
            messagebox.showinfo(title='提示', message=f'delta超出限制')
            return code_list




def process_data():
    cash = 10000000
    month = get_month.get()
    globals()['aaa'] = month
    option_0, und_0, synf_0 = r.read_data_dogsk(get_symbol.get(), get_date0.get(), [int(get_range0.get())])
    option_1, und_1, synf_1 = r.read_data_dogsk(get_symbol.get(), get_date1.get(), [int(get_range1.get())])
    if get_vega.get()!='':
        greeks_type = 'vega'
        cash_vega = cash * get_vega.get()

    elif get_vanna.get()!='':
        greeks_type = 'vanna'
        cash_vanna = cash * get_vanna.get()
        code_list, delta_list = get_option_code(option_0, greeks_type, month)

    elif get_gamma.get()!='':
        greeks_type = 'gamma'
        cash_gamma = cash * get_gamma.get()
    # messagebox.showinfo(title='提示', message=f'你输入的是{get_month.get()}')
    return

tk.Button(window, text="计算", width=25, command=process_data).grid(row=5, column=6, padx=1, pady=1)













window.mainloop()