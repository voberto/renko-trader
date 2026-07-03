//+------------------------------------------------------------------+
//|                                                   Controller.mqh |
//+------------------------------------------------------------------+

#include "RX/RX_funcs.mqh"
#include "TX/TX_funcs.mqh"
#include "Positions/Positions_funcs.mqh"

class cl_Controller
{
   private:
      en_Comm_State en_comm_state_curr;
      bool b_startup_sent;
      bool b_history_sent;
      bool b_data_print;
      
      // Robust startup tracking
      ulong ul_last_startup_send_ms;
      int i_startup_retry_count;
      
      // Watchdog: last TX_DATA timestamp
      ulong ul_last_tx_data_ms;

   public:
      cl_Controller(void);
      ~cl_Controller(void);
      void func_loop_OnInit(cl_Comm_Sockets &obj_Comm_arg, string str_server_ip_arg, int i_server_port_arg, 
                            bool b_comm_period_enabled_arg, string str_comm_tstamp_start_arg, string str_comm_tstamp_end_arg,
                            int i_timer_period_ms_arg);
      void func_loop_OnTick(cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg);
      void func_loop_OnDeinit();
      void func_loop_OnTimer(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg, cl_Positions &obj_Positions_arg);

   protected:
      void func_reset_startup_state(cl_RX &obj_RX_arg);
      void func_process_startup_step(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg);
      void func_log_state_transition(en_Comm_State en_from_arg, en_Comm_State en_to_arg);
};

// Constructor
cl_Controller::cl_Controller(void)
{
   en_comm_state_curr = COMM_STATE_DISCONNECTED;
   b_startup_sent = false;
   b_history_sent = false;
   b_data_print = false;
   ul_last_startup_send_ms = 0;
   i_startup_retry_count = 0;
   ul_last_tx_data_ms = 0;
}

// Destructor
cl_Controller::~cl_Controller(void)
{

}

void cl_Controller::func_loop_OnInit(cl_Comm_Sockets &obj_Comm_arg, string str_server_ip_arg, int i_server_port_arg, 
                                     bool b_comm_period_enabled_arg, string str_comm_tstamp_start_arg, string str_comm_tstamp_end_arg,
                                     int i_timer_period_ms_arg)
{
   obj_Comm_arg.func_obj_init(str_server_ip_arg, i_server_port_arg, b_comm_period_enabled_arg, str_comm_tstamp_start_arg, str_comm_tstamp_end_arg);
   en_comm_state_curr = COMM_STATE_DISCONNECTED;
   b_startup_sent = false;
   b_history_sent = false;
   b_data_print = false;
   ul_last_startup_send_ms = 0;
   i_startup_retry_count = 0;
   ul_last_tx_data_ms = 0;
   EventSetMillisecondTimer(i_timer_period_ms_arg);
}

void cl_Controller::func_loop_OnTick(cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg)
{
   if(en_comm_state_curr == COMM_STATE_STREAMING)
   {
      obj_TX_arg.func_TX_data_send(obj_Comm_arg, b_data_print);
      ul_last_tx_data_ms = GetTickCount64();
   }
}

void cl_Controller::func_loop_OnDeinit()
{
   EventKillTimer();
}

// State transition logger
void cl_Controller::func_log_state_transition(en_Comm_State en_from_arg, en_Comm_State en_to_arg)
{
   string str_names[] = {"DISCONNECTED", "WAIT_SYMBOL_ACK", "WAIT_HISTORY_ACK", "STREAMING"};
   printf("[CTRL][STATE] %s -> %s.", str_names[en_from_arg], str_names[en_to_arg]);
}

void cl_Controller::func_reset_startup_state(cl_RX &obj_RX_arg)
{
   b_startup_sent = false;
   b_history_sent = false;
   ul_last_startup_send_ms = 0;
   i_startup_retry_count = 0;
   ul_last_tx_data_ms = 0;
   if(en_comm_state_curr != COMM_STATE_DISCONNECTED) func_log_state_transition(en_comm_state_curr, COMM_STATE_DISCONNECTED);
   en_comm_state_curr = COMM_STATE_DISCONNECTED;
   obj_RX_arg.func_reset_startup_acks();
}

void cl_Controller::func_process_startup_step(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg)
{
   bool b_is_connected = obj_Comm_arg.IsConnected();
   if(!b_is_connected)
   {
      if(en_comm_state_curr != COMM_STATE_DISCONNECTED) printf("[CTRL][WARNING] Disconnected. Resetting startup state.");

      func_reset_startup_state(obj_RX_arg);
      return;
   }

   if(en_comm_state_curr == COMM_STATE_DISCONNECTED)
   {
      func_log_state_transition(COMM_STATE_DISCONNECTED, COMM_STATE_WAIT_START_ACK);
      en_comm_state_curr = COMM_STATE_WAIT_START_ACK;
   }

   ulong ul_now = GetTickCount64();

   //--- STATE: WAIT_START_ACK ---
   if(en_comm_state_curr == COMM_STATE_WAIT_START_ACK)
   {
      bool b_timeout = (ul_now - ul_last_startup_send_ms) > (ulong)i_inp_startup_ack_timeout_ms;
      
      if(!b_startup_sent || b_timeout)
      {
         if(b_startup_sent)
         {
            i_startup_retry_count++;
            if(i_startup_retry_count > i_inp_startup_max_retries)
            {
               printf("[CTRL][ERROR] Max retries reached for START ACK. Resetting connection.");
               obj_Comm_arg.Disconnect();
               return;
            }
            printf("[CTRL][WARNING] START ACK timeout. Retrying %d/%d...", i_startup_retry_count, i_inp_startup_max_retries);
         }
         else
         {
            printf("[CTRL][INFO] Sending START (first attempt).");
         }
         
         obj_TX_arg.func_TX_startup_start_send(obj_Comm_arg);
         b_startup_sent = true;
         ul_last_startup_send_ms = ul_now;
      }

      if(obj_RX_arg.func_b_ack_symbol_received())
      {
         i_startup_retry_count = 0;
         ul_last_startup_send_ms = 0;
         func_log_state_transition(COMM_STATE_WAIT_START_ACK, COMM_STATE_WAIT_HISTORY_ACK);
         en_comm_state_curr = COMM_STATE_WAIT_HISTORY_ACK;
      }
      return;
   }

   //--- STATE: WAIT_HISTORY_ACK ---
   if(en_comm_state_curr == COMM_STATE_WAIT_HISTORY_ACK)
   {
      bool b_timeout = (ul_now - ul_last_startup_send_ms) > (ulong)i_inp_startup_ack_timeout_ms;
      
      if(!b_history_sent || b_timeout)
      {
         if(b_history_sent)
         {
            i_startup_retry_count++;
            if(i_startup_retry_count > i_inp_startup_max_retries)
            {
               printf("[CTRL][ERROR] Max retries reached for HISTORY ACK. Resetting connection.");
               obj_Comm_arg.Disconnect();
               return;
            }
            printf("[CTRL][WARNING] HISTORY ACK timeout. Retrying %d/%d...", i_startup_retry_count, i_inp_startup_max_retries);
         }
         else
         {
            printf("[CTRL][INFO] Sending HISTORY (first attempt). Lookback = %d ticks.", i_inp_lookback_startup_candles);
         }

         obj_TX_arg.func_TX_startup_history_send(obj_Comm_arg, i_inp_lookback_startup_candles);
         b_history_sent = true;
         ul_last_startup_send_ms = ul_now;
      }

      if(obj_RX_arg.func_b_ack_history_received())
      {
         i_startup_retry_count = 0;
         ul_last_startup_send_ms = 0;
         func_log_state_transition(COMM_STATE_WAIT_HISTORY_ACK, COMM_STATE_STREAMING);
         en_comm_state_curr = COMM_STATE_STREAMING;
         printf("[CTRL][INFO] Startup completed. Streaming enabled.");
      }
      return;
   }

   //--- STATE: STREAMING ---
   if(en_comm_state_curr == COMM_STATE_STREAMING)
   {
      return;
   }
}

void cl_Controller::func_loop_OnTimer(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg, cl_Positions &obj_Positions_arg)
{
   obj_RX_arg.func_loop_OnTimer(obj_Comm_arg, obj_Positions_arg);
   func_process_startup_step(obj_RX_arg, obj_TX_arg, obj_Comm_arg);
}
