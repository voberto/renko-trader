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
        Loads configuration from config.json located in the project root.
        """
        config_path = os.path.join(os.getcwd(), 'config.json')
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found at {config_path}")
            
            with open(config_path, 'r') as f:
                self.dic_config = json.load(f)
            
            if logger_callback:
                logger_callback("Config file loaded successfully.")
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error loading config.json: {str(e)}")

    def get_val(self, section, key, default=None):
        """
        Returns a specific configuration value safely.
        """
        try:
            return self.dic_config.get(section, {}).get(key, default)
        except Exception:
            return default