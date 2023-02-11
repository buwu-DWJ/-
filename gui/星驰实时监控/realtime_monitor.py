#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   realtime_monitor.py
@Time    :   2023/01/12 13:05:12
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   None
'''

import tkinter as tk
from tkinter import ttk
from multiprocessing import Process


def gui_0():
    window_0 = tk.Tk()
    window_0.title('窗口1')
    tk.Label(window_0, text='你好').grid(row=0, column=1)
    window_0.mainloop()


def gui_1():
    window_1 = tk.Tk()
    window_1.title('窗口2')
    tk.Label(window_1, text='你好').grid(row=0, column=1)
    window_1.mainloop()


if __name__ == "__main__":
    p1 = Process(target=gui_0)
    p2 = Process(target=gui_1)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
