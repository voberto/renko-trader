//+------------------------------------------------------------------+
//|                                                   JSON_funcs.mq5 |
//+------------------------------------------------------------------+


// Minimal JSON builder (standalone, no external dependencies)
class cl_JSON
{
   private:
      bool   b_first;
      string str_json;

   public:
      cl_JSON()  { func_reset(); }
      ~cl_JSON() {}

      void func_reset()
      {
         str_json = "{";
         b_first  = true;
      }

      void func_sep_add()
      {
         if(!b_first) str_json += ",";
         b_first = false;
      }

      void func_str_add(string str_key_arg, string str_value_arg)
      {
         func_sep_add();
         str_json += "\"" + str_key_arg + "\":\"" + func_str_escape_return(str_value_arg) + "\"";
      }

      void func_bool_add(string str_key_arg, bool b_value_arg)
      {
         func_sep_add();
         str_json += "\"" + str_key_arg + "\":" + (b_value_arg ? "true" : "false");
      }

      void func_double_add(string str_key_arg, double d_value_arg, int i_digits_arg)
      {
         func_sep_add();
         string s = DoubleToString(d_value_arg, i_digits_arg);
         StringReplace(s, ",", ".");
         str_json += "\"" + str_key_arg + "\":" + s;
      }

      void func_raw_add(string str_key_arg, string str_raw_value_arg)
      {
         func_sep_add();
         str_json += "\"" + str_key_arg + "\":" + str_raw_value_arg;
      }

      string func_str_return() { return(str_json + "}"); }

   private:
      string func_str_escape_return(string str_arg)
      {
         string s = str_arg;
         StringReplace(s, "\\", "\\\\");
         StringReplace(s, "\"", "\\\"");
         StringReplace(s, "\n", "\\n");
         StringReplace(s, "\r", "\\r");
         StringReplace(s, "\t", "\\t");
         return(s);
      }
};