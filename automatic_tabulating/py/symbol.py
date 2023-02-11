# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 14:05:50 2019

@author: 95345
"""

import pandas as pd
from WindPy import *
w.start()

c9 = "10001677.SH,10001678.SH,10001679.SH,10001680.SH,10001681.SH,10001682.SH,10001683.SH,10001684.SH,10001685.SH,10001697.SH,10001701.SH,10001709.SH,10001717.SH,10001743.SH,10001744.SH,10001745.SH,10001746.SH,10001801.SH,10001809.SH,10001817.SH,10001825.SH"
c9 = c9.split(',')
p9 = "10001686.SH,10001687.SH,10001688.SH,10001689.SH,10001690.SH,10001691.SH,10001692.SH,10001693.SH,10001694.SH,10001698.SH,10001702.SH,10001710.SH,10001718.SH,10001747.SH,10001748.SH,10001749.SH,10001750.SH,10001802.SH,10001810.SH,10001818.SH,10001826.SH"
p9 = p9.split(',')

c12 = "10001827.SH,10001828.SH,10001829.SH,10001830.SH,10001831.SH,10001832.SH,10001833.SH,10001834.SH,10001835.SH,10001845.SH,10001847.SH,10001848.SH,10001851.SH,10001853.SH,10001907.SH"
c12 = c12.split(',')
p12 = "10001836.SH,10001837.SH,10001838.SH,10001839.SH,10001840.SH,10001841.SH,10001842.SH,10001843.SH,10001844.SH,10001846.SH,10001849.SH,10001850.SH,10001852.SH,10001854.SH,10001908.SH"
p12 = p12.split(',')

c7 = "10001855.SH,10001856.SH,10001857.SH,10001858.SH,10001859.SH,10001860.SH,10001861.SH,10001862.SH,10001863.SH,10001873.SH,10001875.SH,10001877.SH,10001879.SH,10001880.SH,10001903.SH"
c7 = c7.split(',')
p7 = "10001864.SH,10001865.SH,10001866.SH,10001867.SH,10001868.SH,10001869.SH,10001870.SH,10001871.SH,10001872.SH,10001874.SH,10001876.SH,10001878.SH,10001881.SH,10001882.SH,10001904.SH"
p7 = p7.split(',')

c8 = "10001883.SH,10001884.SH,10001885.SH,10001886.SH,10001887.SH,10001888.SH,10001889.SH,10001890.SH,10001891.SH,10001901.SH,10001905.SH"
c8 = c8.split(',')
p8 = "10001892.SH,10001893.SH,10001894.SH,10001895.SH,10001896.SH,10001897.SH,10001898.SH,10001899.SH,10001900.SH,10001902.SH,10001906.SH"
p8 = p8.split(',')
c = c9+p9+c12+p12+c7+p7+c8+p8

df = pd.DataFrame({'Call':[c9,c12,c7,c8],'Put':[p9,p12,p7,p8]})

'''
error,datac1=w.wsq(c7,"rt_bid1,rt_ask1",usedf=True)
error,datac2=w.wss(c7,"exe_price,exe_enddate,exe_mode",usedf=True)
datac = pd.concat([datac1,datac2],axis=1)

error,datap1=w.wsq(p7,"rt_bid1,rt_ask1",usedf=True)
error,datap2=w.wss(p7,"exe_price,exe_enddate,exe_mode",usedf=True)
datap = pd.concat([datap1,datap2],axis=1)
'''

def LoadData(symbols):
    error,data1=w.wsq(symbols,"rt_bid1,rt_ask1",usedf=True)
    error,data2=w.wss(symbols,"exe_price,exe_enddate,exe_mode",usedf=True)
    return(pd.concat([data1,data2],axis=1))


#datac = LoadData(c7)
#datap = LoadData(p7)


#五个最小的
def CalSynFuturePrice(TC1,TP1):   #算合成期货的价格,行权价格在第几列！！
    premium1=list(0.5*(TC1['RT_BID1']+TC1['RT_ASK1']))
    premium2=list(0.5*(TP1['RT_BID1']+TP1['RT_ASK1']))
    diff=abs(pd.Series(premium1)-pd.Series(premium2)) 
    index = diff.nsmallest(5).index.values
    
    p = []
    for i in index:
        p.append(premium1[i]+TC1.values[i,2]-premium2[i])
    PriceSyn=sum(p)/5  
    return(PriceSyn)


def RemainingDays(enddate):
    from datetime import datetime
    import time
    
    today = datetime.today()
    days = w.tdayscount(today, enddate,"")
    days = days.Data[0][0]
    
    h = int(time.strftime("%H",time.localtime()))
    m = int(time.strftime("%M",time.localtime()))
    s = int(time.strftime("%S",time.localtime()))
    t = h+m/60+s/3600
    if t<9.5:
        t0 = 4
    if t>=9.5 and t<11.5:
        t0 = 2 + 11.5-t
    if t>=11.5 and t<13:
        t0 = 2
    if t>=13 and t<15:
        t0 = 15-t
    if t>=15:
        t0 = 0
    
    return((days-1+t0/4)/243)


def CalIV(datac, datap):
    import time
    import Lib_OptionCalculator2 
 
    S = CalSynFuturePrice(datac,datap)
    AIVc = []
    BIVc = []
    AIVp = []
    BIVp = []
    IVc = []
    IVp = []
    Deltac = []
    Deltap = []
    Gammac = []
    Gammap = []
    
    T = RemainingDays(datac['EXE_ENDDATE'][0])
    for i in range(len(datac)):
        K = datac['EXE_PRICE'][i]
        c1 = datac['RT_ASK1'][i]
        c2 = datac['RT_BID1'][i]
        p1 = datap['RT_ASK1'][i]
        p2 = datap['RT_BID1'][i]
        
        AIVc.append(Lib_OptionCalculator2.CalIVCall(S,K,T,0,c1))
        BIVc.append(Lib_OptionCalculator2.CalIVCall(S,K,T,0,c2))
        AIVp.append(Lib_OptionCalculator2.CalIVPut(S,K,T,0,p1))
        BIVp.append(Lib_OptionCalculator2.CalIVPut(S,K,T,0,p2))
        IVc.append((AIVc[i]+BIVc[i])*0.5)
        IVp.append((AIVp[i]+BIVp[i])*0.5)
        Deltac.append(Lib_OptionCalculator2.CalDeltaCall(S,K,T,0,IVc[i]))
        Deltap.append(Lib_OptionCalculator2.CalDeltaPut(S,K,T,0,IVp[i]))
        Gammac.append(Lib_OptionCalculator2.CalGammaCall(S,K,T,0,IVc[i]))
        Gammap.append(Lib_OptionCalculator2.CalGammaPut(S,K,T,0,IVp[i]))
    
    datac['BIV'] = BIVc
    datac['AIV'] = AIVc
    datap['BIV'] = BIVp
    datap['AIV'] = AIVp
    datac['IV'] = IVc
    datap['IV'] = IVp
    datac['Delta'] = Deltac
    datap['Delta'] = Deltap
    datac['Gamma'] = Gammac
    datap['Gamma'] = Gammap
    return(pd.concat([datac,datap]))

'''
def PutIV(data):
    AIV = []
    BIV = []
    
    for i in range(len(data)):
        T = RemainingDays(data['EXE_ENDDATE'][i])
        K = data['EXE_PRICE'][i]
        p1 = data['RT_ASK1'][i]
        p2 = data['RT_BID1'][i]
        AIV.append(Lib_OptionCalculator2.CalIVPut(S,K,T,0,p1))
        BIV.append(Lib_OptionCalculator2.CalIVPut(S,K,T,0,p2))
    
    data['BIV'] = BIV
    data['AIV'] = AIV
'''


#data = CalIV(datac,datap)

    
