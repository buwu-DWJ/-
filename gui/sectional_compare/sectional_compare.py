import tkinter as tk
from tkinter import ttk
import dwj_tools.read_hdf as r
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib import pyplot as plt


width = 1750
height = 850
strike_len = 30
window = tk.Tk()
window.title('期权截面对比')
screenwidth = window.winfo_screenwidth()
screenheight = window.winfo_screenheight()
size_geo = '%dx%d+%d+%d' % (width, height, (screenwidth-width)/2, (screenheight-height)/2)
window.geometry(size_geo)

tk.Label(window, text="标的代码:").grid(row=0)
tk.Label(window, text="日期1:").grid(row=1)
tk.Label(window, text="日期2:").grid(row=2)
tk.Label(window, text="分钟节点1:").grid(row=3)
tk.Label(window, text="分钟节点2:").grid(row=4)
# 创建输入框控件
get_symbol_0 = tk.Entry(window)
get_symbol_1 = tk.Entry(window)
get_date0 = tk.Entry(window)
get_date1 = tk.Entry(window)
get_range0 = tk.Entry(window)
get_range1 = tk.Entry(window)
get_symbol_0.grid(row=0, column=1)#, padx=10, pady=5)
get_symbol_1.grid(row=0, column=2)
get_date0.grid(row=1, column=1)#, padx=10, pady=5)
get_date1.grid(row=2, column=1)#, padx=10, pady=5)
get_range0.grid(row=3, column=1)#, padx=10, pady=5)
get_range1.grid(row=4, column=1)#, padx=10, pady=5)

def join_list(a, b):
    for i in b:
        if i not in a:
            a += [i]
    return a

def delete_0_1():
    obj = table_0.get_children()
    for o in obj[1:]:
        table_0.delete(o)
    obj = table_1.get_children()
    for o in obj[1:]:
        table_1.delete(o)

def delete_all():
    obj = table_0.get_children()
    for o in obj:
        table_0.delete(o)
    obj = table_1.get_children()
    for o in obj:
        table_1.delete(o)

def process_data():
    obj = table_2.get_children()
    for o in obj:
        table_2.delete(o)
    option_0, _, synf_0 = r.read_data_dogsk(get_symbol_0.get(), get_date0.get(), [int(get_range0.get())])
    option_1, _, synf_1 = r.read_data_dogsk(get_symbol_0.get(), get_date1.get(), [int(get_range1.get())])
    option_0 = option_0.reset_index(drop=True)
    option_1 = option_1.reset_index(drop=True)
    globals()['synf_0'] = synf_0
    globals()['synf_1'] = synf_1
    globals()['df_0'] = option_0
    globals()['df_1'] = option_1
    all_strike = []
    synf_str = ['近月date0','近月date1','次月date0','次月date1','季月date0','季月date1','远月date0','远月date1']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = option_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = option_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = option_0.iloc[list(option_0['tau'] == crt_tau_0)]
        true_option_1 = option_1.iloc[list(option_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        strike_list_0 = [float(a.split('.C.')[1]) for a in true_option_call_0['symbol']]
        strike_list_1 = [float(a.split('.C.')[1]) for a in true_option_call_1['symbol']]
        globals()[f'strike_list_0_{i}'] = strike_list_0
        globals()[f'strike_list_1_{i}'] = strike_list_1
        a = join_list(strike_list_0, strike_list_1)
        all_strike = join_list(all_strike, a)
        s_0 = [round(a,4) if i!=0 and i!=1 else round(a*10000,4) for i,a in enumerate(synf_0.iloc[0,i*9:i*9+9])]+[round((float(synf_0.iloc[0,i*9])-float(synf_0.iloc[0,i*9+1]))*10000,4), round((float(synf_0.iloc[0,i*9])+float(synf_0.iloc[0,i*9+1]))*10000,4)]
        s_1 = [round(a,4) if i!=0 and i!=1 else round(a*10000,4) for i,a in enumerate(synf_1.iloc[0,i*9:i*9+9])]+[round((float(synf_1.iloc[0,i*9])-float(synf_1.iloc[0,i*9+1]))*10000,4), round((float(synf_1.iloc[0,i*9])+float(synf_1.iloc[0,i*9+1]))*10000,4)]
        table_2.insert(parent='', index=i*2, text=synf_str[i*2],values=[synf_str[i*2]]+s_0)
        table_2.insert(parent='', index=i*2+1, text=synf_str[i*2+1],values=[synf_str[i*2+1]]+s_1)
    all_strike = list(np.sort(np.array(all_strike)))
    globals()['strike'] = all_strike
    option_0 = option_0.reset_index(drop=True)
    table_0.insert(parent='',index=0,text='',values=['']+all_strike+['']*(strike_len-len(all_strike)))
    table_1.insert(parent='',index=0,text='',values=['']+all_strike+['']*(strike_len-len(all_strike)))


def draw_iv():
    root = tk.Tk()  # 创建tkinter的主窗口
    root.title("在tkinter中使用matplotlib")

    f = Figure(figsize=(15, 8), dpi=100)
    tau_list_0 = list(df_0['tau'].drop_duplicates())
    tau_list_1 = list(df_1['tau'].drop_duplicates())
    month_str = ['近月', '次月', '季月', '远月']
    for i in range(4):
        a = f.add_subplot(2,2,i+1)  # 添加子图:1行1列第1个
        b = list(df_0['tau']==tau_list_0[i])
        c = list(df_0['flag']=='C')
        d = [b[i] and c[i] for i in range(len(b))]
        iv_call = np.array(df_0.iloc[d,:]['iv'])
        b = list(df_0['tau']==tau_list_0[i])
        c = list(df_0['flag']=='P')
        d = [b[i] and c[i] for i in range(len(b))]
        iv_put = np.array(df_0.iloc[d,:]['iv'])
        iv = (iv_call + iv_put)/2
        a.plot(globals()[f'strike_list_0_{i}'], iv, label=f'df1{month_str[i]}')
        b = list(df_1['tau']==tau_list_1[i])
        c = list(df_1['flag']=='C')
        d = [b[i] and c[i] for i in range(len(b))]
        iv_call = np.array(df_1.iloc[d,:]['iv'])
        b = list(df_1['tau']==tau_list_1[i])
        c = list(df_1['flag']=='P')
        d = [b[i] and c[i] for i in range(len(b))]
        iv_put = np.array(df_1.iloc[d,:]['iv'])
        iv = (iv_call + iv_put)/2
        a.plot(globals()[f'strike_list_1_{i}'], iv, label=f'df2{month_str[i]}')
        a.legend()
        a.grid()
    # 将绘制的图形显示到tkinter:创建属于root的canvas画布,并将图f置于画布上
    canvas = FigureCanvasTkAgg(f, master=root)
    canvas.draw()  # 注意show方法已经过时了,这里改用draw
    canvas.get_tk_widget().pack(side=tk.TOP,  # 上对齐
                                fill=tk.BOTH,  # 填充方式
                                expand=tk.YES)  # 随窗口大小调整而调整

    # matplotlib的导航工具栏显示上来(默认是不会显示它的)
    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    canvas._tkcanvas.pack(side=tk.TOP,  # get_tk_widget()得到的就是_tkcanvas
                          fill=tk.BOTH,
                          expand=tk.YES)


def match_strike(all_strike, temp_strike):
    id_list = []
    for i in temp_strike:
        if i in all_strike:
            id_list += [i]
    return id_list


def sort_data(all_strike, temp_strike, data):
    id_list = []
    for i, csd_strike in enumerate(temp_strike):
        id_list += [all_strike.index(csd_strike)]
    new_data = []
    count = 0
    for i, _ in enumerate(all_strike):
        if i in id_list:
            new_data += [round(data[count],4)]
            count += 1
        else:
            new_data += ['']
    return new_data


def get_close():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['close']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['close']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['close']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['close']))


def get_iv():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['iv']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['iv']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['iv']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['iv']))


def get_delta():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['delta']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['delta']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['delta']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['delta']))


def get_gamma():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['gamma']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['gamma']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['gamma']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['gamma']))


def get_vega():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['vega']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['vega']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['vega']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['vega']))


def get_vanna():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['vanna']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['vanna']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['vanna']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['vanna']))


def get_theta():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['theta']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['theta']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['theta']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['theta']))


def get_charm():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['charm']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['charm']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['charm']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['charm']))


def get_vomma():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['vomma']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['vomma']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['vomma']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['vomma']))


def get_speed():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['speed']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['speed']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['speed']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['speed']))


def get_zomma():
    delete_0_1()
    month_list = ['近月','次月','季月','远月']
    for i in range(4):
        strike_list_0 = []
        strike_list_1 = []
        crt_tau_0 = df_0['tau'].drop_duplicates(keep='first').tolist()[i]
        crt_tau_1 = df_1['tau'].drop_duplicates(keep='first').tolist()[i]
        true_option_0 = df_0.iloc[list(df_0['tau'] == crt_tau_0)]
        true_option_1 = df_1.iloc[list(df_1['tau'] == crt_tau_1)]
        true_option_call_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'C'), :].reset_index(drop=True)
        true_option_call_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'C'), :].reset_index(drop=True)
        true_option_put_0 = true_option_0.loc[list(
        true_option_0['flag'] == 'P'), :].reset_index(drop=True)
        true_option_put_1 = true_option_1.loc[list(
        true_option_1['flag'] == 'P'), :].reset_index(drop=True)
        table_0.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_call_0['zomma']))
        table_0.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_0_{i}'],true_option_put_0['zomma']))
        table_1.insert(parent='',index=1+2*i,text='',values=[month_list[i]+'call']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_call_1['zomma']))
        table_1.insert(parent='',index=2+2*i,text='',values=[month_list[i]+'put']+sort_data(strike,globals()[f'strike_list_1_{i}'],true_option_put_1['zomma']))


columns = ['月份']+[f'K{i}' for i in range(strike_len)]
table_0 = ttk.Treeview(
        master=window,  # 父容器
        height=9,  # 表格显示的行数,height行
        columns=columns,  # 显示的列
        show='headings',  # 隐藏首列
        )
table_0.heading(column='月份', text='月份', #anchor='c',
              command=lambda: print('月份'))  # 定义表头
for i in range(strike_len):
    table_0.heading(f'K{i}', text=f'K{i}', )  # 定义表头
table_0.column('月份', width=60, minwidth=9, anchor='s', )  # 定义列
for i in range(strike_len):
    table_0.column(f'K{i}', width=50, minwidth=9, anchor='s')  # 定义列
table_0.grid(row=6, columnspan=strike_len, padx=5, pady=10)
table_1 = ttk.Treeview(
        master=window,  # 父容器
        height=9,  # 表格显示的行数,height行
        columns=columns,  # 显示的列
        show='headings',  # 隐藏首列
        )
table_1.heading(column='月份', text='月份', #anchor='c',
              command=lambda: print('月份'))  # 定义表头
for i in range(strike_len):
    table_1.heading(f'K{i}', text=f'K{i}', )  # 定义表头
table_1.column('月份', width=60, minwidth=9, anchor='s', )  # 定义列
for i in range(strike_len):
    table_1.column(f'K{i}', width=50, minwidth=9, anchor='s')  # 定义列
table_1.grid(row=7, columnspan=strike_len, padx=5, pady=10)
columns_synf = ['月份','cskew','pskew','tau','iv','synf_c','civ_25','piv_25','civ_10','piv_10','skew','kurt']
table_2 = ttk.Treeview(
        master=window,  # 父容器
        height=9,  # 表格显示的行数,height行
        columns=columns_synf,  # 显示的列
        show='headings',  # 隐藏首列
        )
table_2.heading(column='月份', text='月份', anchor='c',
              command=lambda: print('月份'))  # 定义表头
for i in columns_synf[1:]:
    table_2.heading(i, text=i, )  # 定义表头
table_2.column('月份', width=75, minwidth=9, anchor='s', )  # 定义列
for i in columns_synf[1:]:
    table_2.column(i, width=55, minwidth=9, anchor='s')  # 定义列
table_2.grid(row=8, columnspan=3, padx=5, pady=10)




tk.Button(window, text="处理数据", width=25, command=process_data).grid(row=5, column=0, padx=1, pady=1)
tk.Button(window, text="清除所有", width=10, command=delete_all).grid(row=5, column=1, padx=1, pady=1)
for i, csd_obj in enumerate(['close','iv','delta','gamma','vega','vanna','theta','charm','vomma','speed','zomma']):
    tk.Button(window, text=csd_obj, width=10, command=locals()[f'get_{csd_obj}']).grid(row=5, column=2+i, padx=1, pady=1)
tk.Button(window, text='iv曲线', width=10, command=draw_iv).grid(row=5, column=13, padx=1, pady=1)








window.mainloop()