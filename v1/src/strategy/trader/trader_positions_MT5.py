from datetime import datetime
import MetaTrader5 as mt5
from utils.utils import tstamp_local_get
from strategy.strategy_utils import Signal_Type


class Position_Manager_MT5():
    connected = False
    path = ""
    symbol = ""
    magic_number = 0
    lot_size = 0.0
    SL_points = 0.0
    TP_points = 0.0
    deviation_points = 0.0
    pos_count = 0
    
    def __init__(self, dict_config_arg: dict) -> None:
        self.params_update(dict_config_arg)

    def params_update(self, dict_config_arg: dict):
        self.path = dict_config_arg["price_feed"]["MT5"]["path"]
        self.symbol = dict_config_arg["asset"]["symbol"]
        self.magic_number = dict_config_arg["strategy"]["positions"]["magic_number"]
        self.lot_size = dict_config_arg["strategy"]["positions"]["lot_size"]
        self.SL_points = dict_config_arg["strategy"]["positions"]["SL_points"]
        self.TP_points = dict_config_arg["strategy"]["positions"]["TP_points"]
        self.deviation_points = dict_config_arg["strategy"]["positions"]["deviation_points"]
        self.pos_count = 0

    def connect(self):
        list_msg_terminal = []
        try:
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Connecting to the order feed (MT5) ...")
            self.connected = mt5.initialize(self.path)
        except Exception as e:
            list_msg_terminal.append(f"[{tstamp_local_get()}][ERROR] Error while trying to connect to the order feed (MT5)! {e}.")
        finally:
            if(self.connected == True):
                list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Connected to the order feed (MT5).")
        return(self.connected, list_msg_terminal)

    def disconnect(self):
        list_msg_terminal = []
        try:
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Disconnecting from the price feed (MT5) ...")
            mt5.shutdown()
        except Exception as e:
            list_msg_terminal.append(f"[{tstamp_local_get()}][ERROR] Error while trying to disconnect from the price feed (MT5)! Error = {e}.")
        finally:
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Disconnected from the price feed (MT5).")
            if(mt5.version() is None):
                self.connected = False
        return(self.connected, list_msg_terminal)

    def pos_open(self, signal_type_arg, tstamp_entry_arg):
        str_terminal = None
        SLTP_mult = 0.0
        order_type = None
        order_price = 0.0
        order_comment = ""
        info = mt5.symbol_info(self.symbol)
        if(info is not None):
            self.pos_count += 1
            if(signal_type_arg == Signal_Type.SIGNAL_BUY):
                order_type = mt5.ORDER_TYPE_BUY
                order_price = info.ask
                order_comment = f"{datetime.strftime(tstamp_entry_arg, "%H:%M:%S.%f")[:-3]}"
                SLTP_mult = 1
            elif(signal_type_arg == Signal_Type.SIGNAL_SELL):
                order_type = mt5.ORDER_TYPE_SELL
                order_price = info.bid
                order_comment = f"{datetime.strftime(tstamp_entry_arg, "%H:%M:%S.%f")[:-3]}"
                SLTP_mult = -1
            SL_price = 0.0
            TP_price = 0.0
            if(self.SL_points > 0.0):
                SL_price = (order_price - (SLTP_mult * self.SL_points * info.trade_tick_size))
            if(self.TP_points > 0.0):
                TP_price = (order_price + (SLTP_mult * self.TP_points * info.trade_tick_size))
            request = None
            if(self.SL_points > 0.0 and self.TP_points > 0.0):
                request = {
                    "action":       mt5.TRADE_ACTION_DEAL,
                    "symbol":       self.symbol,
                    "volume":       self.lot_size,
                    "type":         order_type,
                    "price":        order_price,
                    "sl":           SL_price,
                    "tp":           TP_price,
                    "deviation":    int(self.deviation_points),
                    "magic":        self.magic_number,
                    "comment":      order_comment,
                    "type_time":    mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(request)
                str_terminal = f"[{tstamp_local_get()}][INFO] {self.signal_type_str_return(signal_type_arg)} position requested at {datetime.strftime(tstamp_entry_arg, "%H:%M:%S.%f")[:-3]}!"
        return(str_terminal)

    def pos_close_by_ticket(self, order_type_arg, price_arg, ticket_arg):
        order = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       self.symbol,
            "volume":       self.lot_size,
            "type":         order_type_arg,
            "price":        price_arg,
            "deviation":    int(self.deviation_points),
            "position":     ticket_arg,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        ret = mt5.order_send(order)
        return(ret)

    def pos_close_by_type(self, pos_type_arg: Signal_Type):
        list_str_terminal = []
        list_tickets = []
        positions_count = mt5.positions_get(symbol = self.symbol)
        if(positions_count is not None):
            for position in positions_count:
                if(position.magic == self.magic_number):
                    if((position.type == mt5.ORDER_TYPE_BUY and pos_type_arg == Signal_Type.SIGNAL_BUY) or (position.type == mt5.ORDER_TYPE_SELL and pos_type_arg == Signal_Type.SIGNAL_SELL)):
                        list_tickets.append(position.ticket)
        len_list_tickets = len(list_tickets)
        if(len_list_tickets > 0):
            info = mt5.symbol_info_tick(self.symbol)
            price = 0.0
            order_type = None
            if(pos_type_arg == Signal_Type.SIGNAL_BUY): 
                price = info.bid
                order_type = mt5.ORDER_TYPE_SELL
            elif(pos_type_arg == Signal_Type.SIGNAL_SELL): 
                price = info.ask
                order_type = mt5.ORDER_TYPE_BUY
            for ticket in list_tickets:
                pos_close_ret = self.pos_close_by_ticket(order_type, price, ticket)
                str_terminal = f"[{tstamp_local_get()}][INFO] Closing request for position with ticket = {ticket} was successfully sent!"
                list_str_terminal.append(str_terminal)
        return(list_str_terminal)

    def pos_break_even(self, pos_type_arg: Signal_Type, pos_ticket_arg, pos_EP_arg, SL_level_points_arg, tick_size_arg, pos_TP_arg):
        str_terminal = None
        SL_price = 0.0
        if(pos_type_arg == Signal_Type.SIGNAL_BUY):
            SL_price = pos_EP_arg + (SL_level_points_arg * tick_size_arg)
        if(pos_type_arg == Signal_Type.SIGNAL_SELL):
            SL_price = pos_EP_arg - (SL_level_points_arg * tick_size_arg)
        if(SL_price > 0.0):
            request = {
                "action":       mt5.TRADE_ACTION_SLTP,
                "symbol":       self.symbol,
                "sl":           SL_price,
                "tp":           pos_TP_arg,
                "position":     int(pos_ticket_arg),
            }
            result = mt5.order_send(request)
            str_terminal = f"[{tstamp_local_get()}][INFO] Break even on position #{pos_ticket_arg} was requested."
        return(str_terminal)

    def pos_break_even_CbC_process(self, pos_type_arg: Signal_Type, SL_target_points_arg, SL_level_points_arg):
        list_str_terminal = []
        str_terminal = ""
        price_curr = 0.0
        pos_target_price = 0.0
        positions_total = mt5.positions_get(symbol = self.symbol)
        symbol_info = mt5.symbol_info(self.symbol)
        tick_info = mt5.symbol_info_tick(self.symbol)
        tick_size = symbol_info.trade_tick_size
        if(positions_total is not None):
            for position in positions_total:
                if(position.magic == self.magic_number):
                    if(position.type == mt5.POSITION_TYPE_BUY and pos_type_arg == Signal_Type.SIGNAL_BUY):
                        price_curr = tick_info.ask
                        pos_target_price = position.price_open + (SL_target_points_arg * tick_size)
                        if(price_curr > 0.0 and pos_target_price > 0.0 and price_curr >= pos_target_price and position.sl < position.price_open):
                            str_terminal = self.pos_break_even(pos_type_arg, position.ticket, position.price_open, SL_level_points_arg, tick_size, position.tp)
                            if(str_terminal is not None):
                                list_str_terminal.append(str_terminal)
                    elif(position.type == mt5.POSITION_TYPE_SELL and pos_type_arg == Signal_Type.SIGNAL_SELL):
                        price_curr = tick_info.bid
                        pos_target_price = position.price_open - (SL_target_points_arg * tick_size)
                        if(price_curr > 0.0 and pos_target_price > 0.0 and price_curr <= pos_target_price and position.sl > position.price_open):
                            str_terminal = self.pos_break_even(pos_type_arg, position.ticket, position.price_open, SL_level_points_arg, tick_size, position.tp)
                            if(str_terminal is not None):
                                list_str_terminal.append(str_terminal)
        return(list_str_terminal)

    def pos_count_buy_return(self):
        positions_total = mt5.positions_get(symbol = self.symbol)
        positions_count = 0
        if(positions_total is not None):
            for position in positions_total:
                if(position.magic == self.magic_number and position.type == mt5.POSITION_TYPE_BUY):
                    positions_count += 1
        return(positions_count)
    
    def pos_count_sell_return(self):
        positions_total = mt5.positions_get(symbol = self.symbol)
        positions_count = 0
        if(positions_total is not None):
            for position in positions_total:
                if(position.magic == self.magic_number and position.type == mt5.POSITION_TYPE_SELL):
                    positions_count += 1
        return(positions_count)

    def signal_type_str_return(self, pos_type_arg: Signal_Type):
        str_ret = ""
        if(pos_type_arg == Signal_Type.SIGNAL_BUY):
            str_ret = "BUY"
        elif(pos_type_arg == Signal_Type.SIGNAL_SELL):
            str_ret = "SELL"
        return(str_ret)
