9# -*- coding: utf-8 -*-
"""
Created on Thu Mar 09 17:46:33 2017

@author: GLA
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 19:01:18 2017

@author: Liang
"""

def CalIVCall(S,K,T,r,c):
   #S for stock price
   #K for strike price
    preciselevel=0.00001 #原来的精度是0.0000001
   
    import p4f
    i=1
   
    sigma1=0.0001
    sigma2=2
    sigma=sigma1
   
    while i<1000:
          i+=1
          diff=c-p4f.bs_call(S,K,T,r,sigma)#bs_call(S,X,T,rf,sigma):
         
          if diff>0:
              sigma1=sigma
              sigma=(sigma1+sigma2)/2
             
          else:
              sigma2=sigma
              sigma=(sigma1+sigma2)/2
          if abs(diff)<preciselevel: break
          if sigma2 == sigma1: break
     
    return(sigma)
   
def CalIVPut(S,K,T,r,p):
   
    preciselevel=0.00001
   
    import p4f
    i=1
   
    sigma1=0.0001
    sigma2=4
    sigma=sigma1
   
    while i<1000:
          i+=1
          diff=p-p4f.bs_put(S,K,T,r,sigma)
         
          if diff>0:
              sigma1=sigma
              sigma=(sigma1+sigma2)/2
             
          else:
              sigma2=sigma
              sigma=(sigma1+sigma2)/2
          if abs(diff)<preciselevel: break
          if sigma2 == sigma1: break
     
    return(sigma)
   
def CalDeltaCall(S,K,T,r,iv):
   
    change=0.0000001
    import p4f
   
    price1=p4f.bs_call(S+change,K,T,r,iv)
    price2=p4f.bs_call(S-change,K,T,r,iv)
   
    delta=(price1-price2)/(2*change)
     
    return(delta)

def CalDeltaPut(S,K,T,r,iv):
   
    change=0.0000001
    import p4f
   
    price1=p4f.bs_put(S+change,K,T,r,iv)
    price2=p4f.bs_put(S-change,K,T,r,iv)
    delta=(price1-price2)/(2*change)
     
    return(delta)

def CalGammaCall(S,K,T,r,iv):
    ds=0.00001
    orig_delta = CalDeltaCall(S,K,T,r,iv)
    after_delta = CalDeltaCall(S+ds,K,T,r,iv)
    gamma = (after_delta - orig_delta) / ds
    return(gamma)



def CalGammaCallPct(S,K,T,r,iv):
    ds=0.005
    orig_delta = CalDeltaCall(S*(1-ds),K,T,r,iv)
    after_delta = CalDeltaCall(S*(1+ds),K,T,r,iv)
    gamma = (after_delta - orig_delta) 
    return(gamma)


def CalGammaPut(S,K,T,r,iv):
    ds=0.00001
    orig_delta = CalDeltaPut(S,K,T,r,iv)
    after_delta = CalDeltaPut(S+ds,K,T,r,iv)
    gamma = (after_delta - orig_delta) / ds
    return(gamma)
    
def CalGammaPutPct(S,K,T,r,iv):
    ds=0.005
    orig_delta = CalDeltaPut(S*(1-ds),K,T,r,iv)
    after_delta = CalDeltaPut(S*(1+ds),K,T,r,iv)
    gamma = (after_delta - orig_delta) 
    return(gamma)
#############################################################
def CalSpeedCall(S,K,T,r,iv):
    ds=0.00001
    orig_gamma = CalGammaCall(S,K,T,r,iv)
    after_gamma = CalGammaCall(S+ds,K,T,r,iv)
    speed = (after_gamma - orig_gamma) / ds
    return(speed)
    
def CalSpeedCallPct(S,K,T,r,iv):
    ds=0.005
    orig_gamma = CalGammaCallPct(S*(1-ds),K,T,r,iv)
    after_gamma = CalGammaCallPct(S*(1+ds),K,T,r,iv)
    speed = (after_gamma - orig_gamma)
    return(speed)
    
def CalSpeedPutPct(S,K,T,r,iv):
    ds=0.005
    orig_gamma = CalGammaPutPct(S*(1-ds),K,T,r,iv)
    after_gamma = CalGammaPutPct(S*(1+ds),K,T,r,iv)
    speed = (after_gamma - orig_gamma)
    return(speed)

def CalVannaCallPct(S,K,T,r,iv):
    ds=0.005
    orig_vega = CalVegaCall(S*(1-ds),K,T,r,iv)
    after_vega = CalVegaCall(S*(1+ds),K,T,r,iv)
    vanna = (after_vega - orig_vega)
    return(vanna)

def CalVannaPutPct(S,K,T,r,iv):
    ds=0.005
    orig_vega = CalVegaPut(S*(1-ds),K,T,r,iv)
    after_vega = CalVegaPut(S*(1+ds),K,T,r,iv)
    vanna = (after_vega - orig_vega)
    return(vanna)

def CalZommaCallPct(S,K,T,r,iv):
    ds=0.005
    orig_vanna = CalVannaCallPct(S*(1-ds),K,T,r,iv)
    after_vanna = CalVannaCallPct(S*(1+ds),K,T,r,iv)
    zomma = (after_vanna - orig_vanna)
    return(zomma)

def CalZommaPutPct(S,K,T,r,iv):
    ds=0.005
    orig_vanna = CalVannaPutPct(S*(1-ds),K,T,r,iv)
    after_vanna = CalVannaPutPct(S*(1+ds),K,T,r,iv)
    zomma = (after_vanna - orig_vanna)
    return(zomma)








def CalSpeedPut(S,K,T,r,iv):
    ds=0.00001
    orig_gamma = CalGammaPut(S,K,T,r,iv)
    after_gamma = CalGammaPut(S+ds,K,T,r,iv)
    speed = (after_gamma - orig_gamma) / ds
    return(speed)

#########################################################################
def CalThetaCall(S,K,T,r,iv):
    import p4f
    num = 244
    dt = 0.00001
    if T>dt:
        price1=p4f.bs_call(S,K,T,r,iv)
        price2=p4f.bs_call(S,K,T-dt,r,iv)
        theta=(price2-price1) / (dt * num)
    else:
        theta=0
    return(theta)

def CalThetaPut(S,K,T,r,iv):
    import p4f
    num = 244
    dt = 0.00001
    if T>dt:
        price1=p4f.bs_put(S,K,T,r,iv)
        price2=p4f.bs_put(S,K,T-dt,r,iv)
        theta=(price2-price1) / (dt * num)
    else:
        theta=0
    return(theta)
    
def CalThetaCall2(S,K,T,r,iv):
    import p4f
    #file_path='D:\\MyPython\\AnnualTradingDayNum'
    #f = open(file_path,"r")   #设置文件对象
    #ATDN= str(f.readlines())  #直接将文件中按行读到list里，效果与方法2一样
    #f.close()  
    #AnnualTradingDayNum=float(ATDN[2:-2])
    #dt=1/AnnualTradingDayNum
    num = 244
    dt = 1/num
    if T>dt:
        price1=p4f.bs_call(S,K,T,r,iv)
        price2=p4f.bs_call(S,K,T-dt,r,iv)
        theta=(price2-price1)
    else:
        theta=0
    return(theta)

def CalThetaPut2(S,K,T,r,iv):
    import p4f
    #file_path='D:\\MyPthon\\AnnualTradingDayNum'
    #f = open(file_path,"r")   #设置文件对象
    #ATDN= str(f.readlines())  #直接将文件中按行读到list里，效果与方法2一样
    #f.close()  
    #AnnualTradingDayNum=float(ATDN[2:-2])
    #dt=1/AnnualTradingDayNum
    num = 244
    dt = 1/num
    if T>dt:
        price1=p4f.bs_put(S,K,T,r,iv)
        price2=p4f.bs_put(S,K,T-dt,r,iv)
        theta=(price2-price1)
    else:
        theta=0
    return(theta)

def CalVegaCall(S,K,T,r,iv):
    import p4f
    dv=0.005
    if float(iv)>dv:
        price1=p4f.bs_call(S,K,T,r,iv+dv)
        price2=p4f.bs_call(S,K,T,r,iv-dv)
    else:
        price1=p4f.bs_put(S,K,T,r,iv+2*dv)
        price2=p4f.bs_put(S,K,T,r,iv)
        
    vega=price1-price2
    
    return(vega)

def CalVegaPut(S,K,T,r,iv):
    import p4f
    dv=0.005
    if iv>dv:
        price1=p4f.bs_put(S,K,T,r,iv+dv)
        price2=p4f.bs_put(S,K,T,r,iv-dv)
    else:
        price1=p4f.bs_put(S,K,T,r,iv+2*dv)
        price2=p4f.bs_put(S,K,T,r,iv)
    vega=price1-price2
    return(vega)


def CalVannaCall(S,K,T,r,iv):
    dv=0.005
    import p4f
    if float(iv)>dv:
        delta1 = CalDeltaCall(S,K,T,r,iv+dv)
        delta2 = CalDeltaCall(S,K,T,r,iv-dv)
    else:
        delta1 = CalDeltaCall(S,K,T,r,iv+2*dv)
        delta2 = CalDeltaCall(S,K,T,r,iv)
    
    vanna = delta1-delta2
    return(vanna)
    '''
    ds=0.01
    dv=0.005
    import p4f
    if float(iv)>dv:
        price1=p4f.bs_call(S+ds,K,T,r,iv+dv)
        price2=p4f.bs_call(S-ds,K,T,r,iv-dv)
    else:
        price1=p4f.bs_call(S+2*ds,K,T,r,iv+2*dv)
        price2=p4f.bs_call(S,K,T,r,iv)
# !!!!
    vanna=(price1-price2)/(2*ds)
    return(vanna)
    '''

    

def CalVannaPut(S,K,T,r,iv):
    dv=0.005
    import p4f
    if float(iv)>dv:
        delta1 = CalDeltaPut(S,K,T,r,iv+dv)
        delta2 = CalDeltaPut(S,K,T,r,iv-dv)
    else:
        delta1 = CalDeltaPut(S,K,T,r,iv+2*dv)
        delta2 = CalDeltaPut(S,K,T,r,iv)
    
    vanna = delta1-delta2
    return(vanna)
    
    '''
    ds=0.01
    dv=0.005
    import p4f
    if float(iv)>dv:
        price1=p4f.bs_put(S+ds,K,T,r,iv+dv)
        price2=p4f.bs_put(S-ds,K,T,r,iv-dv)
    else:
        price1=p4f.bs_put(S+2*ds,K,T,r,iv+2*dv)
        price2=p4f.bs_put(S,K,T,r,iv)
        
    vanna=(price1-price2)/(2*ds)
    return(vanna)
    '''
####################################
def CalZommaCall(S,K,T,r,iv):
    ds=0.00001
    orig_vanna = CalVannaCall(S,K,T,r,iv)
    after_vanna = CalVannaCall(S+ds,K,T,r,iv)
    zomma = (after_vanna - orig_vanna) / ds
    return(zomma)

def CalZommaPut(S,K,T,r,iv):
    ds=0.00001
    orig_vanna = CalVannaPut(S,K,T,r,iv)
    after_vanna = CalVannaPut(S+ds,K,T,r,iv)
    zomma = (after_vanna - orig_vanna) / ds
    return(zomma)

#####################################################################################



def CalCharmCall(S,K,T,r,iv):
    #charm 隔日delta值的变化
    import p4f
    num = 244
    dt=1/num
    if T>dt:
        delta1 = CalDeltaCall(S,K,T,r,iv)
        delta2 = CalDeltaCall(S,K,T-dt,r,iv)
        charm = delta2-delta1
    else:
        charm=0
    return(charm)
    '''
    import p4f
    ds=0.01
    num = 244
    dt=1/num
    if T>dt:
        price1=p4f.bs_call(S+ds,K,T,r,iv)
        price2=p4f.bs_call(S-ds,K,T-dt,r,iv)
        charm=(price2-price1)/(2*ds)
    else:
        charm=0
    return(charm)
    '''


def CalCharmPut(S,K,T,r,iv):
    import p4f
    num = 244
    dt=1/num
    if T>dt:
        delta1 = CalDeltaPut(S,K,T,r,iv)
        delta2 = CalDeltaPut(S,K,T-dt,r,iv)
        charm = delta2-delta1
    else:
        charm=0
    return(charm)
    
    '''
    import p4f
    ds=0.01
    num = 244
    dt=1/num
    if T>dt:
        price1=p4f.bs_put(S+ds,K,T,r,iv)
        price2=p4f.bs_put(S-ds,K,T-dt,r,iv)
        charm=(price2-price1)/(2*ds)
    else:
        charm=0
    return(charm)
    '''


def CalVommaCall(S,K,T,r,iv):
    import p4f
    dv=0.005  
    if float(iv)>dv:
        ori_vega = CalVegaCall(S,K,T,r,iv-dv)
        after_vega = CalVegaCall(S,K,T,r,iv+dv)
    else:
        ori_vega = CalVegaCall(S,K,T,r,iv)
        after_vega = CalVegaCall(S,K,T,r,iv+2*dv)
    vomma = after_vega - ori_vega
    return(vomma)

def CalVommaPut(S,K,T,r,iv):
    import p4f
    dv=0.005  
    if float(iv)>dv:
        ori_vega = CalVegaPut(S,K,T,r,iv-dv)
        after_vega = CalVegaPut(S,K,T,r,iv+dv)
    else:
        ori_vega = CalVegaPut(S,K,T,r,iv)
        after_vega = CalVegaPut(S,K,T,r,iv+2*dv)
    vomma = after_vega - ori_vega
    return(vomma)



def CalCallPremium(S,K,T,r,iv):
    import p4f
    premium=p4f.bs_call(S,K,T,r,iv)
    return(premium)

def CalPutPremium(S,K,T,r,iv):
    import p4f
    premium=p4f.bs_put(S,K,T,r,iv)
    return(premium)
    
# staddle 
def CalStraddle(S,K,T,r,iv):
    CallATM=CalCallPremium(S,K,T,r,iv)
    PutATM=CalPutPremium(S,K,T,r,iv)
    Straddle=CallATM+PutATM
    return (Straddle)

def CalStraddle2(TC,TP):  #这里的关键是delta=0.5的这个期权是正好对应平值期权
    TC['DeltaDiff']=abs(TC['Delta']-0.5)  
    index1=TC['DeltaDiff'].idxmin()
    TC['DeltaDiff'].iloc[index1]=100000.0
    index2=TC['DeltaDiff'].idxmin()
    x0=TC['Delta'].iloc[index1]  
    x1=TC['Delta'].iloc[index2]
    y0=TC['Price'].iloc[index1]
    y1=TC['Price'].iloc[index2]
    CallATM=(0.5-x1)*(y0-y1)/(x0-x1)+y1
    
    TP['DeltaDiff']=abs(TP['Delta']+0.5)  
    index1=TP['DeltaDiff'].idxmin()
    TP['DeltaDiff'].iloc[index1]=100000.0
    index2=TP['DeltaDiff'].idxmin()
    x0=TP['Delta'].iloc[index1]  
    x1=TP['Delta'].iloc[index2]
    y0=TP['Price'].iloc[index1]
    y1=TP['Price'].iloc[index2]
    PutATM=(-0.5-x1)*(y0-y1)/(x0-x1)+y1
    Straddle=CallATM+PutATM
    
    return (Straddle)
    

    
    
def FindDelta(want_greeks_num,df,greeks='Delta'):
    import pandas as pd
    import copy
    df_new=[]
    tmp = copy.deepcopy(df)
    tmp[greeks] = df[greeks].apply(lambda row: abs(row-want_greeks_num))
    df_new.append(df[tmp[greeks] == tmp[greeks].min()])
    tmp.loc[tmp[greeks] == tmp[greeks].min(),greeks] = 1000
    df_new.append(df[tmp[greeks] == tmp[greeks].min()])
    df_new2 = pd.concat([df_new[0],df_new[1]],ignore_index= False)    
    df_new2 = df_new2.reset_index(drop = True)
    return(df_new2)
def FindDeltaV1(want_greeks_num,df,greeks='Delta'):
    import pandas as pd
    import copy
    df_new=[]
    tmp = copy.deepcopy(df)
    tmp[greeks] = df[greeks].apply(lambda row: abs(row-want_greeks_num))
    df_new.append(df[tmp[greeks] == tmp[greeks].min()])
    tmp.loc[tmp[greeks] == tmp[greeks].min(),greeks] = 1000
    df_new.append(df[tmp[greeks] == tmp[greeks].min()])
    df_new2 = pd.concat([df_new[0],df_new[1]],ignore_index= False)    
    df_new2 = df_new2.reset_index(drop = True)
    return(df_new2)
    
def FindDeltaV3(want_greeks_num,df,greeks='DELTA'):
    import pandas as pd
    import copy
    df_new=[]
#    EmptyFlag=0
    tmp = copy.deepcopy(df)
    tmp['DelAbs']=0
    tmp[greeks] = df[greeks]-want_greeks_num
    if  tmp[tmp[greeks]>0].empty or tmp[tmp[greeks]<0].empty:
#        EmptyFlag=1
        tmp['DelAbs'] = abs(df[greeks]-want_greeks_num)
#        df1=df[tmp['DelAbs'] == tmp['DelAbs'].min()]
#        tmp=df1.reset_index(drop=True)
        df_new.append(df[tmp['DelAbs'] == tmp['DelAbs'].min()])
        tmp.loc[tmp['DelAbs'] == tmp['DelAbs'].min(),'DelAbs'] = 1000
        df_new.append(df[tmp['DelAbs'] == tmp['DelAbs'].min()])
        df_new2 = pd.concat([df_new[0],df_new[1]],ignore_index= False)    
        df_new2 = df_new2.reset_index(drop = True)
    else:
        df_new.append(df[tmp[greeks] == tmp[tmp[greeks]>0][greeks].min()])
        df_new.append(df[tmp[greeks] == tmp[tmp[greeks]<0][greeks].max()])
    df_new2 = pd.concat([df_new[0],df_new[1]],ignore_index= False)    
    df_new2 = df_new2.reset_index(drop = True)
#    print(df_new2)
    return(df_new2)

def CalSkew(call_or_put,df_tmp,greeks='Delta'):  #这个CalSkew是有问题的
    want_greeks_num = 0.25*call_or_put
    TC1_new = FindDelta(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    x1 = abs(TC1_new[greeks][1]-want_greeks_num)
    x2 = abs(TC1_new[greeks][0]-want_greeks_num)
    x11 = x1/(x1+x2)
    x22 = x2/(x1+x2)
    IV_25= TC1_new['ImpliedVolatility'][0]*x11 + TC1_new['ImpliedVolatility'][1]*x22
    want_greeks_num = 0.5*call_or_put
    TC2_new = FindDelta(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    x1 = abs(TC2_new[greeks][1]-want_greeks_num)
    x2 = abs(TC2_new[greeks][0]-want_greeks_num)
    x11 = x1/(x1+x2)
    x22 = x2/(x1+x2)
    IV_50= TC2_new['ImpliedVolatility'][0]*x11 + TC2_new['ImpliedVolatility'][1]*x22
    skew = IV_25/IV_50
    return(skew)
    
def CalSkewV2(call_or_put,df_tmp,greeks='Delta'):  #这是张扬6月26日新修改的
    want_greeks_num = 0.25*call_or_put
    TC1_new = FindDelta(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    x1 = TC1_new[greeks][1]
    x0 = TC1_new[greeks][0]
    y1=TC1_new['ImpliedVolatility'][1]  #这里这种写法纯属为了看的清楚
    y0=TC1_new['ImpliedVolatility'][0]
    IV_25= (want_greeks_num-x1)*(y0-y1)/(x0-x1)+y1
    want_greeks_num = 0.5*call_or_put
    TC2_new = FindDelta(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    x1 = TC2_new[greeks][1]
    x0 = TC2_new[greeks][0]
    y1=TC2_new['ImpliedVolatility'][1]  #这里这种写法纯属为了看的清楚
    y0=TC2_new['ImpliedVolatility'][0]
    IV_50= (want_greeks_num-x1)*(y0-y1)/(x0-x1)+y1
    skew = IV_25/IV_50
    return(skew)

def CalSkewV3(call_or_put,df_tmp,greeks='Delta'):  #V2与V3本质上是完全相同的
    want_greeks_num = 0.25*call_or_put
    TC1_new = FindDelta(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    x1 = want_greeks_num-TC1_new[greeks][1]
    x0 = TC1_new[greeks][0]-want_greeks_num
    x11 = x1/(x0+x1)
    x00 = x0/(x0+x1)
    IV_25= TC1_new['ImpliedVolatility'][0]*x11 + TC1_new['ImpliedVolatility'][1]*x00
    want_greeks_num = 0.5*call_or_put
    TC2_new = FindDelta(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    x1 = want_greeks_num-TC2_new[greeks][1]
    x0 = TC2_new[greeks][0]-want_greeks_num
    x11 = x1/(x0+x1)
    x00 = x0/(x0+x1)
    IV_50= TC2_new['ImpliedVolatility'][0]*x11 + TC2_new['ImpliedVolatility'][1]*x00
    skew = IV_25/IV_50
    return(skew)
    
#截止到20190626日 V4这个版本的CalSkew是最完善的
def CalSkewV4(call_or_put,df_tmp,greeks='Delta'):  #V4 要求一个点Delta是比0.25大的，一个点Delta比0.25小
    want_greeks_num = 0.25*call_or_put
    TC1_new = FindDeltaV3(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')  #使用FindDeltaV3
    Flag1=0
    if TC1_new.shape[0]>2:
        for i in range(TC1_new.shape[0]):
            if TC1_new[greeks][i] != TC1_new[greeks][0]:
                delta1_x1=TC1_new[greeks][i]
                TC1_index=i
                break
            if i==TC1_new.shape[0]:
                Flag1=1   #代表非常特殊的情况，就是所有Call合约的Delta值都相同
    #    x1 = want_greeks_num-TC1_new[greeks][1]  #x1是delta比较小的
        if Flag1 ==0:
            x1 = want_greeks_num-delta1_x1
            x0 = TC1_new[greeks][0]-want_greeks_num  #x0是delta比较大的
            x11 = x1/(x0+x1)
            x00 = x0/(x0+x1)
            IV_25= TC1_new['ImpliedVolatility'][0]*x11 + TC1_new['ImpliedVolatility'][TC1_index]*x00
        else:
            IV_25=1.0
    else:
        x1 = want_greeks_num-TC1_new[greeks][1]  #x1是delta比较小的
        x0 = TC1_new[greeks][0]-want_greeks_num  #x0是delta比较大的
        x11 = x1/(x0+x1)
        x00 = x0/(x0+x1)
        IV_25= TC1_new['ImpliedVolatility'][0]*x11 + TC1_new['ImpliedVolatility'][1]*x00
    
    want_greeks_num = 0.5*call_or_put
    TC2_new = FindDeltaV3(want_greeks_num=want_greeks_num,df=df_tmp,greeks='Delta')
    Flag2=0
    if TC2_new.shape[0]>2:
        for i in range(TC2_new.shape[0]):
            if TC2_new[greeks][i] != TC1_new[greeks][0]:
                delta2_x1=TC2_new[greeks][i]
                TC2_index=i
                break
            if i==TC2_new.shape[0]:
                Flag2=1   #代表非常特殊的情况，就是所有Call合约的Delta值都相同
        if Flag2 ==0:
            x1 = want_greeks_num-delta2_x1
            x0 = TC2_new[greeks][0]-want_greeks_num
            x11 = x1/(x0+x1)
            x00 = x0/(x0+x1)
            IV_50= TC2_new['ImpliedVolatility'][0]*x11 + TC2_new['ImpliedVolatility'][TC2_index]*x00
        else:
            IV_50=1.0
    else:
        x1 = want_greeks_num-TC2_new[greeks][1]
        x0 = TC2_new[greeks][0]-want_greeks_num
        x11 = x1/(x0+x1)
        x00 = x0/(x0+x1)
        IV_50= TC2_new['ImpliedVolatility'][0]*x11 + TC2_new['ImpliedVolatility'][1]*x00 
    skew = IV_25/IV_50
    return(skew)


def CalSkewV5(call_or_put,df_tmp,greeks='DELTA'):  #V4 要求一个点Delta是比0.25大的，一个点Delta比0.25小
    want_greeks_num = 0.25*call_or_put
    TC1_new = FindDeltaV3(want_greeks_num=want_greeks_num,df=df_tmp,greeks='DELTA')  #使用FindDeltaV3
    Flag1=0
    if TC1_new.shape[0]>2:
        for i in range(TC1_new.shape[0]):
            if TC1_new[greeks][i] != TC1_new[greeks][0]:
                delta1_x1=TC1_new[greeks][i]
                TC1_index=i
                break
            if i==TC1_new.shape[0]:
                Flag1=1   #代表非常特殊的情况，就是所有Call合约的Delta值都相同
    #    x1 = want_greeks_num-TC1_new[greeks][1]  #x1是delta比较小的
        if Flag1 ==0:
            x1 = want_greeks_num-delta1_x1
            x0 = TC1_new[greeks][0]-want_greeks_num  #x0是delta比较大的
            x11 = x1/(x0+x1)
            x00 = x0/(x0+x1)
            IV_25= TC1_new['Implied Volatility'][0]*x11 + TC1_new['Implied Volatility'][TC1_index]*x00
        else:
            IV_25=1.0
    else:
        x1 = want_greeks_num-TC1_new[greeks][1]  #x1是delta比较小的
        x0 = TC1_new[greeks][0]-want_greeks_num  #x0是delta比较大的
        x11 = x1/(x0+x1)
        x00 = x0/(x0+x1)
        IV_25= TC1_new['Implied Volatility'][0]*x11 + TC1_new['Implied Volatility'][1]*x00
    
    want_greeks_num = 0.5*call_or_put
    TC2_new = FindDeltaV3(want_greeks_num=want_greeks_num,df=df_tmp,greeks='DELTA')
    Flag2=0
    if TC2_new.shape[0]>2:
        for i in range(TC2_new.shape[0]):
            if TC2_new[greeks][i] != TC2_new[greeks][0]:
                delta2_x1=TC2_new[greeks][i]
                TC2_index=i
                break
            if i==TC2_new.shape[0]:
                Flag2=1   #代表非常特殊的情况，就是所有Call合约的Delta值都相同
        if Flag2 ==0:
            x1 = want_greeks_num-delta2_x1
            x0 = TC2_new[greeks][0]-want_greeks_num
            x11 = x1/(x0+x1)
            x00 = x0/(x0+x1)
            IV_50= TC2_new['Implied Volatility'][0]*x11 + TC2_new['Implied Volatility'][TC2_index]*x00
        else:
            IV_50=1.0
    else:
        x1 = want_greeks_num-TC2_new[greeks][1]
        x0 = TC2_new[greeks][0]-want_greeks_num
        x11 = x1/(x0+x1)
        x00 = x0/(x0+x1)
        IV_50= TC2_new['Implied Volatility'][0]*x11 + TC2_new['Implied Volatility'][1]*x00 
    skew = IV_25/IV_50
    return(skew,IV_25)
'''   
import time


start = time.clock()

#your code here
     
S=2.3352 #for stock
X=2.3   #for strike
T=0.0328
r=0.0000
c=0.03925
p=0.00505
IV1=CalIVCall(S,X,T,r,c)
IV2=CalIVPut(S,X,T,r,p)


print(IV1)

print(IV2)

DeltaCall=CalDeltaCall(S,X,T,r,IV1)
DeltaPut=CalDeltaPut(S,X,T,r,IV2)
GammaCall=CalGammaCall(S,X,T,r,IV1)
GammaPut=CalGammaPut(S,X,T,r,IV2)


print('DeltaCall',DeltaCall)
print('DeltaPut',DeltaPut)
print('GammaCall',GammaCall)
print('GammaPut',GammaPut)


#print(IV2)

end = time.clock()
print( 'time used:',(end-start),'seconds')    
'''

