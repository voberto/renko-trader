//+------------------------------------------------------------------+
//|                                              Positions_funcs.mqh |
//+------------------------------------------------------------------+

#include "../../EA_vars.mqh"
#include <Trade/Trade.mqh>


class cl_Positions
{
   private:
      bool b_trade_enabled, b_trade_close_on_opp, b_trade_async_enabled;
      long l_magic_number;
      double d_lot_size, d_SL_points, d_TP_points, d_tick_size;
      CTrade obj_trade;

   public:
      cl_Positions();
      ~cl_Positions();
      void func_loop_OnInit(bool b_trade_enabled_arg, bool b_trade_close_on_opp_arg, bool b_trade_async_enabled_arg,
                            long l_magic_number_arg, double d_lot_size_arg, double d_SL_points_arg, double d_TP_points_arg);
      void func_loop_pos(string str_sig_type_arg);

   protected:
      void func_pos_close_by_type(ENUM_POSITION_TYPE ept_pos_type_arg);
};

cl_Positions::cl_Positions()
{

}

cl_Positions::~cl_Positions()
{
   
}

void cl_Positions::func_loop_OnInit(bool b_trade_enabled_arg, bool b_trade_close_on_opp_arg, bool b_trade_async_enabled_arg,
                                    long l_magic_number_arg, double d_lot_size_arg, double d_SL_points_arg, double d_TP_points_arg)
{
   b_trade_enabled = b_trade_enabled_arg;
   b_trade_close_on_opp = b_trade_close_on_opp_arg;
   b_trade_async_enabled = b_trade_async_enabled_arg;
   l_magic_number = l_magic_number_arg;
   d_lot_size = d_lot_size_arg;
   d_SL_points = d_SL_points_arg;
   d_TP_points = d_TP_points_arg;
   d_tick_size = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_SIZE);

   if(b_trade_enabled)
   {
      // Magic number
      obj_trade.SetExpertMagicNumber(l_magic_number);
      // Order filling type
      if(!obj_trade.SetTypeFillingBySymbol(Symbol())) obj_trade.SetTypeFilling(ORDER_FILLING_RETURN);
      // Async mode
      obj_trade.SetAsyncMode(b_trade_async_enabled);
   }
}

void cl_Positions::func_loop_pos(string str_sig_type_arg)
{
   double d_EP = 0.0, d_SL = 0.0, d_TP = 0.0;
   string str_comment = "";
   
   if(str_sig_type_arg == SIG_TYPE_LONG)
   {
      if(b_trade_close_on_opp)
      {
         func_pos_close_by_type(POSITION_TYPE_SELL);
      }
      
      d_EP = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
      d_SL = d_EP - ((int)d_SL_points * d_tick_size);
      d_TP = d_EP + ((int)d_TP_points * d_tick_size);
      str_comment = "LONG_" + IntegerToString(l_magic_number);

      printf("[DEBUG] New LONG position triggered. EP = %s, SL = %s, TP = %s, comment = %s.", DoubleToString(d_EP, _Digits), 
             DoubleToString(d_SL, _Digits), DoubleToString(d_TP, _Digits), str_comment);

      obj_trade.Buy(d_lot_size, Symbol(), d_EP, d_SL, d_TP, str_comment);
   }
   else if(str_sig_type_arg == SIG_TYPE_SHORT)
   {
      if(b_trade_close_on_opp)
      {
         func_pos_close_by_type(POSITION_TYPE_BUY);
      }
      
      d_EP = SymbolInfoDouble(Symbol(), SYMBOL_BID);
      d_SL = d_EP + ((int)d_SL_points * d_tick_size);
      d_TP = d_EP - ((int)d_TP_points * d_tick_size);
      str_comment = "SHORT_" + IntegerToString(l_magic_number);

      printf("[DEBUG] New SHORT position triggered. EP = %s, SL = %s, TP = %s, comment = %s.", DoubleToString(d_EP, _Digits), 
             DoubleToString(d_SL, _Digits), DoubleToString(d_TP, _Digits), str_comment);

      obj_trade.Sell(d_lot_size, Symbol(), d_EP, d_SL, d_TP, str_comment);
   }
}

void cl_Positions::func_pos_close_by_type(ENUM_POSITION_TYPE ept_pos_type_arg)
{
   int i_pos_total = PositionsTotal();

   ulong ul_pos_ticket_arr[];
   int i_pos_ticket_arr_size = ArraySize(ul_pos_ticket_arr);

   ulong ul_pos_ticket  = 0;
   long l_pos_magic     = 0;
   ENUM_POSITION_TYPE ept_pos_type;

   for(int i = i_pos_total - 1; i >= 0; i--)
   {
      ul_pos_ticket = PositionGetTicket(i);
      l_pos_magic = PositionGetInteger(POSITION_MAGIC);
      ept_pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      
      if(PositionSelectByTicket(ul_pos_ticket) && l_pos_magic == l_magic_number && ept_pos_type == ept_pos_type_arg)
      {
         i_pos_ticket_arr_size = ArraySize(ul_pos_ticket_arr);
         ArrayResize(ul_pos_ticket_arr, i_pos_ticket_arr_size + 1);
         i_pos_ticket_arr_size = ArraySize(ul_pos_ticket_arr);
         ul_pos_ticket_arr[i_pos_ticket_arr_size - 1] = ul_pos_ticket;
      }
   }

   i_pos_ticket_arr_size = ArraySize(ul_pos_ticket_arr);

   if(i_pos_ticket_arr_size > 0)
   {
      for(int i = 0; i < i_pos_ticket_arr_size; i++)
      {
         obj_trade.PositionClose(ul_pos_ticket_arr[i]);
      }
   }
}
