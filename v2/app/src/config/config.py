import json
import os

class cl_Config:
    def __init__(self, logger_callback=None):
        """
        Optional function to log messages during initialization.
        """
        self.dic_config = {}
        self._load_config(logger_callback)

    def _load_config(self, logger_callback):
        """
        Loads configuration from config.json.
        Tries the current working directory first, then the root directory where main.py resides.
        """
        # 1. Path based on Current Working Directory
        cwd_path = os.path.join(os.getcwd(), 'config.json')
        
        # 2. Path relative to this file's location.
        # Assuming config.py is in src/config/, we go up two levels to reach the project root.
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        script_path = os.path.join(script_dir, 'config.json')

        final_path = None

        if os.path.exists(cwd_path):
            final_path = cwd_path
        elif os.path.exists(script_path):
            final_path = script_path

        try:
            if not final_path:
                raise FileNotFoundError(f"config.json not found in {os.getcwd()} or {script_dir}")
            
            with open(final_path, 'r', encoding='utf-8') as f:
                self.dic_config = json.load(f)
            
            if logger_callback:
                logger_callback(f"Config file loaded successfully from: {final_path}")
                
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error loading config.json: {str(e)}")
            self.dic_config = {}

    def get_val(self, section, key, default=None):
        """
        Returns a specific configuration value safely.
        """
        try:
            return self.dic_config.get(section, {}).get(key, default)
        except Exception:
            return default