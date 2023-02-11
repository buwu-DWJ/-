# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 15:21:24 2019

@author: mrlia
"""
import pandas as pd
import symbols as sb
import datetime

today = sb.today
today = today[0:4] + '年' + today[4].strip('0') + today[5] + '月' + today[6].strip('0') + today[7] + '日'
yesterday = sb.yesterday
yesterday = yesterday[0:4] + '年' + yesterday[4].strip('0') + yesterday[5] + '月' + yesterday[6].strip('0') + yesterday[7] + '日'

d = sb.data
dates = sorted(list(set(d['EXE_ENDDATE'])))
dates.append('total')

for i in range(4):
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
    put_num = sum( merged_p['Position']) 
    
    strike = ['']
    strike.extend(sorted(list(set(d['EXE_PRICE']))))
    
    for i in range(1,5):
        globals()['c'+str(i)] = sb.Reconstruct(locals()['merged'+str(i)], dates[i-1], strike, 'call')
        globals()['p'+str(i)] = sb.Reconstruct(locals()['merged'+str(i)], dates[i-1], strike, 'put')
    position_all = pd.DataFrame([c1,p1,strike,c2,p2,strike,c3,p3,strike,c4,p4], columns=strike)
    
    for i in strike:
        if (position_all[i].iloc[0] == position_all[i].iloc[1] == position_all[i].iloc[3] == position_all[i].iloc[4] == position_all[i].iloc[6] == position_all[i].iloc[7] == position_all[i].iloc[9] == position_all[i].iloc[10] == '') :
            position_all = position_all.drop([i], axis=1)

   
    df3 = sb.LoadPosition(yesterday+'期权持仓报表'+ name +'.csv')
    ygrouped = df3.groupby(['Contract','Month'])['Position'].sum().reset_index()
    ymerged = pd.merge(ygrouped, d, on='Contract')
    ymerged['Return'] = ymerged['Position']  * ((ymerged['RT_BID1']+ymerged['RT_ASK1'])/2 - ymerged['PRE_CLOSE']) * ymerged['EXE_RATIO']
    #yreturn = sum(ymerged['Return'])
    #return_frame = pd.DataFrame({'昨仓':[yreturn], '今仓':[treturn], '手续费':[tfee], '日内损益':[ttotal], '合计':[t_alltogether]})
#'gaile     
    ymerged2 = sb.LoadVolume(yesterday+'期权成交报表'+name+'.csv')
    ymerged2 = ymerged2.replace('卖',-1)
    ymerged2 = ymerged2.replace('买',1)
    ymerged2 = ymerged2.groupby('合约代码')['买卖'].sum()
    ymerged2 = ymerged2.reset_index()
    #ymerged2 = pd.merge(df33, d, on='Contract')
#'gaile     
    
    df4 = sb.LoadVolume(today+'期权成交报表'+name+'.csv')
    tmerged = pd.merge(df4, d, on='Contract')
    tmerged['Return'] = tmerged['Position'] * ((tmerged['RT_BID1'] + tmerged['RT_ASK1'])/2 - tmerged['成交价格']) * tmerged['EXE_RATIO']
    treturn = sum(tmerged['Return'])
    
    dfnew = df4.loc[~ ((df4['买卖']=='卖') & (df4['开平']=='开仓')) ]
    tfee = -sum(dfnew['成交数量']*1.7)
    ttotal = treturn + tfee
    #t_alltogether = yreturn + ttotal 
    
    tgrouped = tmerged.groupby(['EXE_ENDDATE','EXE_PRICE','EXE_MODE','Contract'])['Position'].sum().reset_index()
    for i in range(1,5):
       globals()['c_'+str(i)] = sb.Reconstruct_day(tgrouped, sorted(list(set(d['EXE_ENDDATE']))), strike, 'call', i)
       globals()['p_'+str(i)] = sb.Reconstruct_day(tgrouped, sorted(list(set(d['EXE_ENDDATE']))), strike, 'put', i)
    position_day = pd.DataFrame([c_1,p_1, strike,c_2,p_2, strike, c_3,p_3, strike,c_4,p_4], columns=strike)
    
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
    y_vgrouped = df2.groupby(['Contract'])['Position'].sum().reset_index()
    y_vmerged = pd.merge(y_vgrouped, d, on='Contract')
    
#'gaile     
    
    ymerged2['合约代码'] = [str(i)+'.SH' for i in ymerged2['合约代码']]
    ymerged2.rename(columns=({'合约代码':'Contract'}),inplace=True)
    ymerged3 = pd.merge(y_vmerged,ymerged2,on='Contract',how='left')

    
    y_vmerged['Return'] = ymerged3['Position']  * ((ymerged3['RT_BID1']+ymerged3['RT_ASK1'])/2 - ymerged3['PRE_CLOSE']) * ymerged3['EXE_RATIO']
#'gaile     

    y_affect_t = sum(y_vmerged['Return'])
    
    
    df5 = pd.read_excel('净值统计'+name+'.xlsx')
    lenth = len(df5)-1
    tprofit = df5['盈亏'].iloc[lenth]
    tpercent = df5['盈利率'].iloc[lenth]
    tequity = df5['资金权益'].iloc[lenth]
    
    month = []
    for i in range(lenth+1):
        month.append( str(df5['日期'].iloc[i])[4:6] )
    df5['month'] = month
    df_m = df5.loc[ df5['month'] == sb.today[4:6] ]
    print(df_m)
    mprofit = sum( df_m['盈亏'] )
    
    average = sum( df_m['资金权益'] ) / len(df_m)
    mpercent = mprofit / average
    '''
    ratio = 1
    for i in range(len(df_m)):
        ratio = ratio* (df_m['盈利率'].iloc[i] + 1)
    mpercent = ratio - 1
    '''
    

    dayreturn = pd.read_excel('日内损益.xlsx')[['日期', name]]
    month_r = []
    for i in range(len(dayreturn)):
        month_r.append( dayreturn['日期'].iloc[i].strftime('%m') )
    dayreturn['month'] = month_r
    dayreturn_m = dayreturn.loc[ dayreturn['month'] == sb.today[4:6] ]
    mreturn = sum( dayreturn_m[name] ) + treturn
    
    dayfee = pd.read_excel('手续费.xlsx')[['日期',name]]
    month_f = []
    for i in range(len(dayfee)):
        month_f.append( dayfee['日期'].iloc[i].strftime('%m') )
    dayfee['month'] = month_f
    dayfee_m = dayfee.loc[ dayfee['month'] == sb.today[4:6] ]
    mfee = sum( dayfee_m[name] ) + tfee
    
    
    t_alltogether = tprofit
    yreturn = t_alltogether - ttotal
    return_frame = pd.DataFrame({'昨仓':[yreturn], '今仓':[treturn], '手续费':[tfee], '日内损益':[ttotal], '合计':[t_alltogether]})  
    
    rowname = ['日期', '今日交易手续费', '日内损益（元） （不含手续费）', '昨日交易对今日影响', '今日损益（元）', '今日收益率', '账户总资产（元）', '本月日内交易总计（元）（不含手续费）', '本月交易手续费', '本月收益（元）', '本月累计收益率', 'Call Number', 'Put Number']
    head = pd.DataFrame({'损益情况':rowname, name:[today, tfee, treturn, y_affect_t, tprofit, tpercent, tequity, mreturn, mfee, mprofit, mpercent, call_num, put_num]})
    
    return([position_all, position_day, cashgreeks, return_frame, head, tcashgreeks,ymerged2])

yx = GenerateFrame('YX')

today = sb.today

writer = pd.ExcelWriter('YX每日损益'+ today +'.xlsx')
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

worksheet4.set_row(15, 15, format5)
writer.save()
writer.close()



#worksheet2 = worksheets['YX当日交易']

#worksheet1.set_row(4, 15, format2)
#worksheet1.set_row(7, 15, format2)
#worksheet1.set_row(10, 15, format2)
#worksheet1.set_row(18, 15, format2)
#worksheet1.set_row(21, 15, format2)
#worksheet1.set_row(24, 15, format2)
#worksheet1.insert_image('S2','logo.png')

#worksheet3.insert_image('I2','logo.png')
'''
worksheet2.set_column("A:A", 15, format1)
worksheet2.set_column("B:V", 5, format1)
worksheet2.set_row(8, 15, format2)
worksheet2.set_row(11, 15, format2)
worksheet2.set_row(14, 15, format2)
for col_num, value in enumerate(yx[1].columns.values):
    worksheet2.write(5, col_num, value, format2)
worksheet2.merge_range('A5:C5', 'YX'+today+'当日交易', format4)
worksheet2.insert_image('S2','logo.png')
'''

'''
worksheet4.set_row(6, 15, format6)
worksheet4.set_row(7, 15, format6)
worksheet4.set_row(8, 15, format6)
worksheet4.set_row(9, 15, format6)
worksheet4.set_row(10, 15, format6)
worksheet4.set_row(11, 15, format7)
worksheet4.set_row(12, 15, format6)
worksheet4.set_row(13, 15, format6)
worksheet4.set_row(14, 15, format6)
worksheet4.set_row(15, 15, format6)
worksheet4.set_row(16, 15, format7)
worksheet4.set_row(17, 15, format6)
worksheet4.set_row(18, 15, format6)
'''