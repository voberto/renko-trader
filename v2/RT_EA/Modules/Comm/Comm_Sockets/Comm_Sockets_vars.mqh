//+------------------------------------------------------------------+
//|                                            Comm_Sockets_vars.mqh |
//|                                                                  |
//|     Socket configuration constants for the cl_Comm_Sockets class.|
//| The previous DLL-based implementation (Ws2_32.dll) was replaced  |
//| by the native MQL5 socket functions (build 5833+), so all the    |
//| Winsock imports, C++ structs (WSAData, sockaddr_in, sockaddr)    |
//| and WSA error defines are no longer required.                    |
//+------------------------------------------------------------------+

// Connection timeout used by SocketConnect() (milliseconds)
#define COMM_CONNECT_TIMEOUT_MS     (5000)
// Read timeout used by SocketRead() (milliseconds). Kept small so the
// receive path never blocks the EA event loop (non-blocking behaviour).
#define COMM_READ_TIMEOUT_MS        (1)
// Receive buffer size (bytes)
#define COMM_RECV_BUFFER_SIZE       (1024)
