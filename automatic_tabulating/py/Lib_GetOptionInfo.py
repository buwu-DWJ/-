
"""
# -*- coding: utf-8 -*-
"""
"""
Created on Wed Feb 15 18:09:46 2017

@author: Liang

"""
#import datetime


import urllib

import pandas as pd

#import xlrd

import time 


def getdata(url):  
 
    data=urllib.urlopen(url).read()  
    return data  

def getcontract(url):
    data1=urllib.urlopen(url).read()        
    x=0
    i=0
    Contract={}
    while x>=0:
        x=data1.find("CON",x+1)  
        Contract[i]=data1[x:x+15]
        i+=1
    del(Contract[len(Contract)-1])
    return(Contract)

def StrikePrice(data1):
    
    x=0
    i=0
    while i<7:
              x=data1.find(",",x+1)
              i+=1
    
    SrikePrice=data1[x+1:x+7]
    return(SrikePrice)

def BidPrice(data1):
    x=0
    i=0
    while i<1:
              x=data1.find(",",x+1)
              i+=1
              
    BidPrice=data1[x+1:x+7]
    return(BidPrice)

def AskPrice(data1):
    x=0
    i=0
    while i<3:     
              x=data1.find(",",x+1)
              i+=1
              
    AskPrice=data1[x+1:x+7]
    return(AskPrice)
'''
def ExpiredDay(month):
    url='http://stock.finance.sina.com.cn/futures/api/openapi.php/StockOptionService.getRemainderDay?date=20'+month
    data1=urllib.urlopen(url).read()
    x=data1.find("expireDay")
    day=data1[x+12:x+22]
    return(day)

def ExpiredDay(month):
# month = 1 or 2
  
    data1=pd.DataFrame()
    data1=pd.read_csv('D:\BaiduYunDownload\OptionPython\OptionPython\Parameters.csv',header=1)
    day=data1.loc[0,month]

    return(day)



def ExpiredDayNum(month):
    import datetime

    day=ExpiredDay(month)
    excel=r'D:\\BaiduYunDownload\\OptionPython\\OptionPython\\TradeDay.xls'
    data=pd.read_excel(excel)
    x=data.loc[(data["date"]==day)].index 
               
    today=time.localtime()           
    td=time.strftime("%Y-%m-%d",time.localtime())
    
    
    
    y=data.loc[(data["date"]==td)].index
    
    i=0    
    today=datetime.date.today() 
    oneday=datetime.timedelta(days=1)       
    while not y.any():
        i+=1
        day=today-oneday *i 
        td=day.strftime("%Y-%m-%d")
        y=data.loc[(data["date"]==td)].index
       
        
    ExpiredDNum=x[0]-y[0]
    return(ExpiredDNum)
'''


def ExpiredDay(month):
# month = 1 or 2
    import csv
    
    i=0
    data1=pd.DataFrame()
    with open('D:\BaiduYunDownload\OptionPython\OptionPython\Parameters.csv','rb') as csvfile:
        reader = csv.reader(csvfile)
        for m1 in reader:
            data1[i]=m1
            i=i+1
    data2=data1[data1[1].isin([month])]
    day=data2[2]
    if len(day)==0:
        day=data1.iloc[int(month),2]
   
    
    
    return(day)




def ExpiredDayNum(day):
    import datetime
    import time

#    day=ExpiredDay(month)
   
    excel=r'D:\MyPython\TradeDay.xls'
    data=pd.read_excel(excel)
    if len(day)==10:
        df=datetime.datetime.strptime(str(day),'%Y/%m/%d')
    else:
        df=datetime.datetime.strptime(str(day.iloc[0]),'%Y/%m/%d')

    dayform=df.strftime("%Y-%m-%d")
    
    
    
    x=data.loc[(data["date"]==dayform)].index 
               
    today=time.localtime()           
    td=time.strftime("%Y-%m-%d",time.localtime())
    
    
    
    y=data.loc[(data["date"]==td)].index
    
    i=0    
    today=datetime.date.today() 
    oneday=datetime.timedelta(days=1)       
    while not y.any():
        i+=1
        day=today-oneday *i 
        td=day.strftime("%Y-%m-%d")
        y=data.loc[(data["date"]==td)].index
       
        
    ExpiredDNum=x[0]-y[0]
    return(ExpiredDNum)

def ExpiredTime(day):
    file_path='D:\\MyPython\\AnnualTradingDayNum'
    f = open(file_path,"r")   
    ATDN= str(f.readlines())
    f.close()  
    AnnualTradingDayNum=float(ATDN[2:-2])
    ExpiredDNum=ExpiredDayNum(day)
    h=int(time.strftime("%H",time.localtime()))
    m=int(time.strftime("%M",time.localtime()))
    
    t1=15-h-1+(60-m)/60
    if t1>=6 :
         t2=4
    if t1<6 and t1>=3.5:
        t2=t1-1.5
    
    if t1<3.5 and t1>=2:
        t2=2
        
    if t1<2:
        t2=t1
        
    if t1<0:   #这句话要加上，否则不对的
        t2=0
    
    
    
    ExpiredT=(float(ExpiredDNum)+float(t2)/4)/AnnualTradingDayNum  #这里的交易日按243天来算
                
    return(ExpiredT)


def CalSynFuturePrice(TC1,TP1):   #算合成期货的价格,行权价格在第几列！！
    premium1=0.5*(TC1['BidPrice']+TC1['AskPrice'])
    premium2=0.5*(TP1['BidPrice']+TP1['AskPrice'])
    diff=abs(premium1-premium2)   
    StrikeATM=TC1.values[diff.idxmin(),2]  #!!!第几列是行权价要搞明白
    PriceSyn=premium1[diff.idxmin()]+StrikeATM-premium2[diff.idxmin()]  
    return(PriceSyn)
    
def CalStrikeATM(TC1,TP1):       #算ATM的行权价
    premium1=0.5*(TC1['BidPrice']+TC1['AskPrice'])
    premium2=0.5*(TP1['BidPrice']+TP1['AskPrice'])
    diff=abs(premium1-premium2)
    StrikeATM=TC1.values[diff.idxmin(),2]    #!!!第几列是行权价要搞明白
    if StrikeATM != TP1.values[diff.idxmin(),2]:
        print('error')
    return(StrikeATM) 

def CalOptionPriceATM(TC1,TP1):   #算ATM的期权价格
    premium1=0.5*(TC1['BidPrice']+TC1['AskPrice'])
    premium2=0.5*(TP1['BidPrice']+TP1['AskPrice'])
    diff=abs(premium1-premium2)   
    CallPriceATM=0.5*(TC1.values[diff.idxmin(),3]+TC1.values[diff.idxmin(),5])  #3是Ask 5是bid
    PutPriceATM=0.5*(TP1.values[diff.idxmin(),3]+TP1.values[diff.idxmin(),5])  #3是Ask 5是bid
    return(CallPriceATM,PutPriceATM)


          
def CalSynVol(TC1,TP1):                 #这个函数要求TC1和TP1都是按照行权价从低到高往下排列
    PriceSyn=TC1['S'][0]
    diff1=TC1['EXE_PRICE']-PriceSyn
    a=(diff1>0)*diff1
    if sum(diff1>0)>0 and sum(diff1>0)<len(diff1):  #第一种情况是为了避免全是实值期权，第二种情况是避免全是虚值
                        index1=sum(a==0) #???for call
                        index2=index1-1 #!!!for put
                        share2=(TC1.loc[index1,'EXE_PRICE']-PriceSyn)/(TC1.loc[index1,'EXE_PRICE']-TP1.loc[index2,'EXE_PRICE'])
                        share1=1-share2
                        IVSyn=share1*TC1.loc[index1,'Implied Volatility']+share2*TP1.loc[index2,'Implied Volatility']
    else:
                        if sum(diff1>0)==0:
                                    index1=len(diff1)-1
                                    index2=index1
                                    IVCATM=TC1.loc[index1,'Implied Volatility']+(PriceSyn-TC1.loc[index1,'EXE_PRICE'])*(TC1.loc[index1,'Implied Volatility']-TC1.loc[index1-1,'Implied Volatility'])/(TC1.loc[index1,'EXE_PRICE']-TC1.loc[index1-1,'EXE_PRICE'])
                                    IVPATM=TP1.loc[index2,'Implied Volatility']+(PriceSyn-TP1.loc[index2,'EXE_PRICE'])*(TP1.loc[index2,'Implied Volatility']-TP1.loc[index2-1,'Implied Volatility'])/(TP1.loc[index2,'EXE_PRICE']-TP1.loc[index2-1,'EXE_PRICE'])
                                    IVSyn=IVPATM  
                        else: 
                                    index1=0
                                    index2=index1
                                    IVCATM=TC1.loc[index1,'Implied Volatility']+(PriceSyn-TC1.loc[index1,'EXE_PRICE'])*(TC1.loc[index1,'Implied Volatility']-TC1.loc[index1-1,'Implied Volatility'])/(TC1.loc[index1,'EXE_PRICE']-TC1.loc[index1-1,'EXE_PRICE'])
                                    IVPATM=TP1.loc[index2,'Implied Volatility']+(PriceSyn-TP1.loc[index2,'EXE_PRICE'])*(TP1.loc[index2,'Implied Volatility']-TP1.loc[index2-1,'Implied Volatility'])/(TP1.loc[index2,'EXE_PRICE']-TP1.loc[index2-1,'EXE_PRICE'])
                                    IVSyn=IVCATM   
    return(IVSyn)

          


'''
d1 = datetime.datetime.strptime('2015-03-05 17:41:20', '%Y-%m-%d %H:%M:%S')

d2 = datetime.datetime.strptime('2015-03-02 17:41:20', '%Y-%m-%d %H:%M:%S')

delta = d1 - d2

print delta.days  
'''

