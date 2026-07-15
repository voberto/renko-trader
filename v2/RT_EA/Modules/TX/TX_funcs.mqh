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
      // History buffer — populated once at META send, sliced per chunk
      MqlTick  arr_tick_history[];
      MqlRates arr_rates_history[];
      int i_history_total;   // Actual items available after CopyTicks/CopyRates

   public:
      // Constructor and destructor
      cl_TX(void);
      ~cl_TX(void);

      // Steady-state data transmission
      void func_TX_data_send(cl_Comm_Sockets &obj_Comm_arg, bool b_data_print_arg);

      // Startup protocol transmissions
      void func_TX_startup_start_send(cl_Comm_Sockets &obj_Comm_arg);
      int  func_TX_history_meta_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_arg);
      void func_TX_history_chunk_send(cl_Comm_Sockets &obj_Comm_arg, int i_seq_arg, int i_lookback_arg);

   protected:
      void func_stub();
};


// Constructor
cl_TX::cl_TX(void)
{
   d_price_ask = 0.0;
   d_price_bid = 0.0;
   dt_tstamp = 0;
   i_history_total = 0;
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
   obj_JSON.func_raw_add("symbol_digits", IntegerToString(_Digits));

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

// Copy full history into buffer, compute chunk metadata and send TX_HISTORY_META.
// Returns chunks_total so the Controller can drive the chunk loop.
int cl_TX::func_TX_history_meta_send(cl_Comm_Sockets &obj_Comm_arg, int i_lookback_arg)
{
   i_history_total = 0;

   if(en_inp_ct_curr == en_cd_renko)
   {
      int i_effective = MathMin(i_lookback_arg, MAX_HISTORY_TICKS_SAFE_CAP);
      if(i_effective < i_lookback_arg)
         printf("[TX][WARNING] Requested tick lookback %d exceeds safe cap %d. Truncating.", i_lookback_arg, MAX_HISTORY_TICKS_SAFE_CAP);

      i_history_total = CopyTicks(Symbol(), arr_tick_history, COPY_TICKS_ALL, 0, i_effective);
      if(i_history_total <= 0)
      {
         printf("[TX][ERROR] CopyTicks failed. Error = %d.", GetLastError());
         return 0;
      }
   }
   else
   {
      i_history_total = CopyRates(Symbol(), PERIOD_CURRENT, 0, i_lookback_arg, arr_rates_history);
      if(i_history_total <= 0)
      {
         printf("[TX][ERROR] CopyRates failed. Error = %d.", GetLastError());
         return 0;
      }
   }

   if(i_history_total < i_lookback_arg)
      printf("[TX][WARNING] Requested %d items but only %d available.", i_lookback_arg, i_history_total);

   int i_chunks_total = (int)MathCeil((double)i_history_total / HISTORY_CHUNK_SIZE);

   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", TX_HISTORY_META);
   obj_JSON.func_raw_add("ticks_total",   IntegerToString(i_history_total));
   obj_JSON.func_raw_add("chunk_size",    IntegerToString(HISTORY_CHUNK_SIZE));
   obj_JSON.func_raw_add("chunks_total",  IntegerToString(i_chunks_total));
   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected)
   {
      obj_Comm_arg.SendData(str_TX, true, TX_HISTORY_META);
      printf("[TX][INFO] HISTORY_META sent. ticks_total = %d | chunk_size = %d | chunks_total = %d.",
             i_history_total, HISTORY_CHUNK_SIZE, i_chunks_total);
   }
   else printf("[TX][ERROR] EA is not connected. Can't send HISTORY_META.");

   return i_chunks_total;
}

// Send a single history chunk identified by seq (1-based).
// Chunks are ordered most-recent-first: chunk 1 = newest items, chunk N = oldest.
void cl_TX::func_TX_history_chunk_send(cl_Comm_Sockets &obj_Comm_arg, int i_seq_arg, int i_lookback_arg)
{
   if(i_history_total <= 0)
   {
      printf("[TX][ERROR] HISTORY_CHUNK seq=%d requested but history buffer is empty.", i_seq_arg);
      return;
   }

   int i_chunks_total = (int)MathCeil((double)i_history_total / HISTORY_CHUNK_SIZE);

   // Chunk 1 = most recent slice, chunk N = oldest slice
   // Slice end (exclusive) counting from the newest item
   int i_end   = i_history_total - (i_seq_arg - 1) * HISTORY_CHUNK_SIZE; // exclusive, from array end
   int i_start = MathMax(0, i_end - HISTORY_CHUNK_SIZE);                 // inclusive
   int i_count = i_end - i_start;

   if(i_count <= 0)
   {
      printf("[TX][ERROR] HISTORY_CHUNK seq=%d: computed empty slice. Skipping.", i_seq_arg);
      return;
   }

   obj_JSON.func_reset();
   obj_JSON.func_str_add("type", TX_HISTORY);
   obj_JSON.func_raw_add("seq",          IntegerToString(i_seq_arg));
   obj_JSON.func_raw_add("chunks_total", IntegerToString(i_chunks_total));

   if(en_inp_ct_curr == en_cd_renko)
   {
      string str_arr = "[";
      for(int i = i_start; i < i_end; i++)
      {
         if(i > i_start) str_arr += ",";
         str_arr += "{\"time\":";
         str_arr += IntegerToString(arr_tick_history[i].time);
         str_arr += ",\"price\":";
         str_arr += DoubleToString(arr_tick_history[i].bid, _Digits);
         str_arr += "}";
      }
      str_arr += "]";
      obj_JSON.func_raw_add("ticks", str_arr);
   }
   else
   {
      string str_arr = "[";
      for(int i = i_start; i < i_end; i++)
      {
         if(i > i_start) str_arr += ",";
         str_arr += "{\"time\":";
         str_arr += IntegerToString(arr_rates_history[i].time);
         str_arr += ",\"open\":";
         str_arr += DoubleToString(arr_rates_history[i].open, _Digits);
         str_arr += ",\"high\":";
         str_arr += DoubleToString(arr_rates_history[i].high, _Digits);
         str_arr += ",\"low\":";
         str_arr += DoubleToString(arr_rates_history[i].low, _Digits);
         str_arr += ",\"close\":";
         str_arr += DoubleToString(arr_rates_history[i].close, _Digits);
         str_arr += "}";
      }
      str_arr += "]";
      obj_JSON.func_raw_add("candles", str_arr);
   }

   string str_TX = obj_JSON.func_str_return() + COMM_MSG_DELIMITER;

   bool b_connected = obj_Comm_arg.IsConnected();
   if(b_connected)
   {
      obj_Comm_arg.SendData(str_TX, true, TX_HISTORY);
      printf("[TX][INFO] HISTORY chunk %d/%d sent. Items = %d | payload = %d bytes.",
             i_seq_arg, i_chunks_total, i_count, StringLen(str_TX));
   }
   else printf("[TX][ERROR] EA is not connected. Can't send HISTORY chunk %d.", i_seq_arg);
}

void cl_TX::func_stub()
{

}
