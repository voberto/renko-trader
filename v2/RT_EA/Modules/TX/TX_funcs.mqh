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
      void func_TX_data_send(cl_Comm_Sockets &obj_Comm_arg);

      // Startup protocol transmissions
      void func_TX_startup_symbol_send(cl_Comm_Sockets &obj_Comm_arg);
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
void cl_TX::func_TX_data_send(cl_Comm_Sockets &obj_Comm_arg)
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
   if(b_connected) obj_Comm_arg.SendData(str_TX, true, TX_DATA);
   else if(!b_connected) printf("[TX][ERROR] EA is not connected to the server. Can't send data.");
}

// Announce symbol to app
void cl_TX::func_TX_startup_symbol_send(cl_Comm_Sockets &obj_Comm_arg)
{
   string str_symbol = Symbol();

   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", TX_SYMBOL);
   obj_JSON.func_str_add("symbol", str_symbol);
   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected)
   {
      obj_Comm_arg.SendData(str_TX, true, TX_SYMBOL);
      printf("[TX][INFO] SYMBOL sent. symbol=%s | payload=%d bytes.", str_symbol, StringLen(str_TX));
   }
   else printf("[TX][ERROR] EA is not connected to the server. Can't send SYMBOL.");
}

// Send candle history (bars) for initial chart build instead of ticks
void cl_TX::func_TX_startup_history_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_candles_arg)
{
   MqlRates rates_arr[];
   
   // Apply security cap for candles (usually smaller than tick cap, e.g., 1000/2000 bars is plenty)
   int i_effective_lookback = i_lookback_candles_arg;
   int i_max_candles_cap = 5000; // Safe cap for historical candles structure
   if(i_effective_lookback > i_max_candles_cap)
   {
      printf("[TX][WARNING] Requested candle lookback %d exceeds safe cap %d. Truncating.", i_lookback_candles_arg, i_max_candles_cap);
      i_effective_lookback = i_max_candles_cap;
   }

   // Copy historical rates (candles) from the terminal
   // PERIOD_CURRENT uses the timeframe active on the chart where the EA is running
   int i_copied = CopyRates(Symbol(), PERIOD_CURRENT, 0, i_effective_lookback, rates_arr);

   if(i_copied <= 0)
   {
      printf("[TX][ERROR] CopyRates failed. Error = %d, lookback requested = %d.", GetLastError(), i_effective_lookback);
      return;
   }

   if(i_copied < i_lookback_candles_arg)
   {
      printf("[TX][WARNING] Requested %d candles but only %d available. Sending available amount.", i_lookback_candles_arg, i_copied);
   }

   // Build JSON payload
   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", TX_HISTORY);
   obj_JSON.func_str_add("symbol", Symbol());
   obj_JSON.func_raw_add("lookback_requested", IntegerToString(i_lookback_candles_arg));
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

   // Send as "candles" key instead of "ticks"
   obj_JSON.func_raw_add("candles", str_candles_array);

   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected)
   {
      obj_Comm_arg.SendData(str_TX, true, TX_HISTORY);
      printf("[TX][INFO] HISTORY (candles) sent. lookback_requested=%d | lookback_sent=%d | payload=%d bytes.", i_lookback_candles_arg, i_copied, StringLen(str_TX));
   }
   else printf("[TX][ERROR] EA is not connected to the server. Can't send HISTORY.");
}

void cl_TX::func_stub()
{

}
