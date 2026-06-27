//+------------------------------------------------------------------+
//|                                                      EA_vars.mqh |
//+------------------------------------------------------------------+

// Definitions
#define COMM_MSG_DELIMITER    "\n"
#define RX_STATE_CMD          "CMD"
#define RX_SIZE_LIMIT         8192
// Protocol type
#define TX_SYMBOL             "TX_SYMBOL"
#define TX_HISTORY            "TX_HISTORY"
#define TX_DATA               "TX_DATA"
#define RX_ACK_SYMBOL         "RX_ACK_SYMBOL"
#define RX_ACK_HISTORY        "RX_ACK_HISTORY"

// Modules
#include "Modules/Comm/Comm_Sockets/Comm_Sockets_funcs.mqh"
#include "Modules/JSON/JSON_funcs.mqh"

enum en_Comm_State
{
   COMM_STATE_DISCONNECTED,
   COMM_STATE_WAIT_SYMBOL_ACK,
   COMM_STATE_WAIT_HISTORY_ACK,
   COMM_STATE_STREAMING,
};

// Inputs
input group "--- [1] CONNECTION ---"            // --- [1] CONNECTION ---
input string str_inp_host = "127.0.0.1";        // [1.1] Host (IP address)
input int i_inp_port = 9005;                    // [1.2] Port
input int i_inp_timer_period_ms = 16;           // [1.3] Timer period (ms)
input int i_inp_lookback_startup_ticks = 5000;  // [1.4] Startup lookback (ticks)


// Variables
cl_Comm_Sockets obj_Comm;