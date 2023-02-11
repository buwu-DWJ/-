# -*- coding: utf-8 -*-
"""
Created on Fri Jul 26 09:18:59 2019

@author: 95345
"""
import pandas as pd
#import numpy as np
from WindPy import *
w.start()
contracts = w.wset("optionchain","us_code=159919.SZ;option_var=全部;call_put=全部").Data[3]

#contracts = w.wset("optioncontractbasicinfo","exchange=SZSE;windcode=159919.SZ;status=trading;field=wind_code").Data[0]
#for i in range(len(contracts)):
#    contracts[i] = contracts[i] + '.SZ'

def form(date):
    from dateutil.parser import parse
    return(parse(str(date)).strftime('%Y/%m/%d'))

def LoadData(symbols):
    from datetime import datetime
    error,data1=w.wsq(symbols,"rt_bid1,rt_ask1",usedf=True)
    error,data2=w.wss(symbols,"exe_price,exe_enddate,exe_mode,exe_ratio",usedf=True)
    data = pd.concat([data1,data2],axis=1)
    #data.insert(0,'Contract',list(data.index))
    #data.index = np.arange(len(data))
    data = data.replace('认购','call')
    data = data.replace('认沽','put')
    #data['Endday'] = data['EXE_ENDDATE']
    data['EXE_ENDDATE'] = data['EXE_ENDDATE'].apply(form)
    error,c = w.wss(contracts, "close,pre_close","tradeDate="+datetime.today().strftime('%Y%m%d') +";priceAdj=U;cycle=D", usedf=True)
    #data['50ETF'] = w.wsq('510300.SH','rt_bid1').Data[0][0]
    data0 = pd.concat([data,c],axis=1)
    return(data0)


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
    
    num =244
    today = datetime.today()
    
    tradeday = pd.read_excel('TradeDay.xls')
    selected = tradeday.loc[ (tradeday['date'] > today) & (tradeday['date'] <= enddate)]
    days = len(selected)
   
    #days = w.tdayscount(today, enddate,"")
    #days = days.Data[0][0]
    
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
    
    return((days+t0/4)/num)


def CalGreeks(datac, datap):
    import time
    import Lib_OptionCalculator as oc
 
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
    Vegac = []
    Vegap = []
    Thetac = []
    Thetap = []
    t = []
    s = []
    Vannac = []
    Vannap = []
    Charmc = []
    Charmp = []
    Vommac = []
    Vommap = []
    Speedc = []###########################################
    Speedp = []###########################################
    Zommac = []###########################################
    Zommap = []###########################################
    
    
    datac0 = datac.copy()
    datap0 = datap.copy()
    
    if RemainingDays(datac['EXE_ENDDATE'].iloc[0]) > 0:
        T = RemainingDays(datac['EXE_ENDDATE'].iloc[0])
    else:
        T = 0.000001
    
    for i in range(len(datac)):
        K = datac0['EXE_PRICE'].iloc[i]
        c1 = datac0['RT_ASK1'].iloc[i]
        c2 = datac0['RT_BID1'].iloc[i]
        p1 = datap0['RT_ASK1'].iloc[i]
        p2 = datap0['RT_BID1'].iloc[i]
        
        t.append(T)
        s.append(S)
        AIVc.append(oc.CalIVCall(S,K,T,0,c1))
        BIVc.append(oc.CalIVCall(S,K,T,0,c2))
        AIVp.append(oc.CalIVPut(S,K,T,0,p1))
        BIVp.append(oc.CalIVPut(S,K,T,0,p2))

        if BIVc[i] == 0.0001:
            IVc.append(AIVc[i])
        if (AIVc[i] == 0.0001) and (BIVc[i] > 0.0001):
            IVc.append(BIVc[i])
        if (AIVc[i] > 0.0001) and (BIVc[i] > 0.0001):
            IVc.append((AIVc[i]+BIVc[i])*0.5)
        
        if BIVp[i] == 0.0001:
            IVp.append(AIVp[i])
        if (AIVp[i] == 0.0001) and (BIVp[i] > 0.0001):
            IVp.append(BIVp[i])
        if (AIVp[i] > 0.0001) and (BIVp[i] > 0.0001):
            IVp.append((AIVp[i]+BIVp[i])*0.5)
        
        Deltac.append(oc.CalDeltaCall(S,K,T,0,IVc[i]))
        Deltap.append(oc.CalDeltaPut(S,K,T,0,IVp[i]))
        Gammac.append(oc.CalGammaCallPct(S,K,T,0,IVc[i]))
        Gammap.append(oc.CalGammaPutPct(S,K,T,0,IVp[i]))
        Vegac.append(oc.CalVegaCall(S,K,T,0,IVc[i]))
        Vegap.append(oc.CalVegaPut(S,K,T,0,IVp[i]))
        Thetac.append(oc.CalThetaCall(S,K,T,0,IVc[i]))
        Thetap.append(oc.CalThetaPut(S,K,T,0,IVp[i]))
        Vannac.append(oc.CalVannaCallPct(S,K,T,0,IVc[i]))
        Vannap.append(oc.CalVannaPutPct(S,K,T,0,IVp[i]))
        Charmc.append(oc.CalCharmCall(S,K,T,0,IVc[i]))
        Charmp.append(oc.CalCharmPut(S,K,T,0,IVp[i]))
        Vommac.append(oc.CalVommaCall(S,K,T,0,IVc[i]))
        Vommap.append(oc.CalVommaPut(S,K,T,0,IVp[i]))
        Speedc.append(oc.CalSpeedCallPct(S,K,T,0,IVc[i]))######################################################
        Speedp.append(oc.CalSpeedPutPct(S,K,T,0,IVp[i]))##################################################
        Zommac.append(oc.CalZommaCallPct(S,K,T,0,IVc[i]))######################################################
        Zommap.append(oc.CalZommaPutPct(S,K,T,0,IVp[i]))##################################################
    
    datac0['T'] = t
    datap0['T'] = t
    datac0['S'] = s
    datap0['S'] = s
    datac0['BIV'] = BIVc
    datac0['AIV'] = AIVc
    datap0['BIV'] = BIVp
    datap0['AIV'] = AIVp
    datac0['Implied Volatility'] = IVc
    datap0['Implied Volatility'] = IVp
    datac0['DELTA'] = Deltac
    datap0['DELTA'] = Deltap
    datac0['GAMMA'] = Gammac
    datap0['GAMMA'] = Gammap
    datac0['SPEED'] = Speedc#####################
    datap0['SPEED'] = Speedp####################################
    datac0['ZOMMA'] = Zommac#####################
    datap0['ZOMMA'] = Zommap####################################
    datac0['THETA'] = Thetac
    datap0['THETA'] = Thetap
    datac0['VEGA'] = Vegac
    datap0['VEGA'] = Vegap
    datac0['VANNA'] = Vannac
    datap0['VANNA'] = Vannap
    datac0['CHARM'] = Charmc
    datap0['CHARM'] = Charmp
    datac0['VOMMA'] = Vommac
    datap0['VOMMA'] = Vommap
    datac0['SPEED'] = Speedc#####################
    datap0['SPEED'] = Speedp####################################
    datac0['ZOMMA'] = Zommac#####################
    datap0['ZOMMA'] = Zommap####################################
    
    sc = oc.CalSkewV5(1,datac0)
    sp = oc.CalSkewV5(-1,datap0)
    datac0['SKEW'] = [sc for i in range(len(datac))]
    datap0['SKEW'] = [sp for i in range(len(datac))]
    
    data0 = pd.concat([datac0,datap0])
    data0.insert(0,'Contract',list(data0.index))
    data0.index = [i for i in range(len(data0))]#np.arange(len(datac))
    
    return(data0)


def skew_per(df, interval = 60):
    tmp = df.iloc[len(df)-interval-1:len(df),:]
    tmpc1 = list(tmp['cskew1'].sort_values(ascending = True))
    tmpc2 = list(tmp['cskew2'].sort_values(ascending = True))
    tmpc3 = list(tmp['cskew3'].sort_values(ascending = True))
    tmpc4 = list(tmp['cskew4'].sort_values(ascending = True))
    tmpp1 = list(tmp['pskew1'].sort_values(ascending = True))
    tmpp2 = list(tmp['pskew2'].sort_values(ascending = True))
    tmpp3 = list(tmp['pskew3'].sort_values(ascending = True))
    tmpp4 = list(tmp['pskew4'].sort_values(ascending = True))
    c1_per = tmpc1.index(tmp['cskew1'].iloc[-1]) / (interval+1)
    c2_per = tmpc2.index(tmp['cskew2'].iloc[-1]) / (interval+1)
    c3_per = tmpc3.index(tmp['cskew3'].iloc[-1]) / (interval+1)
    c4_per = tmpc4.index(tmp['cskew4'].iloc[-1]) / (interval+1)
    p1_per = tmpp1.index(tmp['pskew1'].iloc[-1]) / (interval+1)
    p2_per = tmpp2.index(tmp['pskew2'].iloc[-1]) / (interval+1)
    p3_per = tmpp3.index(tmp['pskew3'].iloc[-1]) / (interval+1)
    p4_per = tmpp4.index(tmp['pskew4'].iloc[-1]) / (interval+1)
    
    return(pd.DataFrame({"c_per":[c1_per,c2_per,c3_per,c4_per],"p_per":[p1_per,p2_per,p3_per,p4_per]}))
    #c_per = [c1_per,c2_per,c3_per,c4_per]
    #p_per = [p1_per,p2_per,p3_per,p4_per]
    

def iv_per(df, interval=100):
    tmp = df.iloc[len(df)-interval-1:len(df),:]
    tmpc1 = list(tmp['Implied Volatility 1'].sort_values(ascending = True))
    tmpc2 = list(tmp['Implied Volatility 2'].sort_values(ascending = True))
    tmpc3 = list(tmp['Implied Volatility 3'].sort_values(ascending = True))
    tmpc4 = list(tmp['Implied Volatility 4'].sort_values(ascending = True))
    iv1_per = tmpc1.index(tmp['Implied Volatility 1'].iloc[-1]) / (interval+1)
    iv2_per = tmpc2.index(tmp['Implied Volatility 2'].iloc[-1]) / (interval+1)
    iv3_per = tmpc3.index(tmp['Implied Volatility 3'].iloc[-1]) / (interval+1)
    iv4_per = tmpc4.index(tmp['Implied Volatility 4'].iloc[-1]) / (interval+1)
    
    return([iv1_per,iv2_per,iv3_per,iv4_per])


def LoadHV(interval=130):
    error,data = w.wsd("159919.SZ", "close,open,high,low", w.tdaysoffset(-interval).Data[0][0], w.tdaysoffset(-1).Data[0][0],  usedf=True) 
    return(data)

def FindMonth(name):
    '''
    if len(name) == 12:
        return('0' + name[6])
    if len(name) == 13:
        return(name[6] + name[7])
        '''
    end = name.find('月')
    month = name[7:end]
    if len(month) == 1:
        month = '0' +month
    else:
        month = month
    return(month)
    

def LoadPosition(name):
    df1 = pd.read_csv(name,encoding = "gbk")
    
    position = []
    for i in range(len(df1)):
        if df1['买卖'].iloc[i] == '卖':
            position.append(- df1['持仓'].iloc[i])
        if df1['买卖'].iloc[i] == '买':
            position.append(df1['持仓'].iloc[i])
    df1['Position'] = position
    df1['Contract'] = df1['代码'].apply(str) + '.SZ'
    df1['Month'] = df1['名称'].apply(FindMonth)
    
    return(df1)

def LoadVolume(name):
    df2 = pd.read_csv(name,encoding = "gbk")
    print(df2)
    position = []
    for i in range(len(df2)):
        if df2['买卖'].iloc[i] == '卖' :
            position.append(- df2['成交数量'].iloc[i]) 
        else:
            position.append( df2['成交数量'].iloc[i])
    df2['Position'] = position
    df2['Contract'] = df2['合约代码'].apply(str) + '.SZ'
    df2['Month'] = df2['合约名称'].apply(FindMonth)
    
    return(df2)

def Reconstruct(df, date, strike, c_p):
    #c1 = [df['EXE_ENDDATE'].iloc[0]+ '-' + c_p] 
    c1 = [date + '-' + c_p]
    for i in range(1,len(strike)):
        if len(df.loc[(df['EXE_PRICE']==strike[i]) & (df['EXE_MODE']== c_p)]['Position']) == 0:
            c1.append('')
        if len(df.loc[(df['EXE_PRICE']==strike[i]) & (df['EXE_MODE']== c_p)]['Position']) == 1:
            c1.append(df.loc[(df['EXE_PRICE']==strike[i]) & (df['EXE_MODE']== c_p)]['Position'].iloc[0])
    
    return(c1)


def Reconstruct_day(d, dates, strike, c_p, k):
    #dates = sorted(list(set(d['EXE_ENDDATE'])))
    df = d.loc[d['EXE_ENDDATE'] == dates[k-1] ]
    #c1 = [df['EXE_ENDDATE'].iloc[0]+ '-' + c_p]
    c1 = [dates[k-1] + '-' + c_p]
    for i in range(1,len(strike)):
        if len(df.loc[(df['EXE_PRICE']==strike[i]) & (df['EXE_MODE']== c_p)]['Position']) == 0:
            c1.append('')
        if len(df.loc[(df['EXE_PRICE']==strike[i]) & (df['EXE_MODE']== c_p)]['Position']) == 1:
            c1.append(df.loc[(df['EXE_PRICE']==strike[i]) & (df['EXE_MODE']== c_p)]['Position'].iloc[0])
    
    return(c1)

today = w.tdaysoffset(0).Times[0].strftime('%Y%m%d')
yesterday = w.tdaysoffset(-1).Times[0].strftime('%Y%m%d')


data = LoadData(contracts)
error,etf = w.wsq("159919.SZ", "rt_open,rt_high,rt_low,rt_bid1,rt_ask1,rt_latest", usedf=True)
error,pre_etf = w.wsq("159919.SZ", "rt_pre_close", usedf=True)
#preclose = w.wss("159919.SZ", "pre_close","tradeDate="+today+";priceAdj=U;cycle=D").Data[0]
etf['Close'] = (etf['RT_BID1']+etf['RT_ASK1'])/2
etf['Pre_close'] = pre_etf['RT_PRE_CLOSE']
etf = etf.drop(['RT_BID1','RT_ASK1'],axis=1)

