# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 16:12:38 2020

@author: mrlia
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Dec 26 14:14:27 2019

@author: mrlia
"""

import pandas as pd
import numpy as np
import output_XH_SH300 as SH300
import output_XH_SZ300 as SZ300
import output_XH_ETF50 as ETF50
#import output_LS7_SZ300 as SZ300

import symbolsETF50 as sbETF50
import symbolsSH300 as sbSH300
import symbolsSZ300 as sbSZ300

#import symbolsSZ300 as sbSZ300

#dr = ETF50.dr.append(SH300.dr)
#db = ETF50.db.append(SH300.db)
xh7 = ETF50.xh.append(SH300.xh)
#ls = ETF50.ls.append(SH300.ls)
xh7 = ETF50.xh.append(SZ300.xh)

underlying = ['ETF50','SH300','SZ300'] #SZ
account2 = ['xh']



for n in underlying:
    locals()[n +'xh'] = locals()[n].xh
    
xh1 = ETF50xh[4]
import copy
#print(ETF50db[4])
xh = copy.deepcopy(ETF50xh)


    
for ud in underlying:

    today = sbETF50.today
    underP = locals()['sb' + ud].etf[['Pre_close', 'RT_LATEST']]
    locals()[ud + 'etf'] = pd.DataFrame({'昨日收盘价':underP['Pre_close'], '今日收盘价':underP['RT_LATEST'], '涨跌幅': (underP['RT_LATEST'] - underP['Pre_close']) / underP['Pre_close']})
#head_o = pd.merge(dr[4], dr[4], on='损益情况')
#head = pd.merge(head_o, ls[4], on='损益情况')
#head.columns = ['损益情况', '德睿', '德睿北京', '聊塑']
#-----------------------------------------------------------------------------------
#LS7

for j in account2:
    
    locals()['tfee' + j] =0
    locals()['tr' + j] =0
    locals()['ytt' + j] =0
    locals()['mtr' + j] =0
    locals()['mtfee' + j]=0
    locals()['cnum' + j]=0
    locals()['pnum' + j] =0
    
    for i in underlying:
        tmp = locals()[i + j]
        locals()['tfee' + j] += tmp[4].iloc[1,1]
        locals()['tr' + j] += tmp[4].iloc[2,1]
        locals()['ytt' + j] += tmp[4].iloc[3,1]
        locals()['mtr' + j] += tmp[4].iloc[7,1]
        locals()['mtfee' + j] += tmp[4].iloc[8,1]
        locals()['cnum' + j] += tmp[4].iloc[12,1]
        locals()['pnum' + j] += tmp[4].iloc[13,1]
#        locals()['mtprofit' + j] = tmp[4].iloc[9,1]

        
    locals()[j+'1'].iloc[1,1] = locals()['tfee' + j]
    locals()[j+'1'].iloc[2,1] = locals()['tr' + j]
    locals()[j+'1'].iloc[3,1] = locals()['ytt' + j]
    locals()[j+'1'].iloc[7,1] = locals()['mtr' + j]
    locals()[j+'1'].iloc[8,1] = locals()['mtfee' + j]
#    locals()[j+'1'].iloc[10,1] = locals()[j+'1'].iloc[9,1] / tmp[4].iloc[6,1]
#    print(locals()[j+'1'].iloc[9,1] / tmp[4].iloc[6,1])
    locals()[j+'1'].iloc[12,1] = locals()['cnum' + j]
    locals()[j+'1'].iloc[13,1] = locals()['pnum' + j]

for j in account2:
    locals()[j][4] =locals()[j + str(1)] 
writer = pd.ExcelWriter('XH每日损益'+ today +'.xlsx')

xh[4].to_excel(writer, sheet_name='XH损益情况', index=False, startrow=4, header=False)

for ud in underlying:
    locals()[ud+'xh'][2].to_excel(writer, sheet_name=ud + 'XHGreeks', index=False, startrow=2, header=False, float_format='%.0f')
    locals()[ud+'xh'][5].to_excel(writer, sheet_name=ud + 'XHGreeks', index=False, startrow=10, header=False, float_format='%.0f')
    locals()[ud+'xh'][3].to_excel(writer, sheet_name=ud + 'XHGreeks', index=False, startrow=17, header=False, float_format='%.0f')
    locals()[ud+'xh'][0].to_excel(writer, sheet_name=ud + 'XH持仓_当日交易', index=False, startrow=2, header=False)
    locals()[ud+'xh'][1].to_excel(writer, sheet_name=ud + 'XH持仓_当日交易', index=False, startrow=16, header=False)


workbook1 = writer.book
worksheets = writer.sheets
worksheet1 = worksheets['ETF50XH持仓_当日交易']
worksheet3 = worksheets['ETF50XHGreeks']
worksheet4 = worksheets['XH损益情况']


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
for col_num, value in enumerate(xh[4].columns.values):
    worksheet4.write(3, col_num, value, format2)
worksheet4.set_row(9, 15, format5)
worksheet4.set_row(14, 15, format7)


worksheet1.set_column("A:A", 15, format1)
worksheet1.set_column("B:V", 5, format1)
worksheet1.merge_range('A1:C1', 'XH'+today+'持仓', format4)
for col_num, value in enumerate(xh[0].columns.values):
    worksheet1.write(1, col_num, value, format2)
    worksheet1.write(4, col_num, value, format2)
    worksheet1.write(7, col_num, value, format2)
    worksheet1.write(10, col_num, value, format2)

worksheet1.merge_range('A15:C15', 'XH'+today+'当日交易', format4)
for col_num, value in enumerate(xh[1].columns.values):
    worksheet1.write(15, col_num, value, format2)
    worksheet1.write(18, col_num, value, format2)
    worksheet1.write(21, col_num, value, format2)
    worksheet1.write(24, col_num, value, format2)

worksheet3.set_column("A:H", 11, format3)
for col_num, value in enumerate(xh[2].columns.values):
    worksheet3.write(1, col_num, value, format2)
for col_num, value in enumerate(xh[5].columns.values):
    worksheet3.write(9, col_num, value, format2)
for col_num, value in enumerate(xh[3].columns.values):
    worksheet3.write(16, col_num, value, format2)
worksheet3.merge_range('A1:B1', 'XH'+today+'Greeks', format4)
worksheet3.merge_range('A9:B9', 'XH'+today+'Greeks-日内', format4)

#---------------------------------------------------------------
#新的表
worksheets = writer.sheets
worksheet11 = worksheets['SH300XH持仓_当日交易']
worksheet13 = worksheets['SH300XHGreeks']
#worksheet14 = worksheets['SH300YX损益情况']
#
#  
#worksheet14.insert_image('B1','logo.png')
#worksheet14.set_column('A:D', 40, format6)
#for col_num, value in enumerate(SH300yx[4].columns.values):
#    worksheet14.write(3, col_num, value, format2)
#worksheet14.set_row(9, 15, format5)
#worksheet14.set_row(14, 15, format7)l


worksheet11.set_column("A:A", 15, format1)
worksheet11.set_column("B:V", 5, format1)
worksheet11.merge_range('A1:C1', 'XH'+today+'持仓', format4)
for col_num, value in enumerate(SH300xh[0].columns.values):
    worksheet11.write(1, col_num, value, format2)
    worksheet11.write(4, col_num, value, format2)
    worksheet11.write(7, col_num, value, format2)
    worksheet11.write(10, col_num, value, format2)

worksheet11.merge_range('A15:C15', 'XH'+today+'当日交易', format4)
for col_num, value in enumerate(SH300xh[1].columns.values):
    worksheet11.write(15, col_num, value, format2)
    worksheet11.write(18, col_num, value, format2)
    worksheet11.write(21, col_num, value, format2)
    worksheet11.write(24, col_num, value, format2)

worksheet13.set_column("A:H", 11, format3)
for col_num, value in enumerate(SH300xh[2].columns.values):
    worksheet13.write(1, col_num, value, format2)
for col_num, value in enumerate(SH300xh[5].columns.values):
    worksheet13.write(9, col_num, value, format2)
for col_num, value in enumerate(SH300xh[3].columns.values):
    worksheet13.write(16, col_num, value, format2)
worksheet13.merge_range('A1:B1', 'XH'+today+'Greeks', format4)
worksheet13.merge_range('A9:B9', 'XH'+today+'Greeks-日内', format4)

#---------------------------------------------------------------
#新的表
worksheets = writer.sheets
worksheet21 = worksheets['SZ300XH持仓_当日交易']
worksheet23 = worksheets['SZ300XHGreeks']
worksheet21.set_column("A:A", 15, format1)
worksheet21.set_column("B:V", 5, format1)
worksheet21.merge_range('A1:C1', 'XH'+today+'持仓', format4)
for col_num, value in enumerate(SZ300xh[0].columns.values):
    worksheet21.write(1, col_num, value, format2)
    worksheet21.write(4, col_num, value, format2)
    worksheet21.write(7, col_num, value, format2)
    worksheet21.write(10, col_num, value, format2)

worksheet21.merge_range('A15:C15', 'XH'+today+'当日交易', format4)
for col_num, value in enumerate(SZ300xh[1].columns.values):
    worksheet21.write(15, col_num, value, format2)
    worksheet21.write(18, col_num, value, format2)
    worksheet21.write(21, col_num, value, format2)
    worksheet21.write(24, col_num, value, format2)

worksheet23.set_column("A:H", 11, format3)
for col_num, value in enumerate(SZ300xh[2].columns.values):
    worksheet23.write(1, col_num, value, format2)
for col_num, value in enumerate(SZ300xh[5].columns.values):
    worksheet23.write(9, col_num, value, format2)
for col_num, value in enumerate(SZ300xh[3].columns.values):
    worksheet23.write(16, col_num, value, format2)
worksheet23.merge_range('A1:B1', 'XH'+today+'Greeks', format4)
worksheet23.merge_range('A9:B9', 'XH'+today+'Greeks-日内', format4)


'''
i = 1
while i < 100:
    try:
        name = locals()['worksheet'+i].name
        locals()['worksheet'+i].write(1, 'D', name)
    except:
        continue
    i = i + 1
'''
'''
#------------------YX的第三个标的
worksheets = writer.sheets
worksheet21 = worksheets['SZ300YX持仓_当日交易']
worksheet23 = worksheets['SZ300YXGreeks']


worksheet21.set_column("A:A", 15, format1)
worksheet21.set_column("B:V", 5, format1)
worksheet21.merge_range('A1:C1', 'YX'+today+'持仓', format4)
for col_num, value in enumerate(SZ300yx[0].columns.values):
    worksheet21.write(1, col_num, value, format2)
    worksheet21.write(4, col_num, value, format2)
    worksheet21.write(7, col_num, value, format2)
    worksheet21.write(10, col_num, value, format2)

worksheet21.merge_range('A15:C15', 'YX'+today+'当日交易', format4)
for col_num, value in enumerate(SZ300yx[1].columns.values):
    worksheet21.write(15, col_num, value, format2)
    worksheet21.write(18, col_num, value, format2)
    worksheet21.write(21, col_num, value, format2)
    worksheet21.write(24, col_num, value, format2)

worksheet23.set_column("A:H", 11, format3)
for col_num, value in enumerate(SZ300yx[2].columns.values):
    worksheet23.write(1, col_num, value, format2)
for col_num, value in enumerate(SZ300yx[5].columns.values):
    worksheet23.write(9, col_num, value, format2)
for col_num, value in enumerate(SZ300yx[3].columns.values):
    worksheet23.write(16, col_num, value, format2)
worksheet23.merge_range('A1:B1', 'YX'+today+'Greeks', format4)
worksheet23.merge_range('A9:B9', 'YX'+today+'Greeks-日内', format4)
'''
format10 = workbook1.add_format({'align': 'center', 'valign': 'top',  'bg_color':'#ffd8b1'})
j=0
for ud in underlying:  
    locals()['worksheet' + str(int(1+j*10))].write(0, 3, ud,format10)
    locals()['worksheet' + str(int(3+j*10))].write(0, 3, ud,format10)
    j+=1

# 每天跑完之后把手续费和日内交易记录到表格中
#for ud in underlying: 
'''
ud = underlying[0]
with pd.ExcelWriter(ud + '日内损益'+'.xlsx',engine = 'openpyxl',mode='a') as writer:
#workbook1 = writer.book
#worksheets = writer.sheets
#worksheet1 = worksheets['日内损益']
#    ls[3]['日内损益'][0].to_excel(writer, index=False, startrow=-1,column = 6)
    writer.write(-1,5,ls[3]['日内损益'][0])
    
import os
import xlrd
import xlwt
from xlutils import copy

ud = underlying[0]
filename = ud + '日内损益'+'.xlsx'
wb = xlrd.open_workbook(filename)
sheet = wb.sheet_by_index(0)
row = sheet.nrows
col = sheet.ncols
nb = copy(wb)
ns = nb.get_sheet(0)
ns.write(row, 5, ls[3]['日内损益'][0])
nb.save(filename)
'''
worksheet4.set_row(15,15, format5)
writer.save()
writer.close()
