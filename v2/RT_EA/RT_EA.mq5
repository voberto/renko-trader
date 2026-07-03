//+------------------------------------------------------------------+
//|                                                        RT_EA.mq5 |
//+------------------------------------------------------------------+

#property copyright     "VPO"
#property version       "1.00"
#property description   "Renko Trader EA."
#property strict

// Modules
#include "EA_vars.mqh"
#include "Modules/Controller.mqh"

// Variables
cl_TX obj_TX;
cl_RX obj_RX;
cl_Controller obj_Controller;
cl_Positions obj_Positions;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   int i_retval = INIT_SUCCEEDED;

   obj_Positions.func_loop_OnInit(b_inp_trade_enabled, b_inp_trade_close_on_opp, b_inp_trade_async_enabled, l_inp_magic_number, d_inp_lot_size, d_inp_SL_points, d_inp_TP_points);
   obj_Controller.func_loop_OnInit(obj_Comm, str_inp_host, i_inp_port, false, "00:00", "23:59", i_inp_timer_period_ms);

   return(i_retval);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   obj_Controller.func_loop_OnDeinit();
   
   if(reason == REASON_REMOVE)
   {
   
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // TX loop
   obj_Controller.func_loop_OnTick(obj_TX, obj_Comm);
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   // RX loop
   obj_Controller.func_loop_OnTimer(obj_RX, obj_TX, obj_Comm, obj_Positions);
}

//+------------------------------------------------------------------+
//| OnTradeTransaction function                                      |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   // Get transaction type as enumeration value 
   ENUM_TRADE_TRANSACTION_TYPE ettt_type = trans.type;
   // If transaction is result of addition of the transaction in history
   if(ettt_type == TRADE_TRANSACTION_DEAL_ADD)
   {
      long              l_deal_entry         = 0;
      long              l_deal_ID            = 0;
      long              l_deal_magic         = 0;
      long              l_deal_time_msc      = 0;
      ulong             ul_deal_ticket       = 0;
      double            d_deal_volume        = 0;
      double            d_deal_profit        = 0;
      double            d_EP_in              = 0;
      double            d_SL_in              = 0;
      double            d_TP_in              = 0;
      string            str_deal_symbol      = "";
      datetime          dt_position_tstamp   = 0;
      ENUM_DEAL_TYPE    endt_deal_type       = 0;
      ENUM_DEAL_REASON  endr_deal_reason     = 0;
      
      if(HistoryDealSelect(trans.deal))
      {
         l_deal_entry         = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
         l_deal_ID            = HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
         l_deal_magic         = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
         ul_deal_ticket       = HistoryDealGetInteger(trans.deal, DEAL_TICKET);
         d_deal_volume        = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
         d_deal_profit        = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
         d_EP_in              = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
         d_SL_in              = HistoryDealGetDouble(trans.deal, DEAL_SL);
         d_TP_in              = HistoryDealGetDouble(trans.deal, DEAL_TP);
         str_deal_symbol      = HistoryDealGetString(trans.deal, DEAL_SYMBOL);
         dt_position_tstamp   = (datetime)HistoryDealGetInteger(trans.deal, DEAL_TIME);
         l_deal_time_msc      = HistoryDealGetInteger(trans.deal, DEAL_TIME_MSC);
         endt_deal_type       = (ENUM_DEAL_TYPE)HistoryDealGetInteger(trans.deal, DEAL_TYPE);
         endr_deal_reason     = (ENUM_DEAL_REASON)HistoryDealGetInteger(trans.deal, DEAL_REASON);
      }
      else
      {
         return;
      }
            
   }         
}
