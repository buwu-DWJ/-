#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   hedger.py
@Time    :   2023/02/09 09:36:21
@Author  :   DingWenjie
@Contact :   359582058@qq.com
@Desc    :   自动对冲测试
             模拟实际下单情景,每隔2分钟会分别买入虚值2档的call和put各200与100手;
             不在下单时间是实时判断是否对冲, 简单起见考虑用atm合约调整delta与vega
             至给定目标希腊值的一定范围内
'''


import logging
import numpy as np
from icetcore import TCoreAPI, QuoteEvent, TradeEvent, OrderStruct
import warnings
import threading
import asyncio
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('log.log', 'a')
formatter = logging.Formatter(
    '%(asctime)s|%(levelname)-8s|%(processName)s|%(threadName)s|%(lineno)d|%(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
warnings.simplefilter('ignore')
lock = threading.Lock()
first_time = True
current_time = time.perf_counter()
last_order_start_time = None


class APIEvent(TradeEvent, QuoteEvent):
    def __init__(self):
        super().__init__()

    def onconnected(self, apitype: str):
        pass

    def ondisconnected(self, apitype: str):
        pass

    def onbar(self, datatype, interval, symbol, data, isreal):
        pass

    def onATM(self, datatype, symbol, data):
        global atmdata
        atmdata = data

    def onpositionmoniter(self, data):
        global position
        for i in data:
            if i['Symbol'] == 'TC.S.SSE.510050' and i['SubKey'] == 'Total':
                position = i
                break


class HEDGER():
    def __init__(self, account: str, brokerid: str, order_setting: dict, hedge_setting: dict):
        self.account = account
        self.brokerid = brokerid
        self.order_setting = order_setting
        self.hedge_setting = hedge_setting

    async def _send_order_subthread(self, order):
        '''同时下单协程
        '''
        side = int((1.5-np.sign(order['qty'])/2))
        qty_left = np.abs(order['qty'])
        if 'P' in order['symbol']:
            atm_symbol = atmdata['OTM-1P']
            symbol = atmdata['OPTLIST'][atmdata['OPTLIST'].index(atm_symbol.replace(
                '.P.', '.C.'))+(int((order['symbol'].split('TM')[1][:2]))+1)].replace('.C.', '.P.')
        else:
            atm_symbol = atmdata['OTM-1C']
            symbol = atmdata['OPTLIST'][atmdata['OPTLIST'].index(
                atm_symbol)-(int((order['symbol'].split('TM')[1][:2]))+1)]
        logging.info(f'当前考虑{symbol},剩余单量为:{qty_left}')
        while qty_left:
            temp_qty = min(MAX_QTY_PER_ORDER, qty_left)
            qty_left -= temp_qty
            order_obj = OrderStruct(Account=order['account'],
                                    BrokerID=order['brokerid'],
                                    Symbol=symbol,
                                    Side=side,
                                    OrderQty=temp_qty,
                                    OrderType=11,
                                    TimeInForce=1,
                                    PositionEffect=4,
                                    SelfTradePrevention=3,
                                    Synthetic=1,
                                    ChasePrice='1T|1|1|M')
            api.neworder(order_obj)
            time.sleep(1)
            logger.info(f'下单完成, 当前剩余{qty_left}')
            await asyncio.sleep(MAX_QTY_PER_MINUTE/MAX_QTY_PER_ORDER)

    def _send_order(self):
        '''每隔给定间隔下单
        '''
        global first_time
        global current_time
        global last_order_start_time
        while True:
            current_time = time.perf_counter()
            if last_order_start_time:
                do_send = (
                    current_time-last_order_start_time) > self.order_setting['interval']
            else:
                last_order_start_time = time.perf_counter()
                continue
            if do_send or first_time:
                with lock:
                    last_order_start_time = time.perf_counter()
                    first_time = False
                    crt_time = time.strftime('%H:%M:%S', time.localtime())
                    logger.debug(f'{crt_time}当前开始下单操作')
                    order0 = {
                        'account': self.account,
                        'brokerid': self.brokerid,
                        'symbol': self.order_setting['call_id'],
                        'qty': self.order_setting['call_qty']
                    }
                    order1 = {
                        'account': self.account,
                        'brokerid': self.brokerid,
                        'symbol': self.order_setting['put_id'],
                        'qty': self.order_setting['put_qty']
                    }
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    tasks = [self._send_order_subthread(
                        order0), self._send_order_subthread(order1)]
                    loop.run_until_complete(asyncio.wait(tasks))
                    logger.warning('该次下单协程已结束')
                    loop.close()

    def _hedger(self):
        '''对冲
        '''
        global cash
        atmput_symbol = atmdata['OTM-1P']
        atmcall_symbol = atmdata['OTM-1C']
        order_obj = OrderStruct(Account=self.account,
                                BrokerID=self.brokerid,
                                OrderQty=MAX_QTY_FOR_HEDGING,
                                OrderType=1,
                                Symbol='',
                                Side=1,
                                TimeInForce=2,
                                PositionEffect=4,
                                SelfTradePrevention=3,
                                )
        while True:
            do_hedging = np.abs(position['$Delta']-self.hedge_setting['target_delta']*cash) > cash*self.hedge_setting['check_range_delta'] or np.abs(
                position['$Vega']-self.hedge_setting['target_vega']*cash) > cash*self.hedge_setting['check_range_vega']
            if do_hedging:
                with lock:
                    if position['$Vega'] > cash*self.hedge_setting['target_vega']:
                        order_obj.Side = 2
                        if position['$Delta'] > cash*self.hedge_setting['target_delta']:
                            order_obj.Symbol = atmcall_symbol
                        else:
                            order_obj.Symbol = atmput_symbol
                    else:
                        order_obj.Side = 1
                        if position['$Delta'] > cash*self.hedge_setting['target_delta']:
                            order_obj.Symbol = atmput_symbol
                        else:
                            order_obj.Symbol = atmcall_symbol
                    api.neworder(order_obj)
                    time.sleep(0.1)

    def test(self, timeout: float):
        '''进行测试
        '''
        thread_send = threading.Thread(target=self._send_order, daemon=True)
        thread_hedge = threading.Thread(target=self._hedger, daemon=True)
        thread_send.start()
        thread_hedge.start()
        thread_send.join(timeout=timeout)
        thread_hedge.join(timeout=timeout)


if __name__ == '__main__':
    api = TCoreAPI(APIEvent)
    re = api.connect()
    cash = 10000000
    MAX_QTY_PER_ORDER = 100
    MAX_QTY_PER_MINUTE = 200
    MAX_QTY_FOR_HEDGING = 6
    # account = 'mvtuat09'
    # brokerid = 'DCore_SIM_SS2'
    account = 'y000-mvtuat09'
    brokerid = 'M2_PAPERTRADE'
    atmsymbol_proxy = 'TC.O.SSE.510050.202302.GET.ATM'
    api.subATM(atmsymbol_proxy)
    time.sleep(3)
    order_setting = {
        'interval': 120,
        'call_id': 'OTM-3C',  # 以-1C为平值起始点, -3C即为虚值2档
        'call_qty': 200,
        'put_id': 'OTM-3P',
        'put_qty': 100,
    }
    hedge_setting = {
        'target_delta': 0,  # 均为小数值
        'check_range_delta': 0.05,
        'target_vega': 0,
        'check_range_vega': 0.0001,
    }
    my_hedger = HEDGER(account, brokerid, order_setting, hedge_setting)
    my_hedger.test(600)
