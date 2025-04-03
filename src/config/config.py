import json


dict_config_default = {
    "GUI":
    {
        "version": "1.00", 
        "GUI_height": 1200, 
        "GUI_width": 2000, 
        "terminal_height": 500,
        "text_field_width_max": 200
    },
    "asset":
    {
        "symbol": "XAUUSD", 
        "brick_size_points": 10
    },
    "price_feed":
    {
        "MT5":
        {
            "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
            "lookback_hours": 6
        }
    },
    "chart":
    {
        "INDs":
        {
            "MA_001":
            {
                "length": 10
            },
            "MA_002":
            {
                "length": 20
            }
        }
    },
    "strategy":
    {
        "positions":
        {
            "magic_number": 1001,
            "lot_size": 0.1,
            "SL_points": 1000,
            "TP_points": 1000,
            "deviation_points": 10
        },
        "filters":
        {
            "trading_period":
            {
                "enabled": 0,
                "start": "14:30:00",
                "end": "18:00:00"
            }
        },
        "risk_management":
        {
            "break_even":
            {
                "target_points": 20.0,
                "level_points": 5.0
            }
        }
    },
    "logger":
    {
        "path": "log.txt"
    }
}


def config_return():
    config_filename = 'config.json'
    dict_config = {}
    dict_config_file = {}
    file_found = False
    try:
        with open(config_filename) as json_file:
            str_file = json_file.read()
            dict_config_file = json.loads(str_file)
            file_found = True
    except FileNotFoundError:
        print(f"[WARNING] File \'{config_filename}\' does not exist.")
    if(file_found):
        dict_config = dict_config_file
    else:
        dict_config = dict_config_default
    return(dict_config)
