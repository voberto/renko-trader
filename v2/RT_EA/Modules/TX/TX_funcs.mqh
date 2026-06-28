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
      void func_TX_startup_history_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_ticks_arg);

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

// Send tick history for initial chart build
void cl_TX::func_TX_startup_history_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_ticks_arg)
{
   MqlTick mqlt_tick_arr[];
   
   // Apply security cap
   int i_effective_lookback = i_lookback_ticks_arg;
   if(i_effective_lookback > MAX_HISTORY_TICKS_SAFE_CAP)
   {
      printf("[TX][WARNING] Requested lookback %d exceeds safe cap %d. Truncating.", i_lookback_ticks_arg, MAX_HISTORY_TICKS_SAFE_CAP);
      i_effective_lookback = MAX_HISTORY_TICKS_SAFE_CAP;
   }

   // Copy historical ticks from the terminal using the effective (capped) lookback
   int i_copied = CopyTicks(Symbol(), mqlt_tick_arr, COPY_TICKS_ALL, 0, i_effective_lookback);

   if(i_copied <= 0)
   {
      printf("[TX][ERROR] CopyTicks failed. Error = %d, lookback requested = %d.", GetLastError(), i_effective_lookback);
      return;
   }

   if(i_copied < i_lookback_ticks_arg)
   {
      printf("[TX][WARNING] Requested %d ticks but only %d available. Sending available amount.", i_lookback_ticks_arg, i_copied);
   }

   // Build JSON payload
   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", TX_HISTORY);
   obj_JSON.func_str_add("symbol", Symbol());
   obj_JSON.func_raw_add("lookback_requested", IntegerToString(i_lookback_ticks_arg));
   obj_JSON.func_raw_add("lookback_sent", IntegerToString(i_copied));

   // Build tick array manually (cl_JSON has no native array builder)
   string str_tick_array = "[";
   for(int i = 0; i < i_copied; i++)
   {
      if(i > 0) str_tick_array += ",";

      str_tick_array += "{\"tstamp\":";
      str_tick_array += IntegerToString(mqlt_tick_arr[i].time);
      str_tick_array += ",\"ask\":";
      str_tick_array += DoubleToString(mqlt_tick_arr[i].ask, _Digits);
      str_tick_array += ",\"bid\":";
      str_tick_array += DoubleToString(mqlt_tick_arr[i].bid, _Digits);
      str_tick_array += "}";
   }
   str_tick_array += "]";

   obj_JSON.func_raw_add("ticks", str_tick_array);

   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected)
   {
      obj_Comm_arg.SendData(str_TX, true, TX_HISTORY);
      printf("[TX][INFO] HISTORY sent. lookback_requested=%d | lookback_sent=%d | payload=%d bytes.", i_lookback_ticks_arg, i_copied, StringLen(str_TX));
   }
   else printf("[TX][ERROR] EA is not connected to the server. Can't send HISTORY.");
}

void cl_TX::func_stub()
{

}
