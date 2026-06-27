//+------------------------------------------------------------------+
//|                                                   Controller.mqh |
//+------------------------------------------------------------------+

#include "RX/RX_funcs.mqh"
#include "TX/TX_funcs.mqh"


class cl_Controller
{
   private:
      en_Comm_State en_comm_state_curr;
      bool b_symbol_sent;
      bool b_history_sent;

   public:
      cl_Controller(void);
      ~cl_Controller(void);
      void func_loop_OnInit(cl_Comm_Sockets &obj_Comm_arg, string str_server_ip_arg, int i_server_port_arg, 
                            bool b_comm_period_enabled_arg, string str_comm_tstamp_start_arg, string str_comm_tstamp_end_arg,
                            int i_timer_period_ms_arg);
      void func_loop_OnTick(cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg);
      void func_loop_OnDeinit();
      void func_loop_OnTimer(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg);

   protected:
      void func_reset_startup_state(cl_RX &obj_RX_arg);
      void func_process_startup_step(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg);
};

// Constructor
cl_Controller::cl_Controller(void)
{
   en_comm_state_curr = COMM_STATE_DISCONNECTED;
   b_symbol_sent = false;
   b_history_sent = false;
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
   b_symbol_sent = false;
   b_history_sent = false;
   EventSetMillisecondTimer(i_timer_period_ms_arg);
}

void cl_Controller::func_loop_OnTick(cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg)
{
   if(en_comm_state_curr == COMM_STATE_STREAMING) obj_TX_arg.func_TX_data_send(obj_Comm_arg);
}

void cl_Controller::func_loop_OnDeinit()
{
   EventKillTimer();
}

void cl_Controller::func_reset_startup_state(cl_RX &obj_RX_arg)
{
   b_symbol_sent = false;
   b_history_sent = false;
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

   if(en_comm_state_curr == COMM_STATE_DISCONNECTED) en_comm_state_curr = COMM_STATE_WAIT_SYMBOL_ACK;

   if(en_comm_state_curr == COMM_STATE_WAIT_SYMBOL_ACK)
   {
      if(!b_symbol_sent)
      {
         obj_TX_arg.func_TX_startup_symbol_send(obj_Comm_arg);
         b_symbol_sent = true;
      }
      if(obj_RX_arg.func_b_ack_symbol_received())
      {
         en_comm_state_curr = COMM_STATE_WAIT_HISTORY_ACK;
      }
      return;
   }

   if(en_comm_state_curr == COMM_STATE_WAIT_HISTORY_ACK)
   {
      if(!b_history_sent && obj_RX_arg.func_b_ack_symbol_received())
      {
         obj_TX_arg.func_TX_startup_history_send(obj_Comm_arg, i_inp_lookback_startup_ticks);
         b_history_sent = true;
      }
      if(obj_RX_arg.func_b_ack_history_received())
      {
         en_comm_state_curr = COMM_STATE_STREAMING;
         printf("[CTRL][INFO] Startup completed. Streaming enabled.");
      }
      return;
   }
}

void cl_Controller::func_loop_OnTimer(cl_RX &obj_RX_arg, cl_TX &obj_TX_arg, cl_Comm_Sockets &obj_Comm_arg)
{
   obj_RX_arg.func_loop_OnTimer(obj_Comm_arg);
   func_process_startup_step(obj_RX_arg, obj_TX_arg, obj_Comm_arg);
}