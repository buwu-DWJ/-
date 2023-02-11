# tcoreapi_mq   demo记录

[TOC]

```python
core = t.TCoreZMQ(quote_port="51630", trade_port="51600")  # derui
core = t.TCoreZMQ(quote_port="51864", trade_port="51834")  # uat
```

**修改模拟交易资金账户**

[http://algostars-2.icetech.com.cn/algo/dev/login](http://algostars-2.icetech.com.cn/algo/dev/login)

账号: y开头的账户

###  SubHistory时间段(以20220830为例)

| '2022083000','2022083002'     | 9:31~10:00      |
| ----------------------------- | --------------- |
| **'2022083002','2022083003'** | **10:01~11:00** |
| **'2022083003','2022083004'** | **11:01~11:30** |
| **'2022083005','2022083006'** | **1:01~2:00**   |
| **'2022083006','2022083007'** | **2:01~3:00**   |



## python取数据代码示例

### 1. 获取即时的期权greeks信息

```python
def get_option_data_with_greeks():
    '''
    获取最新k的期权数据, 及其希腊值(权分析版)
    '''
    today = datetime.date.today()
    csd_date = today.strftime('%Y%m%d')
    option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
    while option_symbols['Success'] != 'OK':
        option_symbols = core.QueryAllInstrumentInfo('Options', csd_date)
    for month in [0, 1, 2, 3]:
        tau = int(option_symbols['Instruments']['Node'][0]
                  ['Node'][0]['Node'][2+month]['Node'][0]['TradeingDays'][0])
        for j, crt_symbol in enumerate(option_symbols['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][0]['Contracts']):
            new_option_data = pd.DataFrame(core.SubHistory(
                crt_symbol, 'DOGSK', csd_date+'00', csd_date+'07'))
            newest_index = new_option_data.index.drop_duplicates(keep='first').tolist()[-1]
            true_option = new_option_data.iloc[(new_option_data.index == newest_index).tolist()]
            new_option_data = true_option[['Symbol', 'd', 't', 'iv', 'de', 'ga', 'va', 've', 'th', 'ch', 'vo', 'spe', 'zo', ]]
            flag = 'C'
            new_option_data['flag'] = flag
            new_option_data['tau'] = tau
            if j == 0 and month == 0:
                df = new_option_data
            else:
                df = df.append(new_option_data)
        for k in option_symbols['Instruments']['Node'][0]['Node'][0]['Node'][2+month]['Node'][1]['Contracts']:
            new_option_data = pd.DataFrame(core.SubHistory(
                k, 'DOGSK', csd_date+'00', csd_date+'07'))
            newest_index = new_option_data.index.drop_duplicates(keep='first').tolist()[-1]
            true_option = new_option_data.iloc[(new_option_data.index == newest_index).tolist()]
            new_option_data = true_option[['Symbol', 'd', 't', 'iv', 'de', 'ga', 'va', 've', 'th', 'ch', 'vo', 'spe', 'zo', ]]
            flag = 'P'
            new_option_data['flag'] = flag
            new_option_data['tau'] = tau
            df = df.append(new_option_data)
    df.columns = ['Symbol', 'Date', 'precisetime', 'iv', 'delta', 'gamma', 'vanna', 'vega', 'theta', 'charm', 'vomma', 'speed', 'zomma', 'flag', 'tau']
    return df
```



## 古早版本

### 1.实时行情订阅

```python
from tcorepyapi.tcoreapi_mq import * 
import tcorepyapi.tcoreapi_mq
import datetime

#登入
TCoreAPI= TCoreZMQ(quote_port="51630",trade_port="51600")


#订阅合约实时行情报价
#订阅单个合约参数str或list
TCoreAPI.SubQuote("TC.F.SHFE.rb.202110")
#订阅多个合约list
#TCoreAPI.SubQuote(["TC.F.SHFE.rb.202110","TC.F.CFFEX.IF.202106"])

#订阅合约的Greeks实时数据
#订阅单个合约参数str或list,订阅多个合约list
TCoreAPI.SubGreeks(["TC.F.U_SSE.510050.202106"])

while True:
    message=TCoreAPI.mdupdate()
    if message:
        if message['DataType']=='REALTIME':
            print("实时行情 \n 合约：",datetime.datetime.now(),message['Quote']['Symbol'],"  ",int(message['Quote']['FilledTime'])+80000,"  当日成交量：%s" % message['Quote']['TradeVolume'])
        elif  message['DataType']=="GREEKS":
            print("实时GREEKS \n IV:",datetime.datetime.now(),message['Quote'])
```

### 2.main_sample多线程

```python
import time
from tcorepyapi.tcoreapi_mq import *
import pandas as pd
#登入
TCoreAPI= TCoreZMQ(quote_port="51630",trade_port="51600")
#TCoreAPI= TCoreZMQ(quote_port="51864",trade_port="51834")
#TCoreAPI= TCoreZMQ(quote_port="51424",trade_port="51394")
#查询指定合约信息
print("查询指定合约：",TCoreAPI.QueryInstrumentInfo("TC.O.SSE.510050.202108.C.3.6"))

#查询指定类型合约列表
#参数1：
    #期货：Future
    #期权：Options
    #证券：Stock
#参数2：指定日期的合约列表，如果不带或带入空参数，返回最新的合约列表，否则返回指定日期的合约列表
symbollist=TCoreAPI.QueryAllInstrumentInfo("Options")
#print("查询合约：\n",symbollist)
#解析期权合约列表
if symbollist['Success']=="OK":
    for opt in symbollist['Instruments']['Node']:
        #SSE交易所的期权
        if opt['ENG']=='SSE(O)':
            for optlist in opt['Node']:
                #标的50etf的期权
                if optlist['ENG_M']=='50ETF':
                    for optlist2 in optlist['Node']:
                        #202108月份合约
                        if optlist2['ENG']=='202108':
                            for syblist in optlist2['Node']:
                                for symb in syblist['Contracts']:
                                    print(symb)
#解除订阅
#TCoreAPI.UnsubQuote("TC.F.CFFEX.IF.202106")
#订阅实时行情
TCoreAPI.SubQuote("TC.O.SSE.510050.202108.C.3.2")
#解除订阅
#TCoreAPI.UnsubGreeks("TC.F.U_SSE.510050.202106")
#订阅实时Greeks行情
#TCoreAPI.SubGreeks("TC.F.U_SSE.510050.202106")

#获取历史数据
    #1：合约代码，
    #2：数据周期:
        ##标准行情历史数据
        # tick: "TICKS", 
        # 分K: "1K",
        # 日K: "DK"，
        ##DOGS为包含Greeks、标的期货、标的合约的历史数据
        # DOGS秒："DOGSS", 
        # DOGS分K："DOGSK"
    #3: 历史数据开始时间,
    #4: 历史数据结束时间
#his=TCoreAPI.SubHistory("TC.F.U_SSE.510050.202106", "DOGSK", "2021050100", "2021052107")
his=TCoreAPI.SubHistory("TC.O.SSE.510050.202108.C.3.6", "1K", "2021062300", "2021062307")
print("历史数据：\n",his)

#查询已登入资金账户
accountInfo = TCoreAPI.QryAccount()
#查询当日委托回报
reportData = TCoreAPI.QryReport()
if reportData:
    print("当日委托回报：\n",pd.DataFrame(reportData))
else:
    print("今日没有委托记录")
#查询当日成交回报
fillReportData = TCoreAPI.QryFillReport()
if fillReportData:
    print("当日成交回报：\n",pd.DataFrame(fillReportData))
else:
    print("今日没有成交记录")
#查询持仓监控
PositionTracker=TCoreAPI.QryPositionTracker()
if PositionTracker:
    print("持仓监控信息：\n",PositionTracker)
else:
    print("没有持仓监控信息")
strAccountMask =""
if accountInfo != None:
    arrInfo = accountInfo["Accounts"]
    if len(arrInfo) != 0:
        for acc in arrInfo:
            print("当前已登入资金账户\n",pd.DataFrame.from_dict(acc,orient='index').T)
        #获取账户列表中的第一个账户
        strAccountMask = arrInfo[0]["AccountMask"]
        #查询资金
        margin=TCoreAPI.QryMargin(strAccountMask)
        print("资金信息：\n",pd.DataFrame(margin["Margins"]))
        #查询持仓
        pos = TCoreAPI.QryPosition(strAccountMask)
        print("持仓信息：\n",pd.DataFrame(pos))

def mdupdatethread():
    flag=True
    while True:
        #行情更新
        quoteupdate= TCoreAPI.mdupdate()
        if quoteupdate:
            if quoteupdate['DataType']=='REALTIME':
                print("实时行情: \n",pd.DataFrame.from_dict(quoteupdate['Quote'],orient='index').T)  #这里只是展示用，实际应用建议不要使用dataframe转换实时数据，会影响运行效率
                if strAccountMask !="" and flag:
                    #新增一笔委托
                    orders_obj = {
                                    "Symbol":quoteupdate['Quote']['Symbol'],
                                    "BrokerID":arrInfo[0]['BrokerID'],
                                    "Account":arrInfo[0]['Account'],
                                    "Price":"0.0001",#quoteupdate['Quote']['LowPrice'],
                                    "TimeInForce":"1",
                                    "Side":"1",
                                    "OrderType":"2",
                                    "OrderQty":"1",
                                    "PositionEffect":"4",
                                    "SelfTradePrevention":"3"
                                    #"ChasePrice":"1T|5|3|M"
                                }
                    ordid = TCoreAPI.NewOrder(orders_obj)
                    if ordid!=None:
                        while True:
                            if TCoreAPI.getorderinfo(ordid):
                                print("新增委托",TCoreAPI.getorderinfo(ordid)['ReportID'])#,TCoreAPI.QryReport()[-1]['ReportID'])
                                break

                    #改单
                    time.sleep(1)
                    print(TCoreAPI.getorderinfo(ordid)['ExecType'])
                    reporders_obj={
                        "ReportID":TCoreAPI.getorderinfo(ordid)['ReportID'],#TCoreAPI.QryReport()[-1]['ReportID'],
                        "ReplaceExecType":"0",
                        "Price":quoteupdate['Quote']['TradingPrice']
                        }
                    #在可改单的委托单状态下发送改单指令（注意：模拟交易和外盘允许改单，内盘建议使用先删单单然后发送新委托方式改单）
                    if TCoreAPI.getorderinfo(ordid)['ExecType'] in ["0","1","4","6"]:
                        reorder=TCoreAPI.ReplaceOrder(reporders_obj)
                        print("修改委托单：\n",reorder,TCoreAPI.QryReport()[-1]['ReportID'])
                    #取消委托单
                    time.sleep(1)
                    cancalorders_obj = {
                                "ReportID":TCoreAPI.getorderinfo(ordid)['ReportID'],#TCoreAPI.QryReport()[-1]['ReportID'],
                                }
                    #在可删单的委托单状态下发送删单指令      
                    if TCoreAPI.getorderinfo(ordid)['ExecType'] in ["0","1","4","6"]:
                        cancal_order = TCoreAPI.CancelOrder(cancalorders_obj )
                        print("删单:",cancal_order)
                    #建组合
                    orders_obj = {
                                "Symbol":"TC.O.SSE.510050.202106.C.3.6&TC.O.SSE.510050.202106.C.3.7",
                                "BrokerID":arrInfo[0]['BrokerID'],
                                "Account":arrInfo[0]['Account'],
                                "CombDirection":"1",
                                "Side":"1",
                                "CombinationType":"1",
                                "Volume":"1"
                                }
                    TCoreAPI.OptComb(orders_obj)
                    #查询新建组合的委托回报
                    TCoreAPI.QryOptCombOrder(strAccountMask,"")
                    flag=False
            elif  quoteupdate['DataType']=="GREEKS":
                print("实时GREEKS: \n",pd.DataFrame.from_dict(quoteupdate['Quote'],orient='index').T)

def tdupdatethread():
    while True:
        #交易更新
        tradeupdate= TCoreAPI.tdupdate()
        if tradeupdate:
            if tradeupdate['DataType']=='ACCOUNTS':
                print("账户列表更新: \n",tradeupdate['Accounts'])
                arrInfo = tradeupdate['Accounts']
                if len(arrInfo) != 0:
                    strAccountMask = arrInfo[0]["AccountMask"]
            elif tradeupdate['DataType'] == "EXECUTIONREPORT":
                print("实时委托回报: \n",pd.DataFrame.from_dict(tradeupdate["Report"],orient='index').T)
            elif tradeupdate['DataType'] == "FILLEDREPORT":
                print("实时成交: \n",pd.DataFrame.from_dict(tradeupdate["Report"],orient='index').T)
            elif tradeupdate['DataType'] == "POSITIONTRACKER":
                #查询持仓监控
                PositionTracker=TCoreAPI.QryPositionTracker()
                print("持仓监控信息更新\n",PositionTracker)

thr1=threading.Thread(target=mdupdatethread)
thr2=threading.Thread(target=tdupdatethread)
thr2.start()
thr1.start()
```

### 3.main_sample完整demo

```python
import time
from tcorepyapi.tcoreapi_mq import *
import pandas as pd
#登入
TCoreAPI= TCoreZMQ(quote_port="51630",trade_port="51600")
#TCoreAPI= TCoreZMQ(quote_port="51864",trade_port="51834")
#TCoreAPI= TCoreZMQ(quote_port="51424",trade_port="51394")
#查询指定合约信息
print("查询指定合约：",TCoreAPI.QueryInstrumentInfo("TC.O.SSE.510050.202108.C.3.6"))

#查询指定类型合约列表
#参数1：
    #期货：Future
    #期权：Options
    #证券：Stock
#参数2：指定日期的合约列表，如果不带或带入空参数，返回最新的合约列表，否则返回指定日期的合约列表
symbollist=TCoreAPI.QueryAllInstrumentInfo("Options","20210824")
#print("查询合约：\n",symbollist)
#解析期权合约列表
if symbollist['Success']=="OK":
    for opt in symbollist['Instruments']['Node']:
        #SSE交易所的期权
        if opt['ENG']=='SSE(O)':
            for optlist in opt['Node']:
                #标的50etf的期权
                if optlist['ENG_M']=='50ETF':
                    for optlist2 in optlist['Node']:
                        #202108月份合约
                        if optlist2['ENG']=='202108':
                            for syblist in optlist2['Node']:
                                for symb in syblist['Contracts']:
                                    print(symb)
#解除订阅
#TCoreAPI.UnsubQuote("TC.F.CFFEX.IF.202106")
#订阅实时行情
TCoreAPI.SubQuote("TC.O.SSE.510050.202108.C.3.2")
#解除订阅
#TCoreAPI.UnsubGreeks("TC.F.U_SSE.510050.202106")
#订阅实时Greeks行情
#TCoreAPI.SubGreeks("TC.F.U_SSE.510050.202106")

#获取历史数据
    #1：合约代码，
    #2：数据周期:
        ##标准行情历史数据
        # tick: "TICKS", 
        # 分K: "1K",
        # 日K: "DK"，
        ##DOGS为包含Greeks、标的期货、标的合约的历史数据
        # DOGS秒："DOGSS", 
        # DOGS分K："DOGSK"
    #3: 历史数据开始时间,
    #4: 历史数据结束时间
#his=TCoreAPI.SubHistory("TC.F.U_SSE.510050.202106", "DOGSK", "2021050100", "2021052107")
his=TCoreAPI.SubHistory("TC.O.SSE.510050.202108.C.3.6", "1K", "2021062300", "2021062307")
print("历史数据：\n",his)

#查询已登入资金账户
accountInfo = TCoreAPI.QryAccount()
#查询当日委托回报
reportData = TCoreAPI.QryReport()
if reportData:
    print("当日委托回报：\n",pd.DataFrame(reportData))
else:
    print("今日没有委托记录")
#查询当日成交回报
fillReportData = TCoreAPI.QryFillReport()
if fillReportData:
    print("当日成交回报：\n",pd.DataFrame(fillReportData))
else:
    print("今日没有成交记录")
#查询持仓监控
PositionTracker=TCoreAPI.QryPositionTracker()
if PositionTracker:
    print("持仓监控信息：\n",PositionTracker)
else:
    print("没有持仓监控信息")
strAccountMask =""
if accountInfo != None:
    arrInfo = accountInfo["Accounts"]
    if len(arrInfo) != 0:
        for acc in arrInfo:
            print("当前已登入资金账户\n",pd.DataFrame.from_dict(acc,orient='index').T)
        #获取账户列表中的第一个账户
        strAccountMask = arrInfo[0]["AccountMask"]
        #查询资金
        margin=TCoreAPI.QryMargin(strAccountMask)
        print("资金信息：\n",pd.DataFrame(margin["Margins"]))
        #查询持仓
        pos = TCoreAPI.QryPosition(strAccountMask)
        print("持仓信息：\n",pd.DataFrame(pos))

flag=True
while True:
    #行情更新
    quoteupdate= TCoreAPI.mdupdate()

    if quoteupdate:
        if quoteupdate['DataType']=='REALTIME':
            print("实时行情: \n",pd.DataFrame.from_dict(quoteupdate['Quote'],orient='index').T)  #这里只是展示用，实际应用建议不要使用dataframe转换实时数据，会影响运行效率
            if strAccountMask !="" and flag:
                #新增一笔委托
                orders_obj = {
                                "Symbol":quoteupdate['Quote']['Symbol'],
                                "BrokerID":arrInfo[0]['BrokerID'],
                                "Account":arrInfo[0]['Account'],
                                "Price":"0.0001",#quoteupdate['Quote']['LowPrice'],
                                "TimeInForce":"1",
                                "Side":"1",
                                "OrderType":"2",
                                "OrderQty":"1",
                                "PositionEffect":"4",
                                "SelfTradePrevention":"3"
                                #"ChasePrice":"1T|5|3|M"
                            }
                ordid = TCoreAPI.NewOrder(orders_obj)
                if ordid!=None:
                    while True:
                        if TCoreAPI.getorderinfo(ordid):
                            print("新增委托",TCoreAPI.getorderinfo(ordid)['ReportID'])#,TCoreAPI.QryReport()[-1]['ReportID'])
                            break

                #改单
                time.sleep(1)
                print(TCoreAPI.getorderinfo(ordid)['ExecType'])
                reporders_obj={
                    "ReportID":TCoreAPI.getorderinfo(ordid)['ReportID'],#TCoreAPI.QryReport()[-1]['ReportID'],
                    "ReplaceExecType":"0",
                    "Price":quoteupdate['Quote']['TradingPrice']
                    }
                #在可改单的委托单状态下发送改单指令（注意：模拟交易和外盘允许改单，内盘建议使用先删单单然后发送新委托方式改单）
                if TCoreAPI.getorderinfo(ordid)['ExecType'] in ["0","1","4","6"]:
                    reorder=TCoreAPI.ReplaceOrder(reporders_obj)
                    print("修改委托单：\n",reorder,TCoreAPI.QryReport()[-1]['ReportID'])
                #取消委托单
                time.sleep(1)
                cancalorders_obj = {
                            "ReportID":TCoreAPI.getorderinfo(ordid)['ReportID'],#TCoreAPI.QryReport()[-1]['ReportID'],
                            }
                #在可删单的委托单状态下发送删单指令      
                if TCoreAPI.getorderinfo(ordid)['ExecType'] in ["0","1","4","6"]:
                    cancal_order = TCoreAPI.CancelOrder(cancalorders_obj )
                    print("删单:",cancal_order)
                #建组合
                orders_obj = {
                            "Symbol":"TC.O.SSE.510050.202106.C.3.6&TC.O.SSE.510050.202106.C.3.7",
                            "BrokerID":arrInfo[0]['BrokerID'],
                            "Account":arrInfo[0]['Account'],
                            "CombDirection":"1",
                            "Side":"1",
                            "CombinationType":"1",
                            "Volume":"1"
                            }
                TCoreAPI.OptComb(orders_obj)
                #查询新建组合的委托回报
                TCoreAPI.QryOptCombOrder(strAccountMask,"")
                flag=False

        elif  quoteupdate['DataType']=="GREEKS":
            print("实时GREEKS: \n",pd.DataFrame.from_dict(quoteupdate['Quote'],orient='index').T)      
    #交易更新
    tradeupdate= TCoreAPI.tdupdate()
    if tradeupdate:
        if tradeupdate['DataType']=='ACCOUNTS':
            print("账户列表更新: \n",tradeupdate['Accounts'])
            arrInfo = tradeupdate['Accounts']
            if len(arrInfo) != 0:
                strAccountMask = arrInfo[0]["AccountMask"]
        elif tradeupdate['DataType'] == "EXECUTIONREPORT":
            print("实时委托回报: \n",pd.DataFrame.from_dict(tradeupdate["Report"],orient='index').T)
        elif tradeupdate['DataType'] == "FILLEDREPORT":
            print("实时成交: \n",pd.DataFrame.from_dict(tradeupdate["Report"],orient='index').T)
        elif tradeupdate['DataType'] == "POSITIONTRACKER":
            #查询持仓监控
            PositionTracker=TCoreAPI.QryPositionTracker()
            #print("持仓监控信息更新\n",PositionTracker)
```

## 2022.6.13

### 1.实时行情订阅

```python
from tcoreapi_mq import * 
import datetime

#登入
TCoreAPI= TCoreZMQ(quote_port="51630",trade_port="51600")


#订阅合约实时行情报价
#订阅单个合约参数str或list
TCoreAPI.SubQuote("TC.F.SHFE.rb.HOT")
#订阅多个合约list
#TCoreAPI.SubQuote(["TC.F.SHFE.rb.202110","TC.F.CFFEX.IF.202106"])

#订阅合约的Greeks实时数据
#订阅单个合约参数str或list,订阅多个合约list
TCoreAPI.SubGreeks(["TC.F.U_SSE.510050.202201"])

while True:
    message=TCoreAPI.mdupdate()
    if message:
        if message['DataType']=='REALTIME':
            print("实时行情 \n 合约：",datetime.datetime.now(),message['Quote']['Symbol'],"  ",int(message['Quote']['FilledTime'])+80000,"  当日成交量：%s" % message['Quote']['TradeVolume'])
        elif  message['DataType']=="GREEKS":
            print("实时GREEKS \n IV:",datetime.datetime.now(),message['Quote'])

```

### 2.历史数据回补并动态获取最新k是否产生

```python
import time
from tcoreapi_mq import * 
import numpy as np
import pandas as pd

#登入
TCoreAPI= TCoreZMQ(quote_port="51630",trade_port="51600")
symbol="TC.F.CFFEX.IF.202205"
TCoreAPI.SubQuote(symbol)
hisdk=TCoreAPI.SubHistory(symbol, "DK", "2022012000", "2022051607")#time.strftime("%Y%m%d",time.localtime()
his5k=TCoreAPI.SubHistory(symbol, "5K", "2022012000", "2022051607")
print("历史数据：\n",pd.DataFrame(hisdk),"\n",pd.DataFrame(his5k))

while True:
    message=TCoreAPI.mdupdate()
    if message and message['DataType']=='REALTIME':
        print("实时行情 \n 合约：",message['Quote'])
        print("实时行情 \n 合约：",datetime.datetime.now(),message['Quote']['Symbol'],"  ",int(message['Quote']['FilledTime'])+80000,"  当日成交量：%s" % message['Quote']['TradeVolume'])
        hisdk=TCoreAPI.barupdate2("DK",hisdk,message)
        his5k=TCoreAPI.barupdate2("5K",his5k,message)
        if len(his5k)>barlen and barlen!=0: #每当5分K的新K产生时计算策略
            ma20=np.mean([float(x["Close"]) for x in hisdk[-21:-2]])
            std20=np.std([float(x["Close"]) for x in his5k[-21:-2]])
            bollup=ma20+2*std20
            bolldown=ma20-2*std20
            pos=(float(his5k[-2]["Close"])-bolldown)/(bollup-bolldown) #新K的Open价格形成时用上一根完整K的close参与计算，当根K只有open，收盘未产生不参与计算
            vanna=0.1*(pos-0.5)
            print(pos,"  ",vanna)
        barlen=len(his5k)
        #print("历史数据：\n",pd.DataFrame(hisdk),"\n",pd.DataFrame(his5k))

```

### 3.main_sample完整demo

```python
import time
from tcoreapi_mq import *
import pandas as pd
#登入
TCoreAPI= TCoreZMQ(quote_port="51630",trade_port="51600")
#TCoreAPI= TCoreZMQ(quote_port="51864",trade_port="51834")
#TCoreAPI= TCoreZMQ(quote_port="51424",trade_port="51394")
#查询指定合约信息
print("查询指定合约：",TCoreAPI.QueryInstrumentInfo("TC.O.SSE.510050.202108.C.3.6"))
#查询HOT对应的指定月合约
    #参数：
    #####symbol：TC.F.SHFE.rb.HOT
    #####Time:
    #        "20220105013000" yyyymmddHHMMSS带入该参数返回参数指定时间HOT对应的指定月{'20211116070001': 'TC.F.SHFE.rb.202205'}，其中Key为换月时间，Value为对应的指定月合约    
    #        ""不带入该参数时，返回HOT所有历史的换月记录
hotsymb=TCoreAPI.GetHotChange("TC.F.SHFE.rb.HOT","20220105013000")
print(hotsymb)

'''
.
.
-2:实值两档期权合约
-1:实值一档期权合约
0:平值期权合约
1:虚值期权合约
.
.
'''
ATMsym=GetATM("TC.O.SSE.510050.202201", 1)#获取510050期权202201月份的虚值1档期权合约代码
print(ATM)

#查询指定类型合约列表
#参数1：
    #期货：Future
    #期权：Options
    #证券：Stock
#参数2：指定日期的合约列表，如果不带或带入空参数，返回最新的合约列表，否则返回指定日期的合约列表
symbollist=TCoreAPI.QueryAllInstrumentInfo("Options","20210824")
#print("查询合约：\n",symbollist)
#解析期权合约列表
if symbollist['Success']=="OK":
    for opt in symbollist['Instruments']['Node']:
        #SSE交易所的期权
        if opt['ENG']=='SSE(O)':
            for optlist in opt['Node']:
                #标的50etf的琪琪
                if optlist['ENG_M']=='50ETF':
                    for optlist2 in optlist['Node']:
                        #202108月份合约
                        if optlist2['ENG']=='202108':
                            for syblist in optlist2['Node']:
                                for symb in syblist['Contracts']:
                                    print(symb)
#解除订阅
#TCoreAPI.UnsubQuote("TC.F.CFFEX.IF.202106")
#订阅实时行情
TCoreAPI.SubQuote("TC.O.SSE.510050.202108.C.3.2")
#解除订阅
#TCoreAPI.UnsubGreeks("TC.F.U_SSE.510050.202106")
#订阅实时Greeks行情
#TCoreAPI.SubGreeks("TC.F.U_SSE.510050.202106")

#获取历史数据
    #1：合约代码，
    #2：数据周期:
        ##标准行情历史数据
        # tick: "TICKS", 
        # 分K: "1K",
        # 日K: "DK"，
        ##DOGS为包含Greeks、标的期货、标的合约的历史数据
        # DOGS秒："DOGSS", 
        # DOGS分K："DOGSK"
    #3: 历史数据开始时间,
    #4: 历史数据结束时间
#his=TCoreAPI.SubHistory("TC.F.U_SSE.510050.202106", "DOGSK", "2021050100", "2021052107")
his=TCoreAPI.SubHistory("TC.O.SSE.510050.202108.C.3.6", "1K", "2021062300", "2021062307")
print("历史数据：\n",his)

#查询已登入资金账户
accountInfo = TCoreAPI.QryAccount()
#查询当日委托回报
reportData = TCoreAPI.QryReport()
if reportData:
    print("当日委托回报：\n",pd.DataFrame(reportData))
else:
    print("今日没有委托记录")
#查询当日成交回报
fillReportData = TCoreAPI.QryFillReport()
if fillReportData:
    print("当日成交回报：\n",pd.DataFrame(fillReportData))
else:
    print("今日没有成交记录")
#查询持仓监控
PositionTracker=TCoreAPI.QryPositionTracker()
if PositionTracker:
    print("持仓监控信息：\n",PositionTracker)
else:
    print("没有持仓监控信息")
strAccountMask =""
if accountInfo != None:
    arrInfo = accountInfo["Accounts"]
    if len(arrInfo) != 0:
        for acc in arrInfo:
            print("当前已登入资金账户\n",pd.DataFrame.from_dict(acc,orient='index').T)
        #获取账户列表中的第一个账户
        strAccountMask = arrInfo[0]["AccountMask"]
        #查询资金
        margin=TCoreAPI.QryMargin(strAccountMask)
        print("资金信息：\n",pd.DataFrame(margin["Margins"]))
        #查询持仓
        pos = TCoreAPI.QryPosition(strAccountMask)
        print("持仓信息：\n",pd.DataFrame(pos))
        #建组合
        orders_obj = {
                    "Symbol":"TC.O.SSE.510050.202106.C.3.6&TC.O.SSE.510050.202106.C.3.7",
                    "BrokerID":arrInfo[0]['BrokerID'],
                    "Account":arrInfo[0]['Account'],
                    "CombDirection":"1",
                    "Side":"1",
                    "CombinationType":"1",
                    "Volume":"1"
                    }
        TCoreAPI.OptComb(orders_obj)
        #查询新建组合的委托回报
        TCoreAPI.QryOptCombOrder(strAccountMask)
        #查询组合持仓
        OptCombPos=TCoreAPI.QryOptCombPosition(strAccountMask)
        if len(OptCombPos)!=0:
            #拆分组合，将查询到的第一个组合持仓拆分
            orders_obj = {
                "Symbol":OptCombPos[0]['Symbol'],
                "BrokerID":arrInfo[0]['BrokerID'],
                "Account":arrInfo[0]['Account'],
                "CombDirection":"2",
                "Side":OptCombPos[0]['Side'],
                "CombinationType":OptCombPos[0]['CombinationType'],
                "Volume":"1",
                "OptCombID":OptCombPos[0]['OptCombID']
            }
            TCoreAPI.OptComb(orders_obj)

flag=True
while True:
    #行情更新
    quoteupdate= TCoreAPI.mdupdate()

    if quoteupdate:
        if quoteupdate['DataType']=='REALTIME':
            print("实时行情: \n",pd.DataFrame.from_dict(quoteupdate['Quote'],orient='index').T)  #这里只是展示用，实际应用建议不要使用dataframe转换实时数据，会影响运行效率
            if strAccountMask !="" and flag:
                #新增一笔委托
                orders_obj = {
                                "Symbol":quoteupdate['Quote']['Symbol'],
                                "BrokerID":arrInfo[0]['BrokerID'],
                                "Account":arrInfo[0]['Account'],
                                "Price":"0.0001",#quoteupdate['Quote']['LowPrice'],
                                "TimeInForce":"1",
                                "Side":"1",
                                "OrderType":"2",
                                "OrderQty":"1",
                                "PositionEffect":"4",
                                "SelfTradePrevention":"3"
                                #"ChasePrice":"1T|5|3|M"
                            }
                ordid = TCoreAPI.NewOrder(orders_obj)
                if ordid!=None:
                    while True:
                        if TCoreAPI.getorderinfo(ordid):
                            print("新增委托",TCoreAPI.getorderinfo(ordid)['ReportID'])#,TCoreAPI.QryReport()[-1]['ReportID'])
                            break

                #改单
                time.sleep(1)
                print(TCoreAPI.getorderinfo(ordid)['ExecType'])
                reporders_obj={
                    "ReportID":TCoreAPI.getorderinfo(ordid)['ReportID'],#TCoreAPI.QryReport()[-1]['ReportID'],
                    "ReplaceExecType":"0",
                    "Price":quoteupdate['Quote']['TradingPrice']
                    }
                #在可改单的委托单状态下发送改单指令（注意：模拟交易和外盘允许改单，内盘建议使用先删单单然后发送新委托方式改单）
                if TCoreAPI.getorderinfo(ordid)['ExecType'] in ["0","1","4","6"]:
                    reorder=TCoreAPI.ReplaceOrder(reporders_obj)
                    print("修改委托单：\n",reorder,TCoreAPI.QryReport()[-1]['ReportID'])
                #取消委托单
                time.sleep(1)
                cancalorders_obj = {
                            "ReportID":TCoreAPI.getorderinfo(ordid)['ReportID'],#TCoreAPI.QryReport()[-1]['ReportID'],
                            }
                #在可删单的委托单状态下发送删单指令      
                if TCoreAPI.getorderinfo(ordid)['ExecType'] in ["0","1","4","6"]:
                    cancal_order = TCoreAPI.CancelOrder(cancalorders_obj )
                    print("删单:",cancal_order)
                flag=False

        elif  quoteupdate['DataType']=="GREEKS":
            print("实时GREEKS: \n",pd.DataFrame.from_dict(quoteupdate['Quote'],orient='index').T)      
    #交易更新
    tradeupdate= TCoreAPI.tdupdate()
    if tradeupdate:
        if tradeupdate['DataType']=='ACCOUNTS':
            print("账户列表更新: \n",tradeupdate['Accounts'])
            arrInfo = tradeupdate['Accounts']
            if len(arrInfo) != 0:
                strAccountMask = arrInfo[0]["AccountMask"]
        elif tradeupdate['DataType'] == "EXECUTIONREPORT":
            print("实时委托回报: \n",pd.DataFrame.from_dict(tradeupdate["Report"],orient='index').T)
        elif tradeupdate['DataType'] == "FILLEDREPORT":
            print("实时成交: \n",pd.DataFrame.from_dict(tradeupdate["Report"],orient='index').T)
        elif tradeupdate['DataType'] == "POSITIONTRACKER":
            #查询持仓监控
            PositionTracker=TCoreAPI.QryPositionTracker()
            #print("持仓监控信息更新\n",PositionTracker)
```



# icetcore

## 2023.1.3

### 1. sample

```python
import time
from icetcore import TCoreAPI, QuoteEvent, TradeEvent, OrderStruct, BarType, GreeksType


class APIEvent(TradeEvent, QuoteEvent):
    # 连线成功通知apitype="quoteapi"是行情api的通知，"tradeapi"是交易通知
    def onconnected(self, apitype: str):
        print(apitype)
    # 断线成功通知

    def ondisconnected(self, apitype: str):
        print(apitype)
    # subATM订阅的ATM合约信息，动态推送期权的ATM平值,OTM-1C虚值一档认购，OTM-1P虚值一档认沽，和认购期权合约列表

    def onATM(self, datatype, symbol, data: dict):
        pass
    #

    def ongreeksreal(self, datatype, symbol, data: dict):
        pass
    # subquote订阅的合约实时行情

    def onquote(self, data):
        # print(data)
        pass
    # subbar订阅的动态K线数据

    def onbar(self, datatype, symbol, data: list, isreal: bool):
        print("onbar", self._tcoreapi.getsymbol_session("TC.F.SHFE.rb.HOT"))
        print(data[-1])
    # server与本机时间差

    def ontimediff(self, TimeDiff):
        print("!!!!!!!!!!!!!!!", TimeDiff)
        pass
    # #实时委托信息
    # def onordereportreal(self,data):
    #     print(data)
    # #实时成交信息
    # def onfilledreportreal(self,data):
    #     print(data)
    # 账户登出登入时委托资料需要清理通知

    def onorderreportreset(self):
        print("onorderreportreset")
    # #期权持仓监控信息
    # def onpositionmoniter(self,data):
    #     print(data)


# 事件消息需要继承api中QuoteEvent和TradeEvent类，并重写对应方法，即可在对应的回调方法收到实时更新事件
# TCoreAPI参数也可以不带入事件类名，不带入事件类就无法收到实时消息，只能使用同步接口方法
api = TCoreAPI(APIEvent)
re = api.connect(appid='MCVoltraderUAT')
time.sleep(1)
# 获取合约交易时段
print(api.getsymbol_session("TC.F.SHFE.rb.HOT"))
# #订阅动态K线数据
# api.subbar(BarType.MINUTE,"TC.F.SHFE.rb.HOT",start="2022120101")
# api.subbar(BarType.MINUTE,"TC.F.SHFE.cu.HOT",start="2022120101")
# 获取已登入账户列表
accoutlist = api.getaccoutlist()
print(accoutlist)
# 获取合约持仓
print(api.getposition("CTP_NHGPQQ_SIM-8050-90096859"))
# 获取当天全部委托
print(api.getorderreport())
# 获取热门月列表，填入时间时返回对应时间的热门对应指定月合约，Key是换月时间，value是指定月
print(api.gethotmonth("TC.F.SHFE.rb.HOT"))

# 下单
OrderStruct.Account = accoutlist[0]["Account"]
OrderStruct.BrokerID = accoutlist[0]["BrokerID"]
OrderStruct.Symbol = "TC.F.DCE.i.202301"
OrderStruct.Side = 1
OrderStruct.OrderType = 2
OrderStruct.PositionEffect = 0
OrderStruct.TimeInForce = 1
OrderStruct.Price = 848
OrderStruct.OrderQty = 1
ordkey = api.neworder(OrderStruct)
print(ordkey)
if ordkey != None:
    while True:
        if api.getorderinfo(ordkey):
            print("#####################新增委托：", api.getorderinfo(ordkey)
                  ['ReportID'])  # ,TCoreAPI.QryReport()[-1]['ReportID'])
            break

# 改单
api.replaceorder('4112047019F', price=839)
# 获取历史合约信息
print(api.getsymbolhistory("OPT", "20221216"))
# 获取历史数据
a = api.getquotehistory(BarType.MINUTE, "TC.F.SHFE.rb.HOT", "2022120101")
# 获取历史Greeks
A = api.getgreekshistory(
    GreeksType.DOGSK, "TC.F.U_SSE.510050.202212", "2022121202")
# 获取ATM
# -2:实值两档期权合约
# -1:实值一档期权合约
#  0:平值期权合约
#  1:虚值期权合约
print(api.getATM("TC.O.SSE.510050.202212.C", 2))

api.join()

```

### 2. vannasample

```python
import time
from icetcore import TCoreAPI,QuoteEvent,TradeEvent,OrderStruct,BarType,GreeksType
import pandas as pd
import numpy as np

crash=1000000
Vanna=90000 #此处设定Vanna对应期权总持仓分析的$*0.01,如当前设定当期权总持仓分析的达到900W的时候停止加仓
delta=0
vega=0
maxqty=3
symbol="TC.S.SSE.510050"

orderobj={"StrategyType":"Vanna",  #目前固定Vanna 以後不同策略 依此不同處理
            #交易帳號
            # "BrokerID":"M2_PAPERTRADE",
            # "Account":"y000-zxlee",
            "BrokerID":"AlgoStars_TOUCHANCE",
            "Account":"1999_2-0033361",
            "StrategyID":"20221226",     #策略ID 同一策略 每次下必須相同 不同策略必須唯一
            "StrategyName":"Vannapy2",   #自訂義策略名稱
            "UserKey1":"VannaPy",       #視需要自行帶上
            "UserKey2":"xxxxxx",       #視需要自行帶上
            #"UserKey3":"xxxxxx",       #TCTradeAPI自動帶上
            #"ProcessID":"xxxxxx",      #TCTradeAPI自動帶上
            "Security":"TC.O.SSE.510050.202212", #交易品種月份
            #"StopCondition":"$Vanna="+str(int(vanna*crash)),      #策略停止條件
            #"StopFactor":0.01,
            "StopCondition":"1%$Vanna=90000",
            "StopFactor":1,
            "CheckCondition1":"$Delta="+str(delta),    #策略檢查條件1 文件中日內對沖 X
            "CheckRange1":0.02,                  #策略檢查條件1 文件中日內對沖 X
            "CheckCondition2":"$Vega="+str(vega),     #策略檢查條件1 文件中日內對沖 Y
            "CheckRange2":0.0001,                #策略檢查條件1 文件中日內對沖 Y
            "Cash":crash,                      # 總資產 若檢查條件1 2 $Delta=0 $Vega=0 採用此欄運算條件
            "Order":[                            #委託下單資料 這例子是下 負Vanna
                {
                    "CallPut":"Call",               
                    "Condition":"Delta=0.25",      #因虛值要先下到市場 要先下到市場的 擺在前面
                    #"Side":2,
                    "Qty":maxqty,                      #運用文件中 max運算出的數量
                    "Group":"A"                    #同一Group單 會做OCO OTC...
                },
                {
                    "CallPut":"Call",
                    "Condition":"Delta=0.65",    #因實質要待虛值那支成交後 才要先下到市場 所以擺在後面
                    #"Side":1,
                    "Qty":round(maxqty*0.25/0.65),                    #運用文件中 max運算出的數量
                    "Group":"A"                  #同一Group單 會做OCO OTC... 無group可不帶
                },
                {
                    "CallPut":"Put",
                    "Condition":"Delta=-0.25",   #因虛值要先下到市場 要先下到市場的 擺在前面
                    #"Side":1,
                    "Qty":3,                   #運用文件中 max運算出的數量
                    "Group":"B"                 #同一Group單 會做OCO OTC...  無group可不帶
                },
                {
                    "CallPut":"Put",
                    "Condition":"Delta=-0.65",   #因實質要待虛值那支成交後 才要先下到市場 所以擺在後面
                    #"Side":2,
                    "Qty":round(maxqty*0.25/0.65),                   #運用文件中 max運算出的數量
                    "Group":"B"                 #同一Group單 會做OCO OTC...  
                }
            ],
            "GroupAType":3,                   #Group A 要OTO 所以帶3    1:Normal 2:OCO 3:OTO 4:OTOCO  無group可不帶
            "GroupBType":3                    #Group B 要OTO 所以帶3   無group可不帶
            }

class APIEvent(TradeEvent,QuoteEvent):
    def __init__(self) -> None:
        super().__init__()
        self.hisdk=[]
        self.his5klen=0
        self.his5k=[]
    def onconnected(self,apitype:str):
        print(apitype)
    def ondisconnected(self,apitype:str):
        print(apitype)

    def onbar(self,datatype,interval,symbol,data:list,isreal:bool):
        if datatype==BarType.DK and interval==1:
            self.hisdk=data
        if datatype==BarType.MINUTE and interval==5:
            if self.his5klen and self.his5klen<len(data):
                ma20=np.mean([x["Close"] for x in self.hisdk[-21:-2]]) #当日K不参与计算，所以取到倒数-2
                std20=np.std([x["Close"] for x in self.hisdk[-21:-2]]) #5分K最新K是Open产生时判断不参与计算，所以取到倒数-2
                bollup=ma20+2*std20
                bolldown=ma20-2*std20
                pos=(self.his5k[-2]["Close"]-bolldown)/(bollup-bolldown) #新K的Open价格形成时用上一根完整K的close参与计算，当根K只有open，收盘未产生不参与计算
                vanna=0.1*(pos-0.5)
                #print(pd.DataFrame(hisdk),"\n",pd.DataFrame(his5k))
                print(pos,"  ",vanna)
                if pos>0.7:
                    orderobj["StopCondition"]="1%$Vanna="+str(Vanna)
                    self._tcoreapi.newstrategyorder(orderobj)
                if  pos<0.3:
                    orderobj["StopCondition"]="1%$Vanna=-"+str(Vanna)
                    self._tcoreapi.newstrategyorder(orderobj)

                # if vanna>-0.09 and vanna<0.09 and flag:
                #     orderobj["StopCondition"]="$Vanna="+str(int(vanna*100*crash))
                #     self._tcoreapi.newstrategyorder(orderobj)
                #     flag=False

                if pos>0.3 and pos<=0.5:
                    orderobj["StopCondition"]="1%$Vanna=0"
                    self._tcoreapi.newstrategyorder(orderobj)
            self.his5klen=len(data)
            self.his5k=data

    def onordereportreal(self,data):
        print(data)
    # def onfilledreportreal(self,data):
    #     print(data)
    # def onorderreportreset(self):
    #     print("onorderreportreset")
    # def onsymbolhistory(self,symboltype,symboldate,symboldict):
    #     print(symboltype,symboldate,symboldict)
    # def onpositionmoniter(self,data):
    #     print(data)


api=TCoreAPI(APIEvent)#
re=api.connect()
time.sleep(1)

api.subbar(BarType.DK,1,symbol,starttime="2022071900")
api.subbar(BarType.MINUTE,5,symbol,starttime="2022121900")
accoutlist=api.getaccoutlist()
print(accoutlist)

api.join()

```

