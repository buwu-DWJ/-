# -*- coding: utf-8 -*-
"""
Created on Thu Dec 26 14:14:27 2019

@author: mrlia
"""

import pandas as pd
import numpy as np
import output_LS3_SH300 as SH300
import output_LS3_ETF50 as ETF50
#import output_LS3_SZ300 as SZ300

import symbolsETF50 as sbETF50
import symbolsSH300 as sbSH300
#import symbolsSZ300 as sbSZ300


underlying = ['ETF50','SH300']
account1 = ['ls3','ls4']



for n in underlying:
    locals()[n +'ls3'] = locals()[n].ls3
    locals()[n +'ls4'] = locals()[n].ls4
#    locals()[n +'ls'] = locals()[n].ls
    
ls31 = ETF50ls3[4]
ls41 = ETF50ls4[4]
#ls1 = ETF50ls[4]
import copy
#print(ETF50db[4])
ls3 = copy.deepcopy(ETF50ls3)
ls4 = copy.deepcopy(ETF50ls4)
#ls = copy.deepcopy(ETF50ls)


for j in account1:
    
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
        
    locals()[j+'1'].iloc[1,1] = locals()['tfee' + j]
    locals()[j+'1'].iloc[2,1] = locals()['tr' + j]
    locals()[j+'1'].iloc[3,1] = locals()['ytt' + j]
    locals()[j+'1'].iloc[7,1] = locals()['mtr' + j]
    locals()[j+'1'].iloc[8,1] = locals()['mtfee' + j]
    locals()[j+'1'].iloc[12,1] = locals()['cnum' + j]
    locals()[j+'1'].iloc[13,1] = locals()['pnum' + j]

for j in account1:
    locals()[j][4] =locals()[j + str(1)] 
    
for ud in underlying:
    today = sbETF50.today

    underP = locals()['sb' + ud].etf[['Pre_close', 'RT_LATEST']]
    locals()[ud + 'etf'] = pd.DataFrame({'昨日收盘价':underP['Pre_close'], '今日收盘价':underP['RT_LATEST'], '涨跌幅': (underP['RT_LATEST'] - underP['Pre_close']) / underP['Pre_close']})
head = pd.merge(ls3[4], ls4[4], on='损益情况')
#head = pd.merge(head_o, ls[4], on='损益情况')
head.columns = ['损益情况', '聊塑3号', '聊塑4号']

writer = pd.ExcelWriter('聊塑3号、4号每日损益'+today+'.xlsx')
head.to_excel(writer, sheet_name='损益情况', index=False, startrow=4, header=False)
num=0
for ud in underlying:
    locals()[ud + 'etf'].to_excel(writer, sheet_name='损益情况', index=False, startrow=20+num*3, header=False)
    num+=1
for ud in underlying:
    locals()[ud+'ls3'][2].to_excel(writer, sheet_name= ud + 'LS3Greeks', index=False, startrow=2, header=False, float_format='%.0f')
    locals()[ud+'ls3'][5].to_excel(writer, sheet_name=ud + 'LS3Greeks', index=False, startrow=10, header=False, float_format='%.0f')
    locals()[ud+'ls3'][3].to_excel(writer, sheet_name=ud + 'LS3Greeks', index=False, startrow=17, header=False, float_format='%.0f')
    locals()[ud+'ls3'][0].to_excel(writer, sheet_name=ud + 'LS3持仓_当日交易', index=False, startrow=2, header=False)
    locals()[ud+'ls3'][1].to_excel(writer, sheet_name=ud + 'LS3持仓_当日交易', index=False, startrow=16, header=False)

    locals()[ud+'ls4'][2].to_excel(writer, sheet_name=ud + 'LS4Greeks', index=False, startrow=2, header=False, float_format='%.0f')
    locals()[ud+'ls4'][5].to_excel(writer, sheet_name=ud + 'LS4Greeks', index=False, startrow=10, header=False, float_format='%.0f')
    locals()[ud+'ls4'][3].to_excel(writer, sheet_name=ud + 'LS4Greeks', index=False, startrow=17, header=False, float_format='%.0f')
    locals()[ud+'ls4'][0].to_excel(writer, sheet_name=ud + 'LS4持仓_当日交易', index=False, startrow=2, header=False)
    locals()[ud+'ls4'][1].to_excel(writer, sheet_name=ud + 'LS4持仓_当日交易', index=False, startrow=16, header=False)

#    locals()[ud+'ls'][2].to_excel(writer, sheet_name=ud + 'LSGreeks', index=False, startrow=2, header=False, float_format='%.0f')
#    locals()[ud+'ls'][5].to_excel(writer, sheet_name=ud + 'LSGreeks', index=False, startrow=10, header=False, float_format='%.0f')
#    locals()[ud+'ls'][3].to_excel(writer, sheet_name=ud + 'LSGreeks', index=False, startrow=17, header=False, float_format='%.0f')
#    locals()[ud+'ls'][0].to_excel(writer, sheet_name=ud + 'LS持仓_当日交易', index=False, startrow=2, header=False)
#    locals()[ud+'ls'][1].to_excel(writer, sheet_name=ud + 'LS持仓_当日交易', index=False, startrow=16, header=False)


workbook1 = writer.book
worksheets = writer.sheets
worksheet1 = worksheets['ETF50LS3持仓_当日交易']
worksheet3 = worksheets['ETF50LS3Greeks']
worksheet10 = worksheets['损益情况']
worksheet11 = worksheets['SH300LS3持仓_当日交易']
worksheet13 = worksheets['SH300LS3Greeks']
#worksheet21 = worksheets['SZ300LS3持仓_当日交易']
#worksheet23 = worksheets['SZ300LS3Greeks']


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
for col_num, value in enumerate(ETF50etf.columns.values):
    worksheet10.write(19, col_num, value, format2)
worksheet10.set_row(20, 15, format1)
worksheet10.write('C21', ETF50etf['涨跌幅'].iloc[0], format9)

worksheet10.write('A22', '300SHETF', format4)
for col_num, value in enumerate(SH300etf.columns.values):
    worksheet10.write(22, col_num, value, format2)
worksheet10.set_row(23, 15, format1)
worksheet10.write('C24', SH300etf['涨跌幅'].iloc[0], format9)

'''
worksheet10.write('A25', '300SZETF', format4)
for col_num, value in enumerate(SZ300etf.columns.values):
    worksheet10.write(25, col_num, value, format2)
worksheet10.set_row(26, 15, format1)
worksheet10.write('C27', SZ300etf['涨跌幅'].iloc[0], format9)
'''


worksheet1.set_column("A:A", 15, format1)
worksheet1.set_column("B:V", 5, format1)
worksheet1.merge_range('A1:C1', 'LS3'+today+'持仓', format4)
for col_num, value in enumerate(ls3[0].columns.values):
    worksheet1.write(1, col_num, value, format2)
    worksheet1.write(4, col_num, value, format2)
    worksheet1.write(7, col_num, value, format2)
    worksheet1.write(10, col_num, value, format2)

worksheet1.merge_range('A15:C15', 'LS3'+today+'当日交易', format4)
for col_num, value in enumerate(ls3[1].columns.values):
    worksheet1.write(15, col_num, value, format2)
    worksheet1.write(18, col_num, value, format2)
    worksheet1.write(21, col_num, value, format2)
    worksheet1.write(24, col_num, value, format2)

worksheet3.set_column("A:H", 11, format3)
for col_num, value in enumerate(ls3[2].columns.values):
    worksheet3.write(1, col_num, value, format2)
for col_num, value in enumerate(ls3[5].columns.values):
    worksheet3.write(9, col_num, value, format2)
for col_num, value in enumerate(ls3[3].columns.values):
    worksheet3.write(16, col_num, value, format2)
worksheet3.merge_range('A1:B1', 'LS3'+today+'Greeks', format4)
worksheet3.merge_range('A9:B9', 'LS3'+today+'Greeks-日内', format4)


worksheet4 = worksheets['ETF50LS4持仓_当日交易']
worksheet6 = worksheets['ETF50LS4Greeks']

worksheet4.set_column("A:A", 15, format1)
worksheet4.set_column("B:V", 5, format1)
worksheet4.merge_range('A1:C1', 'LS4'+today+'持仓', format4)
for col_num, value in enumerate(ls4[0].columns.values):
    worksheet4.write(1, col_num, value, format2)
    worksheet4.write(4, col_num, value, format2)
    worksheet4.write(7, col_num, value, format2)
    worksheet4.write(10, col_num, value, format2)

worksheet4.merge_range('A15:C15', 'LS4'+today+'当日交易', format4)
for col_num, value in enumerate(ls4[1].columns.values):
    worksheet4.write(15, col_num, value, format2)
    worksheet4.write(18, col_num, value, format2)
    worksheet4.write(21, col_num, value, format2)
    worksheet4.write(24, col_num, value, format2)

worksheet6.set_column("A:H", 11, format3)
for col_num, value in enumerate(ls4[2].columns.values):
    worksheet6.write(1, col_num, value, format2)
for col_num, value in enumerate(ls4[5].columns.values):
    worksheet6.write(9, col_num, value, format2)
for col_num, value in enumerate(ls4[3].columns.values):
    worksheet6.write(16, col_num, value, format2)
worksheet6.merge_range('A1:B1', 'LS4'+today+'Greeks', format4)
worksheet6.merge_range('A9:B9', 'LS4'+today+'Greeks-日内', format4)


#worksheet7 = worksheets['ETF50LS持仓_当日交易']
#worksheet9 = worksheets['ETF50LSGreeks']
#
#worksheet7.set_column("A:A", 15, format1)
#worksheet7.set_column("B:V", 5, format1)
#worksheet7.merge_range('A1:C1', 'LS'+today+'持仓', format4)
#for col_num, value in enumerate(ls[0].columns.values):
#    worksheet7.write(1, col_num, value, format2)
#    worksheet7.write(4, col_num, value, format2)
#    worksheet7.write(7, col_num, value, format2)
#    worksheet7.write(10, col_num, value, format2)
#
#worksheet7.merge_range('A15:C15', 'LS'+today+'当日交易', format4)
#for col_num, value in enumerate(ls[1].columns.values):
#    worksheet7.write(15, col_num, value, format2)
#    worksheet7.write(18, col_num, value, format2)
#    worksheet7.write(21, col_num, value, format2)
#    worksheet7.write(24, col_num, value, format2)
#
#worksheet9.set_column("A:H", 11, format3)
#for col_num, value in enumerate(ls[2].columns.values):
#    worksheet9.write(1, col_num, value, format2)
#for col_num, value in enumerate(ls[5].columns.values):
#    worksheet9.write(9, col_num, value, format2)
#for col_num, value in enumerate(ls[3].columns.values):
#    worksheet9.write(16, col_num, value, format2)
#worksheet9.merge_range('A1:B1', 'LS'+today+'Greeks', format4)
#worksheet9.merge_range('A9:B9', 'LS'+today+'Greeks-日内', format4)
#
##---------------------------------------------------------------------
##调整第二个标的的格式
worksheet11.set_column("A:A", 15, format1)
worksheet11.set_column("B:V", 5, format1)
worksheet11.merge_range('A1:C1', 'LS3'+today+'持仓', format4)

for col_num, value in enumerate(SH300ls3[0].columns.values):
    worksheet11.write(1, col_num, value, format2)
    worksheet11.write(4, col_num, value, format2)
    worksheet11.write(7, col_num, value, format2)
    worksheet11.write(10, col_num, value, format2)

worksheet11.merge_range('A15:C15', 'LS3'+today+'当日交易', format4)

for col_num, value in enumerate(SH300ls3[1].columns.values):
    worksheet11.write(15, col_num, value, format2)
    worksheet11.write(18, col_num, value, format2)
    worksheet11.write(21, col_num, value, format2)
    worksheet11.write(24, col_num, value, format2)

worksheet13.set_column("A:H", 11, format3)

for col_num, value in enumerate(SH300ls3[2].columns.values):
    worksheet13.write(1, col_num, value, format2)
for col_num, value in enumerate(SH300ls3[5].columns.values):
    worksheet13.write(9, col_num, value, format2)
for col_num, value in enumerate(SH300ls3[3].columns.values):
    worksheet13.write(16, col_num, value, format2)
worksheet13.merge_range('A1:B1', 'LS3'+today+'Greeks', format4)
worksheet13.merge_range('A9:B9', 'LS3'+today+'Greeks-日内', format4)


worksheet14 = worksheets['SH300LS4持仓_当日交易']
worksheet16 = worksheets['SH300LS4Greeks']

worksheet14.set_column("A:A", 15, format1)
worksheet14.set_column("B:V", 5, format1)
worksheet14.merge_range('A1:C1', 'LS4'+today+'持仓', format4)

for col_num, value in enumerate(SH300ls4[0].columns.values):
    worksheet14.write(1, col_num, value, format2)
    worksheet14.write(4, col_num, value, format2)
    worksheet14.write(7, col_num, value, format2)
    worksheet14.write(10, col_num, value, format2)

worksheet14.merge_range('A15:C15', 'LS4'+today+'当日交易', format4)

for col_num, value in enumerate(SH300ls4[1].columns.values):
    worksheet14.write(15, col_num, value, format2)
    worksheet14.write(18, col_num, value, format2)
    worksheet14.write(21, col_num, value, format2)
    worksheet14.write(24, col_num, value, format2)

worksheet16.set_column("A:H", 11, format3)

for col_num, value in enumerate(SH300ls4[2].columns.values):
    worksheet16.write(1, col_num, value, format2)
for col_num, value in enumerate(SH300ls4[5].columns.values):
    worksheet16.write(9, col_num, value, format2)
for col_num, value in enumerate(SH300ls4[3].columns.values):
    worksheet16.write(16, col_num, value, format2)

worksheet16.merge_range('A1:B1', 'LS4'+today+'Greeks', format4)
worksheet16.merge_range('A9:B9', 'LS4'+today+'Greeks-日内', format4)
#
#
#worksheet17 = worksheets['SH300LS持仓_当日交易']
#worksheet19 = worksheets['SH300LSGreeks']
#
#worksheet17.set_column("A:A", 15, format1)
#worksheet17.set_column("B:V", 5, format1)
#worksheet17.merge_range('A1:C1', 'LS'+today+'持仓', format4)
#
#for col_num, value in enumerate(SH300ls[0].columns.values):
#    worksheet17.write(1, col_num, value, format2)
#    worksheet17.write(4, col_num, value, format2)
#    worksheet17.write(7, col_num, value, format2)
#    worksheet17.write(10, col_num, value, format2)
#
#
#worksheet17.merge_range('A15:C15', 'LS'+today+'当日交易', format4)
#for col_num, value in enumerate(SH300ls[1].columns.values):
#    worksheet17.write(15, col_num, value, format2)
#    worksheet17.write(18, col_num, value, format2)
#    worksheet17.write(21, col_num, value, format2)
#    worksheet17.write(24, col_num, value, format2)
#
#
#worksheet19.set_column("A:H", 11, format3)
#for col_num, value in enumerate(SH300ls[2].columns.values):
#    worksheet19.write(1, col_num, value, format2)
#for col_num, value in enumerate(SH300ls[5].columns.values):
#    worksheet19.write(9, col_num, value, format2)
#for col_num, value in enumerate(SH300ls[3].columns.values):
#    worksheet19.write(16, col_num, value, format2)
#worksheet19.merge_range('A1:B1', 'LS'+today+'Greeks', format4)
#worksheet19.merge_range('A9:B9', 'LS'+today+'Greeks-日内', format4)
#

#---------------------------------------------------------------------
#调整第三个标的的格式
'''
worksheet21.set_column("A:A", 15, format1)
worksheet21.set_column("B:V", 5, format1)
worksheet21.merge_range('A1:C1', 'LS3'+today+'持仓', format4)

for col_num, value in enumerate(SZ300ls3[0].columns.values):
    worksheet21.write(1, col_num, value, format2)
    worksheet21.write(4, col_num, value, format2)
    worksheet21.write(7, col_num, value, format2)
    worksheet21.write(10, col_num, value, format2)

worksheet21.merge_range('A15:C15', 'LS3'+today+'当日交易', format4)

for col_num, value in enumerate(SZ300ls3[1].columns.values):
    worksheet21.write(15, col_num, value, format2)
    worksheet21.write(18, col_num, value, format2)
    worksheet21.write(21, col_num, value, format2)
    worksheet21.write(24, col_num, value, format2)

worksheet23.set_column("A:H", 11, format3)

for col_num, value in enumerate(SZ300ls3[2].columns.values):
    worksheet23.write(1, col_num, value, format2)
for col_num, value in enumerate(SZ300ls3[5].columns.values):
    worksheet23.write(9, col_num, value, format2)
for col_num, value in enumerate(SZ300ls3[3].columns.values):
    worksheet23.write(16, col_num, value, format2)
worksheet23.merge_range('A1:B1', 'LS3'+today+'Greeks', format4)
worksheet23.merge_range('A9:B9', 'LS3'+today+'Greeks-日内', format4)
'''
'''
worksheet24 = worksheets['SZ300LS4持仓_当日交易']
worksheet26 = worksheets['SZ300LS4Greeks']

worksheet24.set_column("A:A", 15, format1)
worksheet24.set_column("B:V", 5, format1)
worksheet24.merge_range('A1:C1', 'LS4'+today+'持仓', format4)

for col_num, value in enumerate(SZ300ls4[0].columns.values):
    worksheet24.write(1, col_num, value, format2)
    worksheet24.write(4, col_num, value, format2)
    worksheet24.write(7, col_num, value, format2)
    worksheet24.write(10, col_num, value, format2)

worksheet24.merge_range('A15:C15', 'LS4'+today+'当日交易', format4)

for col_num, value in enumerate(SZ300ls4[1].columns.values):
    worksheet24.write(15, col_num, value, format2)
    worksheet24.write(18, col_num, value, format2)
    worksheet24.write(21, col_num, value, format2)
    worksheet24.write(24, col_num, value, format2)

worksheet26.set_column("A:H", 11, format3)

for col_num, value in enumerate(SZ300ls4[2].columns.values):
    worksheet26.write(1, col_num, value, format2)
for col_num, value in enumerate(SZ300ls4[5].columns.values):
    worksheet26.write(9, col_num, value, format2)
for col_num, value in enumerate(SZ300ls4[3].columns.values):
    worksheet26.write(16, col_num, value, format2)

worksheet26.merge_range('A1:B1', 'LS4'+today+'Greeks', format4)
worksheet26.merge_range('A9:B9', 'LS4'+today+'Greeks-日内', format4)


#worksheet27 = worksheets['SZ300LS持仓_当日交易']
#worksheet29 = worksheets['SZ300LSGreeks']
#
#worksheet27.set_column("A:A", 15, format1)
#worksheet27.set_column("B:V", 5, format1)
#worksheet27.merge_range('A1:C1', 'LS'+today+'持仓', format4)
#
#for col_num, value in enumerate(SZ300ls[0].columns.values):
#    worksheet27.write(1, col_num, value, format2)
#    worksheet27.write(4, col_num, value, format2)
#    worksheet27.write(7, col_num, value, format2)
#    worksheet27.write(10, col_num, value, format2)
#
#
#worksheet27.merge_range('A15:C15', 'LS'+today+'当日交易', format4)
#for col_num, value in enumerate(SZ300ls[1].columns.values):
#    worksheet27.write(15, col_num, value, format2)
#    worksheet27.write(18, col_num, value, format2)
#    worksheet27.write(21, col_num, value, format2)
#    worksheet27.write(24, col_num, value, format2)
#
#
#worksheet29.set_column("A:H", 11, format3)
#for col_num, value in enumerate(SZ300ls[2].columns.values):
#    worksheet29.write(1, col_num, value, format2)
#for col_num, value in enumerate(SZ300ls[5].columns.values):
#    worksheet29.write(9, col_num, value, format2)
#for col_num, value in enumerate(SZ300ls[3].columns.values):
#    worksheet29.write(16, col_num, value, format2)
#worksheet29.merge_range('A1:B1', 'LS'+today+'Greeks', format4)
#worksheet29.merge_range('A9:B9', 'LS'+today+'Greeks-日内', format4)
'''
#format10 = workbook1.add_format({'align': 'center', 'valign': 'top',  'bg_color':'#ffd8b1'})
#j=0
#for ud in underlying:  
#    locals()['worksheet' + str(int(1+j*10))].write(0, 3, ud,format10)
#    locals()['worksheet' + str(int(3+j*10))].write(0, 3, ud,format10)
#    locals()['worksheet' + str(int(4+j*10))].write(0, 3, ud,format10)
#    locals()['worksheet' + str(int(6+j*10))].write(0, 3, ud,format10)
#    locals()['worksheet' + str(int(7+j*10))].write(0, 3, ud,format10)
#    locals()['worksheet' + str(int(9+j*10))].write(0, 3, ud,format10)
#
#    j+=1


worksheet10.set_row(15,15, format5)
writer.save()
writer.close()

