//+------------------------------------------------------------------+
//|                                                      EA_vars.mqh |
//+------------------------------------------------------------------+

// Definitions
#define COMM_MSG_DELIMITER    "<FRAME_END>"
#define RX_STATE_CMD          "CMD"
#define RX_SIZE_LIMIT         8192
// Protocol type
#define TX_START              "TX_START"
#define TX_HISTORY            "TX_HISTORY"
#define TX_DATA               "TX_DATA"
#define RX_ACK_START          "RX_ACK_START"
#define RX_ACK_HISTORY        "RX_ACK_HISTORY"
// Security cap for history payload to avoid 
// socket buffer overflow (approx 150-200 bytes per tick in JSON)
#define MAX_HISTORY_TICKS_SAFE_CAP  10000

#define SIG_TYPE_LONG         "LONG_OPEN"
#define SIG_TYPE_SHORT        "SHORT_OPEN"

// Modules
#include "Modules/Comm/Comm_Sockets/Comm_Sockets_funcs.mqh"
#include "Modules/JSON/JSON_funcs.mqh"

enum en_Comm_State
{
   COMM_STATE_DISCONNECTED,
   COMM_STATE_WAIT_START_ACK,
   COMM_STATE_WAIT_HISTORY_ACK,
   COMM_STATE_STREAMING,
};

enum en_candles_type
{
   en_cd_regular = 0,   // Regular
   en_cd_renko = 1,     // Renko
};


// Inputs
input group "--- [1] CONNECTION ---"                  // --- [1] CONNECTION ---
input string str_inp_host = "127.0.0.1";              // [1.1] Host (IP address)
input int i_inp_port = 9005;                          // [1.2] Port
input int i_inp_timer_period_ms = 16;                 // [1.3] Timer period (ms)
input int i_inp_lookback_startup_candles = 100;       // [1.4] Startup lookback (candles/ticks)

input group "--- [2] SETUP ---"                       // --- [2] SETUP ---
input en_candles_type en_inp_ct_curr = en_cd_regular; // [2.1] Candle type
input int i_inp_renko_brick_size = 1000;              // [2.2] Brick size (points)

input group "--- [3] STARTUP PROTOCOL ---"            // --- [3] STARTUP PROTOCOL ---
input int i_inp_startup_ack_timeout_ms = 2000;        // [3.1] ACK timeout per startup step (ms)
input int i_inp_startup_max_retries    = 5;           // [3.2] Max retransmissions before reset
input int i_inp_reconnect_backoff_ms   = 1000;        // [3.3] Min interval between reconnect attempts (ms)

input group "--- [4] WATCHDOG ---"                    // --- [4] WATCHDOG ---
input int i_inp_watchdog_tx_window_ms  = 30000;       // [4.1] TX activity window (ms)
input int i_inp_watchdog_rx_timeout_ms = 60000;       // [4.2] RX silence timeout (ms)

input group "--- [5] TRADES ---"                      // --- [5] TRADES ---
input bool b_inp_trade_enabled = true;                // [5.1] Trades enabled?
input bool b_inp_trade_close_on_opp = true;           // [5.2] Close on opposite signal?
input bool b_inp_trade_async_enabled = true;          // [5.3] Async mode enabled?
input long l_inp_magic_number = 1001;                 // [5.4] Magic number
input double d_inp_lot_size = 0.01;                   // [5.5] Lot size
input double d_inp_SL_points = 500;                   // [5.6] Stop loss (points)
input double d_inp_TP_points = 500;                   // [5.7] Take profit (points)


// Variables
cl_Comm_Sockets obj_Comm;
