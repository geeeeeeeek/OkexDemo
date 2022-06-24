import time

import numpy as np
import pandas as pd


class Turtle:

    def __init__(self, context):
        self.context = context

        # 做多参数
        self.buyprice = 0
        self.buy_count = 0

        # 做空参数
        self.sellprice = 0
        self.sell_count = 0

        self.ATR_T = 14
        self.T = 20
        self.VALUE = 1000
        self.InstId = "DOT-USDT-SWAP"
        self.BAR = "1H"

    def run(self):

        self.context.log("读取配置")
        value = self.context.okConfig.get_config_value(sector=self.InstId, item="buyprice")
        if value is not None:
            self.buyprice = float(value)

        value = self.context.okConfig.get_config_value(sector=self.InstId, item="buy_count")
        if value is not None:
            self.buy_count = float(value)

        value = self.context.okConfig.get_config_value(sector=self.InstId, item="sellprice")
        if value is not None:
            self.sellprice = float(value)

        value = self.context.okConfig.get_config_value(sector=self.InstId, item="sell_count")
        if value is not None:
            self.sell_count = float(value)

        self.context.log("读取配置成功: buyprice=%s,buy_count=%s,sellprice=%s,sell_count=%s" % (
        self.buyprice, self.buy_count, self.sellprice, self.sell_count))

        broker_value = self.VALUE  # 当前净值

        """"""""""""""""""""""""" 核心代码 """""""""""""""""""""""""

        self.context.log("获取k线")
        ksuccess = False
        for i in range(30):
            try:
                self.context.log("获取k线第%s次" % (i + 1))
                data = self.context.okApi.getHistoryData(self.InstId, bar=self.BAR)
                if len(data) > 0:
                    self.context.log("获取k线成功, 数量:" + str(len(data)))
                    ksuccess = True
                    break

            except Exception as e:
                self.context.log("error:" + str(e))
            time.sleep(1)

        self.context.log("获取价格")
        psuccess = False
        for i in range(30):
            try:
                self.context.log("获取价格第%s次" % (i + 1))
                price = self.context.okApi.getLastPrice(instId=self.InstId)
                self.context.log("获取价格成功, 价格:" + str(price))
                if float(price) > 0:
                    psuccess = True
                    break
            except Exception as e:
                self.context.log("error:" + str(e))
            time.sleep(1)

        if not ksuccess or not psuccess:
            self.context.log("数据获取失败, 请手动执行!")
            self.context.okApi.sendMessage("数据获取失败, 请手动执行!")
            return

        price = float(price)

        signal = self.in_or_out(data[:-1], price, self.T)
        atr = self.calc_atr(data, self.ATR_T)
        self.context.log("ATR:" + str(atr))

        # 平多
        if signal == -1 and self.buy_count > 0:
            self.context.log("平多信号")
            self.context.okApi.sendMessage("平多信号")
            self.sellAll()

        # 平空
        if signal == 1 and self.sell_count > 0:
            self.context.log("平空信号")
            self.buyAll()

        # 做多
        if signal == 1 and self.buy_count == 0:
            unit = self.calc_size(broker_value, price)
            self.context.log("做多:" + str(unit))
            self.context.okApi.sendMessage("做多:" + str(unit))
            flag = self.context.okApi.placeOrder(instId=self.InstId, side='buy', posSide='long', sz=unit)
            if flag:
                self.context.log("做多成功, 数量:" + str(unit))
                self.context.okApi.sendMessage("做多成功, 数量:" + str(unit))
            else:
                self.context.log("做多失败, 请手动执行, 数量:" + str(unit))
                self.context.okApi.sendMessage("做多失败, 请手动执行, 数量:" + str(unit))

            self.buyprice = price
            self.buy_count = 1
            self.context.okConfig.set_config_value(sector=self.InstId, item="buyprice", value=price)
            self.context.okConfig.set_config_value(sector=self.InstId, item="buy_count", value=self.buy_count)
        # 做多加仓
        elif price > self.buyprice + 0.5 * atr and self.buy_count > 0 and self.buy_count <= 3:
            unit = self.calc_size(broker_value, price)
            self.context.log("做多加仓:" + str(unit))
            self.context.okApi.sendMessage("做多加仓:" + str(unit))
            flag = self.context.okApi.placeOrder(instId=self.InstId, side='buy', posSide='long', sz=unit)
            if flag:
                self.context.log("做多加仓成功, 数量:" + str(unit))
                self.context.okApi.sendMessage("做多加仓成功, 数量:" + str(unit))
            else:
                self.context.log("做多加仓失败, 请手动执行, 数量:" + str(unit))
                self.context.okApi.sendMessage("做多加仓失败, 请手动执行, 数量:" + str(unit))

            self.buy_count += 1
            self.buyprice = price
            self.context.okConfig.set_config_value(sector=self.InstId, item="buyprice", value=price)
            self.context.okConfig.set_config_value(sector=self.InstId, item="buy_count", value=self.buy_count)

        # 做空
        elif signal == -1 and self.sell_count == 0:
            unit = self.calc_size(broker_value, price)
            self.context.log("做空:" + str(unit))
            self.context.okApi.sendMessage("做空:" + str(unit))
            flag = self.context.okApi.placeOrder(instId=self.InstId, side='sell', posSide='short', sz=unit)
            if flag:
                self.context.log("做空成功, 数量:" + str(unit))
                self.context.okApi.sendMessage("做空成功, 数量:" + str(unit))
            else:
                self.context.log("做空失败, 请手动执行, 数量:" + str(unit))
                self.context.okApi.sendMessage("做空失败, 请手动执行, 数量:" + str(unit))

            self.sell_count = 1
            self.sellprice = price
            self.context.okConfig.set_config_value(sector=self.InstId, item="sellprice", value=price)
            self.context.okConfig.set_config_value(sector=self.InstId, item="sell_count", value=self.sell_count)

        # 做空加仓
        elif price < self.sellprice - 0.5 * atr and self.sell_count > 0 and self.sell_count <= 3:
            unit = self.calc_size(broker_value, price)
            self.context.log("做空加仓:" + str(unit))
            self.context.okApi.sendMessage("做空加仓:" + str(unit))
            flag = self.context.okApi.placeOrder(instId=self.InstId, side='sell', posSide='short', sz=unit)
            if flag:
                self.context.log("做空加仓成功, 数量:" + str(unit))
                self.context.okApi.sendMessage("做空加仓成功, 数量:" + str(unit))
            else:
                self.context.log("做空加仓失败, 请手动执行, 数量:" + str(unit))
                self.context.okApi.sendMessage("做空加仓失败, 请手动执行, 数量:" + str(unit))

            self.sell_count += 1
            self.sellprice = price
            self.context.okConfig.set_config_value(sector=self.InstId, item="sellprice", value=price)
            self.context.okConfig.set_config_value(sector=self.InstId, item="sell_count", value=self.sell_count)

    def sellAll(self):
        if self.buy_count > 0:
            flag = self.context.okApi.closeAllPositions(instId=self.InstId)
            if flag:
                self.context.log("平多成功!")
                self.context.okApi.sendMessage("平多成功!")
            else:
                self.context.log("平多失败, 请手动操作!")
                self.context.okApi.sendMessage("平多失败, 请手动操作!")

            self.buy_count = 0
            self.buyprice = 0
            self.context.okConfig.set_config_value(sector=self.InstId, item="buyprice", value=0)
            self.context.okConfig.set_config_value(sector=self.InstId, item="buy_count", value=0)

    def buyAll(self):
        if self.sell_count > 0:
            flag = self.context.okApi.closeAllPositions(instId=self.InstId)
            if not flag:
                self.context.log("平空成功!")
                self.context.okApi.sendMessage("平空成功!")
            else:
                self.context.log("平空失败, 请手动操作!")
                self.context.okApi.sendMessage("平空失败, 请手动操作!")

            self.sell_count = 0
            self.sellprice = 0
            self.context.okConfig.set_config_value(sector=self.InstId, item="sellprice", value=0)
            self.context.okConfig.set_config_value(sector=self.InstId, item="sell_count", value=0)

    def in_or_out(self, data, price, T):
        up = float(np.max(data["high"].iloc[-int(T):]))
        down = float(np.min(data["low"].iloc[-int(T / 2):]))
        self.context.log("上轨:%s,下轨:%s,价格:%s" % (up, down, price))
        if price > up:
            return 1
        elif price < down:
            return -1
        else:
            return 0

    # ATR值计算
    def calc_atr(self, vdata, ATR_T):
        tr_list = []
        data = vdata[-ATR_T:] if len(vdata) > ATR_T else vdata
        for i in range(1, len(data)):
            tr = max(data["high"].iloc[i] - data["low"].iloc[i],
                     abs(data["high"].iloc[i] - data["close"].iloc[i - 1]),
                     abs(data["close"].iloc[i - 1] - data["low"].iloc[i]))
            tr_list.append(tr)
        atr = np.array(tr_list).mean()
        return atr

    def calc_size(self, value, price):
        return int(value * 0.1 / price)
