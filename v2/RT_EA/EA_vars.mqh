//+------------------------------------------------------------------+
//|                                                      EA_vars.mqh |
//+------------------------------------------------------------------+

// Definitions
#define COMM_MSG_DELIMITER    "<FRAME_END>"
#define RX_STATE_CMD          "CMD"
#define RX_SIZE_LIMIT         8192
// Protocol type
#define TX_SYMBOL             "TX_SYMBOL"
#define TX_HISTORY            "TX_HISTORY"
#define TX_DATA               "TX_DATA"
#define RX_ACK_SYMBOL         "RX_ACK_SYMBOL"
#define RX_ACK_HISTORY        "RX_ACK_HISTORY"
// Security cap for history payload to avoid 
// socket buffer overflow (approx 150-200 bytes per tick in JSON)
#define MAX_HISTORY_TICKS_SAFE_CAP  2000

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
input group "--- [1] CONNECTION ---"                  // --- [1] CONNECTION ---
input string str_inp_host = "127.0.0.1";              // [1.1] Host (IP address)
input int i_inp_port = 9005;                          // [1.2] Port
input int i_inp_timer_period_ms = 16;                 // [1.3] Timer period (ms)
input int i_inp_lookback_startup_candles = 100;       // [1.4] Startup lookback (candles)

input group "--- [2] STARTUP PROTOCOL ---"            // --- [2] STARTUP PROTOCOL ---
input int i_inp_startup_ack_timeout_ms = 2000;        // [2.1] ACK timeout per startup step (ms)
input int i_inp_startup_max_retries    = 5;           // [2.2] Max retransmissions before reset
input int i_inp_reconnect_backoff_ms   = 1000;        // [2.3] Min interval between reconnect attempts (ms)

input group "--- [3] WATCHDOG ---"                    // --- [3] WATCHDOG ---
input int i_inp_watchdog_tx_window_ms  = 30000;       // [3.1] TX activity window (ms)
input int i_inp_watchdog_rx_timeout_ms = 60000;       // [3.2] RX silence timeout (ms)

// Variables
cl_Comm_Sockets obj_Comm;
