//+------------------------------------------------------------------+
//|                                           Comm_Sockets_funcs.mqh |
//|                                                                  |
//|     This library provides a class-based interface for TCP socket |
//| communication in MQL5, with automatic reconnection capabilities. |
//|                                                                  |
//|     This version uses the native MQL5 socket functions           |
//| (SocketCreate / SocketConnect / SocketSend / SocketRead, build   |
//| 5833+) instead of the Ws2_32.dll imports. Host names (DNS) are   |
//| resolved automatically by SocketConnect(), so both IP addresses  |
//| and DNS names are accepted as the server address.                |
//+------------------------------------------------------------------+

#include "Comm_Sockets_vars.mqh"


// Error description function
string func_str_NetSocketErrorDescript(int i_code_arg)
{
   string s = string(i_code_arg);
   switch(i_code_arg)
   {
      case ERR_NETSOCKET_INVALIDHANDLE:      return("(#"+s+") Wrong socket handle");
      case ERR_NETSOCKET_TOO_MANY_OPENED:    return("(#"+s+") Too many open sockets (limit is 128)");
      case ERR_NETSOCKET_CANNOT_CONNECT:     return("(#"+s+") Connection to remote host failed");
      case ERR_NETSOCKET_IO_ERROR:           return("(#"+s+") Data send/receive error");
      case ERR_NETSOCKET_HANDSHAKE_FAILED:   return("(#"+s+") Secure connection (TLS Handshake) error");
      case ERR_NETSOCKET_NO_CERTIFICATE:     return("(#"+s+") No data on a certificate securing the connection");
   }
   return("(#"+s+") Unknow error");
}

// Main socket communication class
class cl_Comm_Sockets
{
   private:
      // General variables
      bool b_backtest;
      bool b_comm_period_enabled;
      int i_bars_D1_curr, i_bars_D1_prev;
      string str_comm_tstamp_start, str_comm_tstamp_end;
      datetime dt_comm_tstamp_start, dt_comm_tstamp_end;

      // Socket connection parameters
      string m_server_ip;
      int m_server_port;
      
      // Socket state variables
      int m_client_socket;
      bool m_is_connected;
      
   public:
      // Constructor and destructor
      cl_Comm_Sockets(void);
      ~cl_Comm_Sockets(void);
      
      // Initialization and configuration methods
      void func_obj_init(string str_server_ip_arg, int i_server_port_arg, bool b_comm_period_enabled_arg, string str_comm_tstamp_start_arg, string str_comm_end_start);
      // OnTick loop
      void func_loop_OnTick();
      
      // Connection management methods
      bool Connect(bool b_msg_enabled_arg);
      void Disconnect(void);
      bool Reconnect(bool b_msg_enabled_arg);
      
      // Data transmission methods
      bool SendData(string str_data_arg, bool b_data_print_arg, string str_data_tier_arg);
      string ReceiveData(bool b_conn_reset_by_peer_enabled_arg);

      // Status methods
      bool IsConnected(void) const;
      
   protected:
      // Internal helper methods
      void CloseSocket(void);
      void HandleConnectionError(int i_error_code_arg, bool b_msg_enabled_arg);
      // Custom
      void func_comm_tstamp_D1_update();
      bool func_b_comm_enabled_by_period();
      string func_str_tstamp_return(datetime dt_tstamp_arg);
};

// Constructor
cl_Comm_Sockets::cl_Comm_Sockets(void)
{
   m_client_socket = INVALID_HANDLE;
   m_is_connected = false;
   m_server_ip = "";
   m_server_port = 0;
}

// Destructor
cl_Comm_Sockets::~cl_Comm_Sockets(void)
{
   if(m_client_socket != INVALID_HANDLE) Disconnect();
}

// Initialize the socket with server parameters
void cl_Comm_Sockets::func_obj_init(string str_server_ip_arg, int i_server_port_arg, bool b_comm_period_enabled_arg, string str_comm_tstamp_start_arg, string str_comm_tstamp_end_arg)
{
   m_server_ip = str_server_ip_arg;
   m_server_port = i_server_port_arg;
   b_comm_period_enabled = b_comm_period_enabled_arg;
   str_comm_tstamp_start = str_comm_tstamp_start_arg;
   str_comm_tstamp_end = str_comm_tstamp_end_arg;
   b_backtest = MQLInfoInteger(MQL_TESTER);

   func_comm_tstamp_D1_update();
}

void cl_Comm_Sockets::func_loop_OnTick()
{
   func_comm_tstamp_D1_update();
}

// Establish a connection to the server
bool cl_Comm_Sockets::Connect(bool b_msg_enabled_arg)
{
   // Close existing connection if needed
   if(m_client_socket != INVALID_HANDLE)
   {
      CloseSocket();
   }
   
   // Create socket
   m_client_socket = SocketCreate();
   if(m_client_socket == INVALID_HANDLE)
   {
      printf("[COMM_SOCKETS][ERROR] Socket failed error: %s.", func_str_NetSocketErrorDescript(GetLastError()));
      CloseSocket();
      return(false);
   }
   
   // Connect to server (SocketConnect resolves DNS / IP automatically)
   if(!SocketConnect(m_client_socket, m_server_ip, m_server_port, COMM_CONNECT_TIMEOUT_MS))
   {
      int error = GetLastError();
      HandleConnectionError(error, b_msg_enabled_arg);
      CloseSocket();
      return(false);
   }
   
   if(IsConnected())
   {
      m_is_connected = true;
      printf("[COMM_SOCKETS][INFO] Successfully connected to server (IP = %s, port = %d).", m_server_ip, m_server_port);
      return(true);
   }

   return(false);
}

// Disconnect from the server
void cl_Comm_Sockets::Disconnect(void)
{
   CloseSocket();
   m_is_connected = false;
   printf("[COMM_SOCKETS][INFO] Socket closed (IP = %s, port = %d).", m_server_ip, m_server_port);
}

// Attempt to reconnect to the server
bool cl_Comm_Sockets::Reconnect(bool b_msg_enabled_arg)
{
   if(b_msg_enabled_arg) printf("[COMM_SOCKETS][INFO] Trying to reconnect to the server (IP = %s, port = %d) ...", m_server_ip, m_server_port);
   return Connect(b_msg_enabled_arg);
}

// Send data to the server
bool cl_Comm_Sockets::SendData(string str_data_arg, bool b_data_print_arg, string str_data_tier_arg)
{
   if(func_b_comm_enabled_by_period())
   {
      if(m_client_socket == INVALID_HANDLE || !m_is_connected)
      {
         printf("[COMM_SOCKETS][ERROR] EA is not connected to the server (IP = %s, port = %d).", m_server_ip, m_server_port);
         return(false);
      }
      
      uchar uch_data_chars_arr[];
      int i_data_len = StringToCharArray(str_data_arg, uch_data_chars_arr);
      
      // StringToCharArray appends a null terminator, so send data_len - 1 bytes
      int i_send_result = SocketSend(m_client_socket, uch_data_chars_arr, i_data_len - 1);
      if(i_send_result < 0)
      {
         int i_error = GetLastError();
         printf("[COMM_SOCKETS][ERROR] TX error (IP = %s, port = %d) = %s.", m_server_ip, m_server_port, func_str_NetSocketErrorDescript(i_error));
         m_is_connected = false;
         return(false);
      }
      else if(i_send_result == 0)
      {
         // Connection closed by server
         printf("[COMM_SOCKETS][INFO] Connection closed by server (IP = %s, port = %d).", m_server_ip, m_server_port);
         m_is_connected = false;
         return(false);
      }
      else
      {
         if(b_data_print_arg)       printf("[COMM_SOCKETS][INFO] Sent %s data to server (IP = %s, port = %d) = %s.", str_data_tier_arg, m_server_ip, m_server_port, str_data_arg);
         else if(!b_data_print_arg) printf("[COMM_SOCKETS][INFO] Sent %s data to server (IP = %s, port = %d).", str_data_tier_arg, m_server_ip, m_server_port);
      }
   }
   return true;
}

// Receive data from the server
string cl_Comm_Sockets::ReceiveData(bool b_conn_reset_by_peer_enabled_arg)
{
   if(func_b_comm_enabled_by_period())
   {
      if(m_client_socket == INVALID_HANDLE || !m_is_connected)
      {
         return("");
      }
      
      // Poll for available data so the read never blocks (non-blocking behaviour).
      // SocketIsReadable() returns the number of bytes currently waiting in the
      // socket buffer, or 0 if there is nothing to read right now.
      uint ui_bytes_pending = SocketIsReadable(m_client_socket);
      if(ui_bytes_pending == 0)
      {
         // No data available right now (equivalent to the old WSAEWOULDBLOCK).
         // Only treat this as a dropped connection if the socket itself is no
         // longer connected; otherwise it is the normal "nothing yet" case.
         if(!SocketIsConnected(m_client_socket))
         {
            if(!b_conn_reset_by_peer_enabled_arg) printf("[COMM_SOCKETS][ERROR] RX error (IP = %s, port = %d) = %s.", m_server_ip, m_server_port, func_str_NetSocketErrorDescript(GetLastError()));
            m_is_connected = false;
         }
         return "";
      }

      // Drain all data currently available in the socket buffer.
      //
      // CRITICAL: read EXACTLY the number of bytes reported by
      // SocketIsReadable() (never an arbitrarily larger buffer size). If we ask
      // SocketRead() for more bytes than are available, it will wait until the
      // timeout expires trying to fill the buffer and then return -1 with
      // error #5273 (ERR_NETSOCKET_IO_ERROR). Reading exactly the available
      // amount lets SocketRead() return immediately with the data.
      string str_data_received = "";
      while(ui_bytes_pending > 0)
      {
         uchar read_buffer[];
         int recv_result = SocketRead(m_client_socket, read_buffer, ui_bytes_pending, COMM_READ_TIMEOUT_MS);

         if(recv_result > 0)
         {
            str_data_received += CharArrayToString(read_buffer, 0, recv_result);
         }
         else if(recv_result == 0)
         {
            // Connection gracefully closed by the server
            printf("[COMM_SOCKETS][INFO] Connection closed by server (IP = %s, port = %d).", m_server_ip, m_server_port);
            m_is_connected = false;
            break;
         }
         else // recv_result < 0
         {
            // -1 can be either a transient timeout (no fatal error) or a real
            // I/O error. Only flag the connection as lost when the socket is
            // actually disconnected, so a momentary timeout does not kill an
            // otherwise healthy connection mid-handshake.
            if(!SocketIsConnected(m_client_socket))
            {
               if(!b_conn_reset_by_peer_enabled_arg) printf("[COMM_SOCKETS][ERROR] RX error (IP = %s, port = %d) = %s.", m_server_ip, m_server_port, func_str_NetSocketErrorDescript(GetLastError()));
               m_is_connected = false;
            }
            break;
         }

         // More data may have arrived while we were reading; keep draining.
         ui_bytes_pending = SocketIsReadable(m_client_socket);
      }

      return(str_data_received);
   }

   return("");
}

// Check if currently connected
bool cl_Comm_Sockets::IsConnected(void) const
{
   return m_is_connected;
}

void cl_Comm_Sockets::func_comm_tstamp_D1_update()
{
   if(b_comm_period_enabled)
   {
      i_bars_D1_curr = Bars(Symbol(), PERIOD_D1);

      if(i_bars_D1_curr > i_bars_D1_prev)
      {
         if(b_backtest)
         {
            dt_comm_tstamp_start = StringToTime(str_comm_tstamp_start);
            dt_comm_tstamp_end   = StringToTime(str_comm_tstamp_end);
         }
         else if(!b_backtest)
         {
            dt_comm_tstamp_start = StringToTime(str_comm_tstamp_start)  - StringToTime("00:00") + StringToTime(TimeToString(TimeTradeServer(), TIME_DATE));
            dt_comm_tstamp_end   = StringToTime(str_comm_tstamp_end)    - StringToTime("00:00") + StringToTime(TimeToString(TimeTradeServer(), TIME_DATE));
         }
         
         printf("[COMM][INFO] Communication period updated. Start = %s, end = %s.", func_str_tstamp_return(dt_comm_tstamp_start), func_str_tstamp_return(dt_comm_tstamp_end));
      }

      i_bars_D1_prev = i_bars_D1_curr;
   }
}

bool cl_Comm_Sockets::func_b_comm_enabled_by_period()
{
   bool b_retval = false;

   if(!b_comm_period_enabled) b_retval = true;
   else if(b_comm_period_enabled)   
   {
      datetime dt_time_now = TimeTradeServer();

      if(dt_time_now >= dt_comm_tstamp_start && dt_time_now <= dt_comm_tstamp_end) b_retval = true;
   }

   return(b_retval);
}

// Close the socket cleanly
void cl_Comm_Sockets::CloseSocket(void)
{
   if(m_client_socket != INVALID_HANDLE)
   {
      SocketClose(m_client_socket);
      m_client_socket = INVALID_HANDLE;
   }
}

// Handle connection errors with specific messages
void cl_Comm_Sockets::HandleConnectionError(int i_error_code_arg, bool b_msg_enabled_arg)
{
   if(i_error_code_arg == ERR_NETSOCKET_CANNOT_CONNECT)
   {
      if(b_msg_enabled_arg) printf("[COMM_SOCKETS][ERROR] Connection failed. Server may be down (IP = %s, port = %d).", m_server_ip, m_server_port);
   }
   else
   {
      printf("[COMM_SOCKETS][ERROR] Connection error (IP = %s, port = %d) = %s.", m_server_ip, m_server_port, func_str_NetSocketErrorDescript(i_error_code_arg));
   }
}

string cl_Comm_Sockets::func_str_tstamp_return(datetime dt_tstamp_arg)
{
   return(StringFormat("%s %s", TimeToString(dt_tstamp_arg, TIME_DATE), TimeToString(dt_tstamp_arg, TIME_MINUTES)));
}
