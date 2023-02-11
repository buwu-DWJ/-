import pandas as pd
import symbolsIO300 as sb
import datetime

today = sb.today
today = today[0:4] + '年' + today[4].strip('0') + today[5] + '月' + today[6].strip('0') + today[7] + '日'
yesterday = sb.yesterday
yesterday = yesterday[0:4] + '年' + yesterday[4].strip('0') + yesterday[5] + '月' + yesterday[6].strip('0') + yesterday[7] + '日'
trading_exchange = '中金所'
！！！！！underlying = '300ETF' #这里得换

d = sb.data
dates = sorted(list(set(d['EXE_ENDDATE'])))
dates.append('total')

for i in range(6): #这里总共有六个到期日
    locals()['data'+str(i+1)] = sb.CalGreeks(d.loc[(d['EXE_MODE']=='call')&(d['EXE_ENDDATE']==dates[i])],d.loc[(d['EXE_MODE']=='put')&(d['EXE_ENDDATE']==dates[i])])

def GenerateFrame(name):
    df1 = sb.LoadPosition(today+'期权持仓报表' + name +'.csv')
    df1 = df1[df1['市场名称'].str.contains(trading_exchange)]
    df1 = df1[df1['名称'].str.contains(underlying)]
    grouped = df1.groupby(['Contract','Month'])['Position'].sum().reset_index()
    
    delta = []
    gamma = []
    vega = []
    theta = []
    charm = []
    vanna = []
    vomma = []
    speed = []######################################
    zomma = []
    
    for i in range(4):
        locals()['grouped'+str(i+1)] = grouped.loc[grouped['Month'] == dates[i][5:7]]
        locals()['merged'+str(i+1)] = pd.merge(locals()['grouped'+str(i+1)],globals()['data'+str(i+1)],on='Contract')
        delta.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['DELTA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S']))
        gamma.append(sum( locals()['merged'+str(i+1)]['Position'] *locals()['merged'+str(i+1)]['GAMMA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S'] ))
        vega.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['VEGA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        theta.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['THETA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        charm.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['CHARM'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S'] ))
        vanna.append(sum( locals()['merged'+str(i+1)]['Position'] * 100 * locals()['merged'+str(i+1)]['VANNA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))#############*0.5
        vomma.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['VOMMA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        speed.append(sum( locals()['merged'+str(i+1)]['Position'] *locals()['merged'+str(i+1)]['SPEED'] * locals()['merged'+str(i+1)]['EXE_RATIO']* locals()['merged'+str(i+1)]['S'] ))  ######################################################################
        zomma.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['ZOMMA'] * locals()['merged'+str(i+1)]['EXE_RATIO']* locals()['merged'+str(i+1)]['S'] ))

    delta.append(sum(delta))
    gamma.append(sum(gamma))
    vega.append(sum(vega))
    theta.append(sum(theta))
    charm.append(sum(charm))
    vanna.append(sum(vanna))
    vomma.append(sum(vomma))
    speed.append(sum(speed))#####################################
    zomma.append(sum(zomma))
   
    if sb.today == dates[0][0:4]+dates[0][5:7]+dates[0][8:10] :###############################################################
        delta[0] = 0
        gamma[0] = 0
        vega[0] = 0
        theta[0] = 0
        charm[0] = 0
        vanna[0] = 0
        vomma[0] = 0
        speed[0] = 0
        zomma[0] = 0
    
    cashgreeks = pd.DataFrame({'EndDate':dates, 'Delta':delta, 'Gamma':gamma,'Vega':vega, 'Theta':theta, 'Charm':charm,'Vanna':vanna, 'Vomma':vomma, 'Speed':speed, 'Zomma':zomma})
    delta0 = delta
    
    d['Contract'] = d.index
    new_merged = pd.merge(grouped, d, on='Contract')
    merged_c = new_merged.loc[ new_merged['EXE_MODE'] == 'call' ]
    call_num = sum( merged_c['Position'] )
    merged_p = new_merged.loc[ new_merged['EXE_MODE'] == 'put' ]
    put_num = sum( merged_p['Position'] )
    
    
    strike = ['']
    strike.extend(sorted(list(set(d['EXE_PRICE']))))
    
    for i in range(1,7):
        globals()['c'+str(i)] = sb.Reconstruct(locals()['merged'+str(i)], dates[i-1], strike, 'call')
        globals()['p'+str(i)] = sb.Reconstruct(locals()['merged'+str(i)], dates[i-1], strike, 'put')
    position_all = pd.DataFrame([c1,p1,strike,c2,p2,strike,c3,p3,strike,c4,p4,strike,c5,p5,strike,c6,p6,strike], columns=strike)
   
    for i in strike:
        if (position_all[i].iloc[0] == position_all[i].iloc[1] == position_all[i].iloc[3] == position_all[i].iloc[4] == position_all[i].iloc[6] == position_all[i].iloc[7] == position_all[i].iloc[9] == position_all[i].iloc[10] == '') :
            position_all = position_all.drop([i], axis=1)
    
    df3 = sb.LoadPosition(yesterday+'期权持仓报表'+ name +'.csv')
    df3 = df3[df3['市场名称'].str.contains(trading_exchange)]
    df3 = df3[df3['名称'].str.contains(underlying)]
    ygrouped = df3.groupby(['Contract','Month'])['Position'].sum().reset_index()
    ymerged = pd.merge(ygrouped, d, on='Contract')
    ymerged['Return'] = ymerged['Position']  * ((ymerged['RT_BID1']+ymerged['RT_ASK1'])/2 - ymerged['PRE_CLOSE']) * ymerged['EXE_RATIO']
    #yreturn = sum(ymerged['Return'])
    
    ymerged2 = sb.LoadVolume(yesterday+'期权成交报表'+name+'.csv')
    ymerged2 = ymerged2[ymerged2['市场名称'].str.contains(trading_exchange)]
    ymerged2 = ymerged2[ymerged2['合约名称'].str.contains(underlying)]

    ymerged2 = ymerged2.replace('卖',-1)
    ymerged2 = ymerged2.replace('买',1)
    ymerged2 = ymerged2.groupby('合约代码')['买卖'].sum()
    ymerged2 = ymerged2.reset_index()
    
    
    df4 = sb.LoadVolume(today+'期权成交报表'+name+'.csv')
    df4 = df4[df4['市场名称'].str.contains(trading_exchange)]
    df4 = df4[df4['合约名称'].str.contains(underlying)]

    tmerged = pd.merge(df4, d, on='Contract')
    tmerged['Return'] = tmerged['Position'] * ((tmerged['RT_BID1'] + tmerged['RT_ASK1'])/2 - tmerged['成交价格']) * tmerged['EXE_RATIO']
    treturn = sum(tmerged['Return'])
    
    dfnew = df4.loc[~ ((df4['买卖']=='卖') & (df4['开平']=='开仓')) ]
    tfee = - sum(dfnew['成交数量']*1.7)
    ttotal = treturn + tfee
    #t_alltogether = yreturn + ttotal
    #return_frame = pd.DataFrame({'昨仓':[yreturn], '今仓':[treturn], '手续费':[tfee], '日内损益':[ttotal], '合计':[t_alltogether]})
    
    tgrouped = tmerged.groupby(['EXE_ENDDATE','EXE_PRICE','EXE_MODE', 'Contract'])['Position'].sum().reset_index()
    for i in range(1,7):
        globals()['c_'+str(i)] = sb.Reconstruct_day(tgrouped, sorted(list(set(d['EXE_ENDDATE']))), strike, 'call', i)
        globals()['p_'+str(i)] = sb.Reconstruct_day(tgrouped, sorted(list(set(d['EXE_ENDDATE']))), strike, 'put', i)
    position_day = pd.DataFrame([c_1,p_1, strike,c_2,p_2, strike, c_3,p_3, strike,c_4,p_4,strike,c_5,p_5,strike,c_6,p_6,strike], columns=strike)
    
    for i in strike:
        if (position_day[i].iloc[0] == position_day[i].iloc[1] == position_day[i].iloc[3] == position_day[i].iloc[4] == position_day[i].iloc[6] == position_day[i].iloc[7] == position_day[i].iloc[9] == position_day[i].iloc[10] == '') :
            position_day = position_day.drop([i], axis=1)
    
    
    tdelta = []
    tgamma = [] 
    tvega = []
    ttheta = []
    tcharm = []
    tvanna = []
    tvomma = []
    tspeed = []
    tzomma = []
    for i in range(4):###############################################################################
        locals()['grouped'+str(i+1)] = tgrouped.loc[tgrouped['EXE_ENDDATE'] == dates[i] ]
        locals()['merged'+str(i+1)] = pd.merge(locals()['grouped'+str(i+1)],globals()['data'+str(i+1)],on='Contract')
        tdelta.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['DELTA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S']))
        tgamma.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['GAMMA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S'] ))
        tvega.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['VEGA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        ttheta.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['THETA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        tcharm.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['CHARM'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S'] ))
        tvanna.append(sum( locals()['merged'+str(i+1)]['Position'] * 100 * locals()['merged'+str(i+1)]['VANNA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        tvomma.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['VOMMA'] * locals()['merged'+str(i+1)]['EXE_RATIO'] ))
        tspeed.append(sum( locals()['merged'+str(i+1)]['Position'] * locals()['merged'+str(i+1)]['SPEED'] * locals()['merged'+str(i+1)]['EXE_RATIO'] * locals()['merged'+str(i+1)]['S'] ))
        tzomma.append(sum( locals()['merged'+str(i+1)]['Position']  * locals()['merged'+str(i+1)]['ZOMMA'] * locals()['merged'+str(i+1)]['EXE_RATIO']* locals()['merged'+str(i+1)]['S'] ))
    tdelta.append(sum(tdelta))
    tgamma.append(sum(tgamma))
    tvega.append(sum(tvega))
    ttheta.append(sum(ttheta))
    tcharm.append(sum(tcharm))
    tvanna.append(sum(tvanna))
    tvomma.append(sum(tvomma))
    tspeed.append(sum(tspeed))
    tzomma.append(sum(tzomma))
    tcashgreeks = pd.DataFrame({'EndDate':dates, 'Delta':tdelta, 'Gamma':tgamma, 'Vega':tvega, 'Theta':ttheta, 'Charm':tcharm,'Vanna':tvanna, 'Vomma':tvomma, 'Speed':tspeed,  'Zomma':tzomma})
    
    
    df2 = sb.LoadVolume(yesterday+'期权成交报表'+name+'.csv')
    df2 = df2[df2['市场名称'].str.contains(trading_exchange)]
    df2 = df2[df2['合约名称'].str.contains(underlying)]
    y_vgrouped = df2.groupby(['Contract'])['Position'].sum().reset_index()
    y_vmerged = pd.merge(y_vgrouped, d, on='Contract')
    #y_vmerged['Return'] = y_vmerged['Position']  * ((y_vmerged['RT_BID1']+y_vmerged['RT_ASK1'])/2 - y_vmerged['PRE_CLOSE']) * y_vmerged['EXE_RATIO']
    
    
    ymerged2['合约代码'] = [str(i)+'.CFE' for i in ymerged2['合约代码']]
    ymerged2.rename(columns=({'合约代码':'Contract'}),inplace=True)
    ymerged3 = pd.merge(y_vmerged,ymerged2,on='Contract',how='left')

    
    y_vmerged['Return'] = ymerged3['Position']  * ((ymerged3['RT_BID1']+ymerged3['RT_ASK1'])/2 - ymerged3['PRE_CLOSE']) * ymerged3['EXE_RATIO']
    y_affect_t = sum(y_vmerged['Return'])
    
    df5 = pd.read_excel('净值统计'+name+'.xlsx')
    lenth = len(df5)-1
    tprofit = df5['盈亏'].iloc[lenth]
    tpercent = df5['盈利率'].iloc[lenth]
    tequity = df5['资金权益'].iloc[lenth]
    mpercent = df5['月度收益'].iloc[0]
    year_percent = df5['年度收益'].iloc[0]

    month = []
    for i in range(lenth+1):
        month.append( str(df5['月份'].iloc[i]) )
    df5['month'] = month
    tmp_m = sb.today[4:6]
    if sb.today[4]==str(0):
        tmp_m = sb.today[5]
    else:
        tmp_m = sb.today[4:6]
    df_m = df5.loc[ df5['month'] == tmp_m ]
    df_m = df_m.fillna(0)
    mprofit = sum( df_m['盈亏'] )
    
#    average = sum( df_m['资金权益'] ) / len(df_m)
#    mpercent = mprofit / average
    '''
    ratio = 1
    for i in range(len(df_m)):
        ratio = ratio* (df_m['盈利率'].iloc[i] + 1)
    mpercent = ratio - 1
    '''
    
    dayreturn = pd.read_excel('300IO日内损益.xlsx')[['日期', name]]
    month_r = []
    for i in range(len(dayreturn)):
        month_r.append(dayreturn['日期'].iloc[i].strftime('%m') )
    dayreturn['month'] = month_r
    dayreturn_m = dayreturn.loc[ dayreturn['month'] == sb.today[4:6] ]
    dayreturn_m = dayreturn_m.fillna(0)
    mreturn = sum( dayreturn_m[name] ) + treturn
    
    dayfee = pd.read_excel('300IO手续费.xlsx')[['日期',name]]
    month_f = []
    for i in range(len(dayfee)):
        month_f.append( dayfee['日期'].iloc[i].strftime('%m') )
    dayfee['month'] = month_f
    dayfee_m = dayfee.loc[ dayfee['month'] == sb.today[4:6] ]
    dayfee_m = dayfee_m.fillna(0)
    mfee = sum( dayfee_m[name] ) + tfee
    
    tmergednew = tmerged[~ ((tmerged['买卖']=='卖') & (tmerged['开平']=='开仓'))]
    tmergednew['手续费'] = -tmergednew['成交数量']*1.7
    tfee_permon = tmergednew.groupby(['EXE_ENDDATE'])['手续费'].sum().reset_index()
    y_vmerged_permon = y_vmerged.groupby(['EXE_ENDDATE'])['Return'].sum().reset_index()
    tmerged_permon = tmerged.groupby(['EXE_ENDDATE'])['Return'].sum().reset_index()
    ymerged_permon = ymerged.groupby(['EXE_ENDDATE'])['Return'].sum().reset_index()
    
    
    yreturn = sum(ymerged['Return'])
    t_alltogether = yreturn + ttotal
    return_frame = pd.DataFrame({'昨仓':[yreturn], '今仓':[treturn], '手续费':[tfee], '日内损益':[ttotal], '合计':[t_alltogether]})  
    
    rowname = ['日期', '今日交易手续费', '日内损益（元） （不含手续费）', '昨日交易对今日影响', '今日损益（元）', '今日收益率', '账户总资产（元）', '本月日内交易总计（元）（不含手续费）', '本月交易手续费', '本月收益（元）', '本月累计收益率','本年累计收益率', 'Call Number', 'Put Number']
    head = pd.DataFrame({'损益情况':rowname, name:[today, tfee, treturn, y_affect_t, tprofit, tpercent, tequity, mreturn, mfee, mprofit, mpercent,year_percent, call_num, put_num]})
    
    return([position_all, position_day, cashgreeks, return_frame, head, tcashgreeks,ymerged3,ymerged2,y_vmerged,strike,y_vmerged_permon,tmerged_permon,tfee_permon, ymerged_permon])
    
ls = GenerateFrame('LS')
dr = GenerateFrame('DR')
db = GenerateFrame('DB')
yx = GenerateFrame('YX')

pls = pd.merge(ls[10],ls[11], on = 'EXE_ENDDATE', how = 'outer')
pls = pd.merge(pls,ls[12], on = 'EXE_ENDDATE', how = 'outer')
pls = pd.merge(pls,ls[13], on = 'EXE_ENDDATE', how = 'outer')
pls.columns = ['月份', '隔日', '日内', '手续费', '昨持']
pls.to_excel('300IOdailyreturn.xlsx')

pdr = pd.merge(dr[10],dr[11], on = 'EXE_ENDDATE', how = 'outer')
pdr = pd.merge(pdr,dr[12], on = 'EXE_ENDDATE', how = 'outer')
pdr = pd.merge(pdr,dr[13], on = 'EXE_ENDDATE', how = 'outer')
pdr.columns = ['月份', '隔日', '日内', '手续费', '昨持']
pdr.to_excel('300IODRdailyreturn.xlsx')


head_o = pd.merge(dr[4], db[4], on='损益情况')
head = pd.merge(head_o, ls[4], on='损益情况')
head.columns = ['损益情况', '德睿', '德睿北京', '聊塑']

today = sb.today

load = sb.etf[['Pre_close', 'RT_LATEST']]
etf = pd.DataFrame({'昨日收盘价':load['Pre_close'], '今日收盘价':load['RT_LATEST'], '涨跌幅': (load['RT_LATEST'] - load['Pre_close']) / load['Pre_close']})
print('etf:',etf)

writer = pd.ExcelWriter(underlying + '德睿每日损益'+today+'.xlsx')
head.to_excel(writer, sheet_name='损益情况', index=False, startrow=4, header=False)
etf.to_excel(writer, sheet_name='损益情况', index=False, startrow=20, header=False)
dr[2].to_excel(writer, sheet_name='DRGreeks', index=False, startrow=2, header=False, float_format='%.0f')
dr[5].to_excel(writer, sheet_name='DRGreeks', index=False, startrow=10, header=False, float_format='%.0f')
dr[3].to_excel(writer, sheet_name='DRGreeks', index=False, startrow=17, header=False, float_format='%.0f')
dr[0].to_excel(writer, sheet_name='DR持仓_当日交易', index=False, startrow=2, header=False)
dr[1].to_excel(writer, sheet_name='DR持仓_当日交易', index=False, startrow=16, header=False)

db[2].to_excel(writer, sheet_name='DBGreeks', index=False, startrow=2, header=False, float_format='%.0f')
db[5].to_excel(writer, sheet_name='DBGreeks', index=False, startrow=10, header=False, float_format='%.0f')
db[3].to_excel(writer, sheet_name='DBGreeks', index=False, startrow=17, header=False, float_format='%.0f')
db[0].to_excel(writer, sheet_name='DB持仓_当日交易', index=False, startrow=2, header=False)
db[1].to_excel(writer, sheet_name='DB持仓_当日交易', index=False, startrow=16, header=False)

ls[2].to_excel(writer, sheet_name='LSGreeks', index=False, startrow=2, header=False, float_format='%.0f')
ls[5].to_excel(writer, sheet_name='LSGreeks', index=False, startrow=10, header=False, float_format='%.0f')
ls[3].to_excel(writer, sheet_name='LSGreeks', index=False, startrow=17, header=False, float_format='%.0f')
ls[0].to_excel(writer, sheet_name='LS持仓_当日交易', index=False, startrow=2, header=False)
ls[1].to_excel(writer, sheet_name='LS持仓_当日交易', index=False, startrow=16, header=False)

workbook1 = writer.book
worksheets = writer.sheets
worksheet1 = worksheets['DR持仓_当日交易']
worksheet3 = worksheets['DRGreeks']
worksheet10 = worksheets['损益情况']

format1 = workbook1.add_format({'align': 'center', 'valign': 'top', 'text_wrap': False})
format2 = workbook1.add_format({'align': 'center', 'valign': 'top', 'text_wrap': False, 'fg_color': 'C0C0C0'})
format3 = workbook1.add_format({'align': 'center', 'valign': 'top', 'text_wrap': False, 'num_format': '#,##0'})
format4 = workbook1.add_format({'align': 'left', 'valign': 'top', 'text_wrap': False})
format6 = workbook1.add_format({'num_format': '#,##0', 'text_wrap': True, 'align': 'left'})
format7 = workbook1.add_format({'num_format': '0.00%', 'align': 'left'})
format5 = workbook1.add_format({'num_format': '0.0000%', 'align': 'left'})
#format8 = workbook1.add_format({'align': 'center'})
format9 = workbook1.add_format({'num_format': '0.00%', 'align': 'center'})


worksheet10.insert_image('D1','logo.png')
for col_num, value in enumerate(head.columns.values):
    worksheet10.write(3, col_num, value, format2)
worksheet10.set_column('A:A', 37, format6)
worksheet10.set_column('B:D', 27, format6)
worksheet10.set_row(9, 15, format5)
worksheet10.set_row(14, 15, format7)

worksheet10.write('A19', '50ETF', format4)
for col_num, value in enumerate(etf.columns.values):
    worksheet10.write(19, col_num, value, format2)
worksheet10.set_row(20, 15, format1)
worksheet10.write('C21', etf['涨跌幅'].iloc[0], format9)


worksheet1.set_column("A:A", 15, format1)
worksheet1.set_column("B:V", 5, format1)
worksheet1.merge_range('A1:C1', 'DR'+today+'持仓', format4)
for col_num, value in enumerate(dr[0].columns.values):
    worksheet1.write(1, col_num, value, format2)
    worksheet1.write(4, col_num, value, format2)
    worksheet1.write(7, col_num, value, format2)
    worksheet1.write(10, col_num, value, format2)

worksheet1.merge_range('A15:C15', 'DR'+today+'当日交易', format4)
for col_num, value in enumerate(dr[1].columns.values):
    worksheet1.write(15, col_num, value, format2)
    worksheet1.write(18, col_num, value, format2)
    worksheet1.write(21, col_num, value, format2)
    worksheet1.write(24, col_num, value, format2)

worksheet3.set_column("A:H", 11, format3)
for col_num, value in enumerate(dr[2].columns.values):
    worksheet3.write(1, col_num, value, format2)
for col_num, value in enumerate(dr[5].columns.values):
    worksheet3.write(9, col_num, value, format2)
for col_num, value in enumerate(dr[3].columns.values):
    worksheet3.write(16, col_num, value, format2)
worksheet3.merge_range('A1:B1', 'DR'+today+'Greeks', format4)
worksheet3.merge_range('A9:B9', 'DR'+today+'Greeks-日内', format4)


worksheet4 = worksheets['DB持仓_当日交易']
worksheet6 = worksheets['DBGreeks']

worksheet4.set_column("A:A", 15, format1)
worksheet4.set_column("B:V", 5, format1)
worksheet4.merge_range('A1:C1', 'DB'+today+'持仓', format4)
for col_num, value in enumerate(db[0].columns.values):
    worksheet4.write(1, col_num, value, format2)
    worksheet4.write(4, col_num, value, format2)
    worksheet4.write(7, col_num, value, format2)
    worksheet4.write(10, col_num, value, format2)

worksheet4.merge_range('A15:C15', 'DB'+today+'当日交易', format4)
for col_num, value in enumerate(db[1].columns.values):
    worksheet4.write(15, col_num, value, format2)
    worksheet4.write(18, col_num, value, format2)
    worksheet4.write(21, col_num, value, format2)
    worksheet4.write(24, col_num, value, format2)

worksheet6.set_column("A:H", 11, format3)
for col_num, value in enumerate(db[2].columns.values):
    worksheet6.write(1, col_num, value, format2)
for col_num, value in enumerate(db[5].columns.values):
    worksheet6.write(9, col_num, value, format2)
for col_num, value in enumerate(db[3].columns.values):
    worksheet6.write(16, col_num, value, format2)
worksheet6.merge_range('A1:B1', 'DB'+today+'Greeks', format4)
worksheet6.merge_range('A9:B9', 'DB'+today+'Greeks-日内', format4)


worksheet7 = worksheets['LS持仓_当日交易']
worksheet9 = worksheets['LSGreeks']

worksheet7.set_column("A:A", 15, format1)
worksheet7.set_column("B:V", 5, format1)
worksheet7.merge_range('A1:C1', 'LS'+today+'持仓', format4)
for col_num, value in enumerate(ls[0].columns.values):
    worksheet7.write(1, col_num, value, format2)
    worksheet7.write(4, col_num, value, format2)
    worksheet7.write(7, col_num, value, format2)
    worksheet7.write(10, col_num, value, format2)

worksheet7.merge_range('A15:C15', 'LS'+today+'当日交易', format4)
for col_num, value in enumerate(ls[1].columns.values):
    worksheet7.write(15, col_num, value, format2)
    worksheet7.write(18, col_num, value, format2)
    worksheet7.write(21, col_num, value, format2)
    worksheet7.write(24, col_num, value, format2)

worksheet9.set_column("A:H", 11, format3)
for col_num, value in enumerate(ls[2].columns.values):
    worksheet9.write(1, col_num, value, format2)
for col_num, value in enumerate(ls[5].columns.values):
    worksheet9.write(9, col_num, value, format2)
for col_num, value in enumerate(ls[3].columns.values):
    worksheet9.write(16, col_num, value, format2)
worksheet9.merge_range('A1:B1', 'LS'+today+'Greeks', format4)
worksheet9.merge_range('A9:B9', 'LS'+today+'Greeks-日内', format4)

worksheet10.set_row(15, 15, format5)
writer.save()
writer.close()



##_________________________________YX_____________________________________________________
'''
writer = pd.ExcelWriter(underlying + 'YX每日损益'+ today +'.xlsx')
yx[4].to_excel(writer, sheet_name='YX损益情况', index=False, startrow=4, header=False)
yx[2].to_excel(writer, sheet_name='YXGreeks', index=False, startrow=2, header=False, float_format='%.0f')
yx[5].to_excel(writer, sheet_name='YXGreeks', index=False, startrow=10, header=False, float_format='%.0f')
yx[3].to_excel(writer, sheet_name='YXGreeks', index=False, startrow=17, header=False, float_format='%.0f')
yx[0].to_excel(writer, sheet_name='YX持仓_当日交易', index=False, startrow=2, header=False)
yx[1].to_excel(writer, sheet_name='YX持仓_当日交易', index=False, startrow=16, header=False)


workbook1 = writer.book
worksheets = writer.sheets
worksheet1 = worksheets['YX持仓_当日交易']
worksheet3 = worksheets['YXGreeks']
worksheet4 = worksheets['YX损益情况']

format1 = workbook1.add_format({'align': 'center', 'valign': 'top', 'text_wrap': False})
format2 = workbook1.add_format({'align': 'center', 'valign': 'top', 'text_wrap': False, 'fg_color': 'C0C0C0'})
format3 = workbook1.add_format({'align': 'center', 'valign': 'top', 'text_wrap': False, 'num_format': '#,##0'})
format4 = workbook1.add_format({'align': 'left', 'valign': 'top', 'text_wrap': False})
format5 = workbook1.add_format({'num_format': '0.0000%', 'align': 'left'})
format6 = workbook1.add_format({'num_format': '#,##0', 'align': 'left'})
format7 = workbook1.add_format({'num_format': '0.00%', 'align': 'left'})
#'border': 1, 
  
worksheet4.insert_image('B1','logo.png')
worksheet4.set_column('A:D', 40, format6)
for col_num, value in enumerate(yx[4].columns.values):
    worksheet4.write(3, col_num, value, format2)
worksheet4.set_row(9, 15, format5)
worksheet4.set_row(14, 15, format7)


worksheet1.set_column("A:A", 15, format1)
worksheet1.set_column("B:V", 5, format1)
worksheet1.merge_range('A1:C1', 'YX'+today+'持仓', format4)
for col_num, value in enumerate(yx[0].columns.values):
    worksheet1.write(1, col_num, value, format2)
    worksheet1.write(4, col_num, value, format2)
    worksheet1.write(7, col_num, value, format2)
    worksheet1.write(10, col_num, value, format2)

worksheet1.merge_range('A15:C15', 'YX'+today+'当日交易', format4)
for col_num, value in enumerate(yx[1].columns.values):
    worksheet1.write(15, col_num, value, format2)
    worksheet1.write(18, col_num, value, format2)
    worksheet1.write(21, col_num, value, format2)
    worksheet1.write(24, col_num, value, format2)

worksheet3.set_column("A:H", 11, format3)
for col_num, value in enumerate(yx[2].columns.values):
    worksheet3.write(1, col_num, value, format2)
for col_num, value in enumerate(yx[5].columns.values):
    worksheet3.write(9, col_num, value, format2)
for col_num, value in enumerate(yx[3].columns.values):
    worksheet3.write(16, col_num, value, format2)
worksheet3.merge_range('A1:B1', 'YX'+today+'Greeks', format4)
worksheet3.merge_range('A9:B9', 'YX'+today+'Greeks-日内', format4)

writer.save()
writer.close()
'''

