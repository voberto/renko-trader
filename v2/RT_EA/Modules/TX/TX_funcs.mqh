//+------------------------------------------------------------------+
//|                                                     TX_funcs.mqh |
//+------------------------------------------------------------------+

#include "../../EA_vars.mqh"

class cl_TX
{
   private:
      double d_price_ask, d_price_bid;
      datetime dt_tstamp;
      cl_JSON obj_JSON;

   public:
      // Constructor and destructor
      cl_TX(void);
      ~cl_TX(void);

      // Steady-state data transmission
      void func_TX_data_send(cl_Comm_Sockets &obj_Comm_arg, bool b_data_print_arg);

      // Startup protocol transmissions
      void func_TX_startup_start_send(cl_Comm_Sockets &obj_Comm_arg);
      void func_TX_startup_history_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_candles_arg);

   protected:
      void func_stub();
};


// Constructor
cl_TX::cl_TX(void)
{
   d_price_ask = 0.0;
   d_price_bid = 0.0;
   dt_tstamp = 0;
}

// Destructor
cl_TX::~cl_TX(void)
{

}

// Steady-state tick transmission (normal operation)
void cl_TX::func_TX_data_send(cl_Comm_Sockets &obj_Comm_arg, bool b_data_print_arg)
{
   // Collect market variables
   d_price_ask = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
   d_price_bid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
   dt_tstamp = TimeCurrent();

   // Prepare TX JSON
   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", TX_DATA);
   obj_JSON.func_raw_add("tstamp", IntegerToString(dt_tstamp));
   obj_JSON.func_double_add("ask", d_price_ask, _Digits);
   obj_JSON.func_double_add("bid", d_price_bid, _Digits);
   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   // Check connection and send data
   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected) obj_Comm_arg.SendData(str_TX, b_data_print_arg, TX_DATA);
   else if(!b_connected) printf("[TX][ERROR] EA is not connected to the server. Can't send data.");
}

// Announce start params to app
void cl_TX::func_TX_startup_start_send(cl_Comm_Sockets &obj_Comm_arg)
{
   double d_tick_size = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_SIZE);
   // Note: TX_START, ENUM_CHART_TYPE, etc., must be defined in your constants/vars
   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", "TX_START"); // Generic type for startup configuration
   obj_JSON.func_str_add("symbol", Symbol());
   obj_JSON.func_raw_add("timeframe_sec", IntegerToString(PeriodSeconds()));
   obj_JSON.func_raw_add("candles_type", IntegerToString(en_inp_ct_curr));
   obj_JSON.func_raw_add("brick_size", IntegerToString(i_inp_renko_brick_size));
   obj_JSON.func_raw_add("tick_size", DoubleToString(d_tick_size, _Digits));
   
   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected)
   {
      // Using a generic tag for transmission or updating your TX_SYMBOL constant to TX_START
      obj_Comm_arg.SendData(str_TX, true, "TX_START"); 
      printf("[TX][INFO] START config sent. Symbol = %s | type = %d | payload = %d bytes.", Symbol(), IntegerToString(en_inp_ct_curr), StringLen(str_TX));
   }
   else printf("[TX][ERROR] EA is not connected to the server. Can't send START config.");
}

// Send history for initial chart build — candles (regular) or ticks (renko)
void cl_TX::func_TX_startup_history_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_arg)
{
   // --- Mode: RENKO (send raw ticks) ---
   if(en_inp_ct_curr == en_cd_renko)
   {
      MqlTick tick_arr[];

      // Apply security cap for ticks
      int i_effective_lookback = i_lookback_arg;
      if(i_effective_lookback > MAX_HISTORY_TICKS_SAFE_CAP)
      {
         printf("[TX][WARNING] Requested tick lookback %d exceeds safe cap %d. Truncating.", i_lookback_arg, MAX_HISTORY_TICKS_SAFE_CAP);
         i_effective_lookback = MAX_HISTORY_TICKS_SAFE_CAP;
      }

      int i_copied = CopyTicks(Symbol(), tick_arr, COPY_TICKS_ALL, 0, i_effective_lookback);

      if(i_copied <= 0)
      {
         printf("[TX][ERROR] CopyTicks failed. Error = %d, lookback requested = %d.", GetLastError(), i_effective_lookback);
         return;
      }

      if(i_copied < i_lookback_arg)
      {
         printf("[TX][WARNING] Requested %d ticks but only %d available. Sending available amount.", i_lookback_arg, i_copied);
      }

      // Build JSON payload
      obj_JSON.func_reset();
      obj_JSON.func_str_add("type", TX_HISTORY);
      obj_JSON.func_str_add("symbol", Symbol());
      obj_JSON.func_raw_add("lookback_requested", IntegerToString(i_lookback_arg));
      obj_JSON.func_raw_add("lookback_sent", IntegerToString(i_copied));

      // Build ticks array manually (cl_JSON has no native array builder)
      string str_ticks_array = "[";
      for(int i = 0; i < i_copied; i++)
      {
         if(i > 0) str_ticks_array += ",";

         str_ticks_array += "{\"time\":";
         str_ticks_array += IntegerToString(tick_arr[i].time);
         str_ticks_array += ",\"price\":";
         str_ticks_array += DoubleToString(tick_arr[i].bid, _Digits);
         str_ticks_array += "}";
      }
      str_ticks_array += "]";

      obj_JSON.func_raw_add("ticks", str_ticks_array);

      string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

      bool b_connected = obj_Comm_arg.IsConnected();
      if(b_connected)
      {
         obj_Comm_arg.SendData(str_TX, true, TX_HISTORY);
         printf("[TX][INFO] HISTORY (ticks) sent. Lookback_requested = %d | lookback_sent = %d | payload = %d bytes.", i_lookback_arg, i_copied, StringLen(str_TX));
      }
      else printf("[TX][ERROR] EA is not connected to the server. Can't send HISTORY.");
   }
   // --- Mode: REGULAR (send candles) ---
   else
   {
      MqlRates rates_arr[];

      // Apply security cap for candles
      int i_effective_lookback = i_lookback_arg;
      int i_max_candles_cap = 5000;
      if(i_effective_lookback > i_max_candles_cap)
      {
         printf("[TX][WARNING] Requested candle lookback %d exceeds safe cap %d. Truncating.", i_lookback_arg, i_max_candles_cap);
         i_effective_lookback = i_max_candles_cap;
      }

      int i_copied = CopyRates(Symbol(), PERIOD_CURRENT, 0, i_effective_lookback, rates_arr);

      if(i_copied <= 0)
      {
         printf("[TX][ERROR] CopyRates failed. Error = %d, lookback requested = %d.", GetLastError(), i_effective_lookback);
         return;
      }

      if(i_copied < i_lookback_arg)
      {
         printf("[TX][WARNING] Requested %d candles but only %d available. Sending available amount.", i_lookback_arg, i_copied);
      }

      // Build JSON payload
      obj_JSON.func_reset();
      obj_JSON.func_str_add("type", TX_HISTORY);
      obj_JSON.func_str_add("symbol", Symbol());
      obj_JSON.func_raw_add("lookback_requested", IntegerToString(i_lookback_arg));
      obj_JSON.func_raw_add("lookback_sent", IntegerToString(i_copied));

      // Build candles array manually (cl_JSON has no native array builder)
      string str_candles_array = "[";
      for(int i = 0; i < i_copied; i++)
      {
         if(i > 0) str_candles_array += ",";

         str_candles_array += "{\"time\":";
         str_candles_array += IntegerToString(rates_arr[i].time);
         str_candles_array += ",\"open\":";
         str_candles_array += DoubleToString(rates_arr[i].open, _Digits);
         str_candles_array += ",\"high\":";
         str_candles_array += DoubleToString(rates_arr[i].high, _Digits);
         str_candles_array += ",\"low\":";
         str_candles_array += DoubleToString(rates_arr[i].low, _Digits);
         str_candles_array += ",\"close\":";
         str_candles_array += DoubleToString(rates_arr[i].close, _Digits);
         str_candles_array += "}";
      }
      str_candles_array += "]";

      obj_JSON.func_raw_add("candles", str_candles_array);

      string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

      bool b_connected = obj_Comm_arg.IsConnected();
      if(b_connected)
      {
         obj_Comm_arg.SendData(str_TX, true, TX_HISTORY);
         printf("[TX][INFO] HISTORY (candles) sent. Lookback_requested = %d | lookback_sent = %d | payload = %d bytes.", i_lookback_arg, i_copied, StringLen(str_TX));
      }
      else printf("[TX][ERROR] EA is not connected to the server. Can't send HISTORY.");
   }
}

void cl_TX::func_stub()
{

}
