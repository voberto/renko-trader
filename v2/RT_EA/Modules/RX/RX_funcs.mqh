//+------------------------------------------------------------------+
//|                                                     RX_funcs.mqh |
//+------------------------------------------------------------------+

#include "../../EA_vars.mqh"
#include "../Positions/Positions_funcs.mqh"


class cl_RX
{
   private:
      bool b_reconnect_attempt;
      string str_RX_buffer;
      // Startup protocol state flags
      bool b_ack_symbol_received;
      bool b_ack_history_received;
      
      // Reconnect backoff tracking
      ulong ul_last_reconnect_attempt_ms;
      
      // RX activity watchdog
      ulong ul_last_rx_activity_ms;

   public:
      // Constructor and destructor
      cl_RX(void);
      ~cl_RX(void);   
      void func_loop_OnTimer(cl_Comm_Sockets &obj_Comm_arg, cl_Positions &obj_Positions_arg);
      
      // Startup protocol state getters
      bool func_b_ack_symbol_received(void) const;
      bool func_b_ack_history_received(void) const;
      void func_reset_startup_acks(void);
      void func_reset_session_state(void);
      
      // RX activity timestamp getter
      ulong func_ul_last_rx_activity_ms(void) const;

   protected:
      void func_RX_loop(cl_Comm_Sockets &obj_Comm_arg, cl_Positions &obj_Positions_arg);
      void func_message_handle(string str_msg_arg, cl_Positions &obj_Positions_arg);
      string func_str_field_extract(string str_json_arg, string str_key_arg);
      string func_str_truncate_return(string str_arg, int i_max_len_arg);
      string func_str_tail_return(string str_arg, int i_max_len_arg);
};


// Constructor
cl_RX::cl_RX(void)
{
   b_reconnect_attempt = false;
   str_RX_buffer = "";
   b_ack_symbol_received = false;
   b_ack_history_received = false;
   ul_last_reconnect_attempt_ms = 0;
   ul_last_rx_activity_ms = 0;
}

// Destructor
cl_RX::~cl_RX(void)
{

}

// Main OnTimer loop (reconnection + reception)
void cl_RX::func_loop_OnTimer(cl_Comm_Sockets &obj_Comm_arg, cl_Positions &obj_Positions_arg)
{
   // Reconnect if disconnected
   bool b_is_connected = obj_Comm_arg.IsConnected();
   if(!b_is_connected)
   {
      ulong ul_now = GetTickCount64();
      
      // Backoff check
      if(ul_now - ul_last_reconnect_attempt_ms < (ulong)i_inp_reconnect_backoff_ms) return;

      if(!b_reconnect_attempt) printf("[RX][WARNING] Connection lost. Attempting reconnect ...");
      
      b_reconnect_attempt = true;
      ul_last_reconnect_attempt_ms = ul_now;
      
      func_reset_session_state();
      
      obj_Comm_arg.Connect(false);
      return;
   }
   
   if(b_is_connected)
   {
      b_reconnect_attempt = false;

      // Receive and process incoming messages
      func_RX_loop(obj_Comm_arg, obj_Positions_arg);
   }
}

// Internal RX loop (buffering + framing)
void cl_RX::func_RX_loop(cl_Comm_Sockets &obj_Comm_arg, cl_Positions &obj_Positions_arg)
{
   string str_raw = obj_Comm_arg.ReceiveData(true);
   if(str_raw == "") return;
   
   // Mark RX activity timestamp
   ul_last_rx_activity_ms = GetTickCount64();
   
   str_RX_buffer += str_raw;

   if(StringLen(str_RX_buffer) > RX_SIZE_LIMIT)
   {
      // Log tail of buffer before clearing (most recent data is at the end)
      printf("[RX][WARNING] RX buffer exceeded safe size (%d). Clearing partial data. Tail = %s", RX_SIZE_LIMIT, func_str_tail_return(str_RX_buffer, 200));
      str_RX_buffer = "";
      return;
   }

   int i_delim_len = StringLen(COMM_MSG_DELIMITER);
   int i_pos;
   while((i_pos = StringFind(str_RX_buffer, COMM_MSG_DELIMITER)) >= 0)
   {
      string str_line = StringSubstr(str_RX_buffer, 0, i_pos);
      str_RX_buffer   = StringSubstr(str_RX_buffer, i_pos + i_delim_len);

      StringTrimLeft(str_line);
      StringTrimRight(str_line);
      if(StringLen(str_line) == 0) continue;

      // Frame validation: must look like a JSON object
      int i_len = StringLen(str_line);
      if(i_len < 2 || StringGetCharacter(str_line, 0) != '{' || StringGetCharacter(str_line, i_len - 1) != '}')
      {
         printf("[RX][WARNING] Malformed frame discarded: %s", func_str_truncate_return(str_line, 200));
         continue;
      }

      func_message_handle(str_line, obj_Positions_arg);
   }
}

// Message dispatcher (startup protocol + legacy CMD)
void cl_RX::func_message_handle(string str_msg_arg, cl_Positions &obj_Positions_arg)
{
   printf("[DEBUG] RX message = %s", str_msg_arg);
   
   string str_type = func_str_field_extract(str_msg_arg, "type");

   if(str_type == RX_STATE_CMD)
   {
      string str_cmd = func_str_field_extract(str_msg_arg, "value");
      
      printf("[DEBUG] Received valid command = %s.", str_cmd);

      // Process trades
      obj_Positions_arg.func_loop_pos(str_cmd);
   }
   else if(str_type == RX_ACK_START)
   {
      b_ack_symbol_received = true;
      printf("[RX][INFO] Received %s. App confirmed start reception.", RX_ACK_START);
   }
   else if(str_type == RX_ACK_HISTORY)
   {
      b_ack_history_received = true;
      printf("[RX][INFO] Received %s. App is ready for streaming ticks.", RX_ACK_HISTORY);
   }
   else
   {
      printf("[RX][WARNING] Unknown message type '%s'. Ignored.", str_type);
   }
}

// Startup protocol state getters (for the orchestrator)
bool cl_RX::func_b_ack_symbol_received(void) const
{
   return b_ack_symbol_received;
}

bool cl_RX::func_b_ack_history_received(void) const
{
   return b_ack_history_received;
}

// Reset startup flags (called on reconnect or EA restart)
void cl_RX::func_reset_startup_acks(void)
{
   b_ack_symbol_received = false;
   b_ack_history_received = false;
}

void cl_RX::func_reset_session_state(void)
{
   str_RX_buffer = "";
   func_reset_startup_acks();
   ul_last_rx_activity_ms = 0;
}

// RX activity timestamp getter
ulong cl_RX::func_ul_last_rx_activity_ms(void) const
{
   return ul_last_rx_activity_ms;
}

// JSON field extractor
string cl_RX::func_str_field_extract(string str_json_arg, string str_key_arg)
{
   string str_search = "\"" + str_key_arg + "\":";
   int i_pos = StringFind(str_json_arg, str_search);
   if(i_pos < 0) return("");
   int i_start = i_pos + StringLen(str_search);
   while(i_start < StringLen(str_json_arg) && StringGetCharacter(str_json_arg, i_start) == ' ') i_start++;

   if(i_start >= StringLen(str_json_arg)) return("");

   ushort uc_first = StringGetCharacter(str_json_arg, i_start);
   if(uc_first == '"')
   {
      i_start++;
      string str_value = "";
      int i = i_start;
      while(i < StringLen(str_json_arg))
      {
         ushort c = StringGetCharacter(str_json_arg, i);
         if(c == '\\') { i += 2; continue; }
         if(c == '"')  break;
         str_value += ShortToString(c);
         i++;
      }
      return(str_value);
   }
   else
   {
      string str_value = "";
      int i = i_start;
      while(i < StringLen(str_json_arg))
      {
         ushort c = StringGetCharacter(str_json_arg, i);
         if(c == ',' || c == '}' || c == ' ' || c == '\n') break;
         str_value += ShortToString(c);
         i++;
      }
      return(str_value);
   }
}

// String truncation helper for safe logging
string cl_RX::func_str_truncate_return(string str_arg, int i_max_len_arg)
{
   if(StringLen(str_arg) <= i_max_len_arg) return str_arg;
   return StringSubstr(str_arg, 0, i_max_len_arg) + "...";
}

// Tail extraction helper for overflow diagnostics
string cl_RX::func_str_tail_return(string str_arg, int i_max_len_arg)
{
   int i_len = StringLen(str_arg);
   if(i_len <= i_max_len_arg) return str_arg;
   int i_start = i_len - i_max_len_arg;
   return "..." + StringSubstr(str_arg, i_start, i_max_len_arg);
}
