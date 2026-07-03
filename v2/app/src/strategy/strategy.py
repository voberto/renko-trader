# strategy.py
# Final adjustment: Supports both flat and enveloped JSON structures.

import glob
import json
import os
import sys
import importlib.util
from typing import Callable, Optional

import pandas as pd
from .strategy_utils import cl_StrategyBase


STRAT_LOG_MODULE = "STRAT"


class cl_StrategyManager:
    def __init__(self, logger_callback: Callable[[str], None]) -> None:
        self._log = logger_callback
        self._strategies: list[cl_StrategyBase] = []
        self._strategy_map: dict[str, type[cl_StrategyBase]] = {}

    def discover_and_load(self, strategy_dir: str, active_indicators: list[dict]) -> None:
        self._strategies.clear()
        abs_strategy_dir = os.path.abspath(strategy_dir)
        self._log(f"[{STRAT_LOG_MODULE}] Searching in: {abs_strategy_dir}")

        self._discover_strategy_classes(abs_strategy_dir)

        pattern = os.path.join(abs_strategy_dir, "strat_config_*.json")
        files = sorted(glob.glob(pattern))

        for filepath in files:
            self._load_single_strategy(filepath, active_indicators)

        self._log(f"[{STRAT_LOG_MODULE}] Discovery complete. {len(self._strategies)} strategy(ies) active.")

    def _discover_strategy_classes(self, strategy_dir: str) -> None:
        py_files = glob.glob(os.path.join(strategy_dir, "strategy_*.py"))
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(strategy_dir)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        for py_file in py_files:
            module_name = f"src.strategy.{os.path.basename(py_file)[:-3]}"
            try:
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and issubclass(attr, cl_StrategyBase) and attr is not cl_StrategyBase):
                        self._strategy_map[attr_name] = attr
            except Exception as e:
                self._log(f"[{STRAT_LOG_MODULE}] Failed to import {module_name}: {e}")

    def _load_single_strategy(self, filepath: str, active_indicators: list[dict]) -> None:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            self._log(f"[{STRAT_LOG_MODULE}] {filename} -> Read error: {e}")
            return

        # Handle Enveloped Structure (like indicators) or Flat Structure
        # Find the first key that doesn't start with '_'
        keys = [k for k in raw_data.keys() if not k.startswith("_")]
        
        # If there's only one relevant key and it contains 'enabled' or 'ID', it's an envelope
        if len(keys) == 1 and isinstance(raw_data[keys[0]], dict):
            cfg = raw_data[keys[0]]
            self._log(f"[{STRAT_LOG_MODULE}] DEBUG: Enveloped strategy detected using key: {keys[0]}")
        else:
            cfg = raw_data
            self._log(f"[{STRAT_LOG_MODULE}] DEBUG: Flat strategy structure detected.")

        strat_id = cfg.get("ID")
        strat_name = cfg.get("name", "Unknown")
        
        # Robust enabled check
        enabled_val = cfg.get("enabled")
        is_enabled = str(enabled_val).lower() == "true"

        if not is_enabled:
            # We log the ID and Name to ensure we are looking at the right config
            self._log(f"[{STRAT_LOG_MODULE}] {filename} -> Disabled (ID={strat_id}, Name={strat_name}).")
            return

        class_name = cfg.get("class_name")
        if class_name not in self._strategy_map:
            self._log(f"[{STRAT_LOG_MODULE}] {filename} -> FAILED: Class '{class_name}' not loaded.")
            return

        try:
            strat_instance = self._strategy_map[class_name](cfg)
        except Exception as e:
            self._log(f"[{STRAT_LOG_MODULE}] {filename} -> Instantiation error: {e}")
            return

        self._log(f"[{STRAT_LOG_MODULE}] DEBUG active_indicators: {active_indicators}")

        # Collect all candidates grouped by unique indicator type required
        required_types = set(req.get("type") for req in cfg.get("required_indicators", []))
        candidates = {}
        for ind_type in required_types:
            matches = self._find_all_of_type(ind_type, active_indicators)
            if not matches:
                self._log(f"[{STRAT_LOG_MODULE}] {strat_name} -> FAILED: No indicators of type '{ind_type}'.")
                return
            candidates[ind_type] = matches

        # Delegate arbitration to the strategy itself
        try:
            strat_instance.set_bindings(candidates)
        except ValueError as e:
            self._log(f"[{STRAT_LOG_MODULE}] {strat_name} -> FAILED: {e}")
            return

        self._strategies.append(strat_instance)
        self._log(f"[{STRAT_LOG_MODULE}] {filename} -> OK: {strat_name} (ID={strat_id}) loaded and bound.")

    def _find_all_of_type(self, target_type: str, active_indicators: list[dict]) -> list[dict]:
        """Returns all active indicators matching the required type, with their params."""
        results = []
        for ind_config in active_indicators:
            if target_type in ind_config:
                cfg = ind_config[target_type]
                results.append({"name": cfg.get("name"), "params": cfg})
        return results

    def warmup_all(self, df_candles: pd.DataFrame, indicator_results: dict[str, Optional[pd.DataFrame]]) -> None:
        """
        Sequentially feeds historical candles and indicator results to all active strategies
        to seed their internal states before live streaming begins.
        """
        if df_candles.empty:
            return

        self._log(f"[{STRAT_LOG_MODULE}] Warming up strategies with {len(df_candles)} historical candles...")

        for idx, candle in df_candles.iterrows():
            for strategy in self._strategies:
                strat_ind_map = {}
                for role, bound_name in strategy.get_bindings().items():
                    df_ind = indicator_results.get(bound_name)
                    if df_ind is not None and len(df_ind) > idx:
                        # Get indicator value at the same index as the candle
                        strat_ind_map[role] = df_ind.iloc[idx]["value"]
                
                strategy.warmup(candle, strat_ind_map)

        self._log(f"[{STRAT_LOG_MODULE}] Warmup complete.")

    def execute(self, candle: pd.Series, indicator_results: dict[str, Optional[pd.Series]]) -> list[dict]:
        all_signals = []
        for strategy in self._strategies:
            # Pass all indicator values by name — strategy uses its internal bound names
            strat_ind_map = {
                name: series.get("value")
                for name, series in indicator_results.items()
                if series is not None
            }

            signal = strategy.process(candle, strat_ind_map)
            if signal:
                all_signals.append(signal)
        return all_signals