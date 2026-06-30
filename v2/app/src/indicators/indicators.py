# indicators.py
# cl_IndicatorEngine: discovers, validates, instantiates, and orchestrates indicators.
# Fully decoupled from indicator implementations — operates exclusively on descriptors.

import glob
import json
import os
import re
from typing import Callable, Optional

import pandas as pd


IND_LOG_MODULE = "IND"


class cl_IndicatorEngine:
    """
    Discovers indicator config files matching the pattern
    'ind_config_<ID>.json' inside each indicator subfolder,
    validates each one using the descriptor registered for that type,
    and instantiates the corresponding indicator via the descriptor factory.

    All type-specific knowledge (required fields, validation, instantiation)
    lives in each indicator's descriptor — this class is completely agnostic.
    """

    def __init__(self, logger_callback: Callable[[str], None]) -> None:
        self._log = logger_callback
        # {type_key: descriptor_dict}
        self._descriptors: dict[str, dict] = {}
        # {name: {"instance": ..., "ind_id": int, "type": str}}
        self._registry: dict[str, dict] = {}

    # -----------------------------------------------------------------------
    # Descriptor Registration
    # -----------------------------------------------------------------------

    def register_descriptor(self, descriptor: dict) -> None:
        """
        Registers an indicator descriptor.
        Must be called (via indicators/__init__.py) before discover_and_load().

        Parameters
        ----------
        descriptor : dict
            Must contain keys: type_key, required_fields, optional_fields,
            validate, factory, summary.
        """
        type_key = descriptor["type_key"]
        self._descriptors[type_key] = descriptor
        self._log(f"[{IND_LOG_MODULE}] Descriptor registered: '{type_key}'.")

    # -----------------------------------------------------------------------
    # Discovery & Loading
    # -----------------------------------------------------------------------

    def discover_and_load(self, indicators_dir: str) -> None:
        """
        Scans all subdirectories of indicators_dir for files matching
        'ind_config_<ID>.json' (excluding *.example files), validates each
        config against the corresponding descriptor, and registers valid indicators.

        Parameters
        ----------
        indicators_dir : str
            Absolute or relative path to the src/indicators/ directory.
        """
        self._registry.clear()

        if not self._descriptors:
            self._log(f"[{IND_LOG_MODULE}] No descriptors registered — nothing to load.")
            return

        pattern = os.path.join(indicators_dir, "**", "ind_config_*.json")
        files   = sorted(glob.glob(pattern, recursive=True))
        files   = [f for f in files if not f.endswith(".example")]

        if not files:
            self._log(f"[{IND_LOG_MODULE}] No indicator config files found in '{indicators_dir}'.")
            return

        self._log(f"[{IND_LOG_MODULE}] Found {len(files)} config file(s). Validating...")

        seen_ids:   set[int] = set()
        seen_names: set[str] = set()

        for filepath in files:
            self._load_single(filepath, seen_ids, seen_names)

        loaded = len(self._registry)
        self._log(
            f"[{IND_LOG_MODULE}] Discovery complete — "
            f"{loaded}/{len(files)} indicator(s) loaded successfully."
        )

    def _load_single(
        self,
        filepath:   str,
        seen_ids:   set,
        seen_names: set,
    ) -> None:
        filename = os.path.basename(filepath)

        # ---- 1. Parse JSON ----
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self._log(f"[{IND_LOG_MODULE}] {filename} → INVALID: could not read file ({e}).")
            return

        # ---- 2. Detect type key (ignore keys starting with '_') ----
        type_keys = [k for k in raw if not k.startswith("_") and k in self._descriptors]
        if not type_keys:
            known = list(self._descriptors.keys())
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"no recognized type key found (registered types: {known})."
            )
            return
        if len(type_keys) > 1:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"multiple type keys found ({type_keys}) — only one allowed per file."
            )
            return

        type_key   = type_keys[0]
        descriptor = self._descriptors[type_key]
        cfg        = raw[type_key]

        # ---- 3. Validate required fields and their types ----
        for field, expected_type in descriptor["required_fields"].items():
            if field not in cfg:
                self._log(
                    f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                    f"required field '{field}' is missing."
                )
                return
            if not isinstance(cfg[field], expected_type):
                self._log(
                    f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                    f"field '{field}' must be {expected_type.__name__}, "
                    f"got {type(cfg[field]).__name__}."
                )
                return

        # ---- 4. Apply optional field defaults ----
        for field, default in descriptor["optional_fields"].items():
            cfg.setdefault(field, default)

        ind_id   = cfg["ID"]
        ind_name = cfg["name"]

        # ---- 5. Validate ID matches filename ----
        match = re.search(r"ind_config_(\d+)\.json$", filename)
        if not match:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"filename does not match pattern 'ind_config_<integer>.json'."
            )
            return
        file_id = int(match.group(1))
        if file_id != ind_id:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"filename ID ({file_id}) does not match internal ID ({ind_id})."
            )
            return

        # ---- 6. Validate uniqueness of ID and name ----
        if ind_id in seen_ids:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"ID {ind_id} is already used by another indicator."
            )
            return
        if ind_name in seen_names:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"name '{ind_name}' is already used by another indicator."
            )
            return

        # ---- 7. Check enabled flag ----
        if not cfg["enabled"]:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → DISABLED: "
                f"'{ind_name}' (ID={ind_id}) skipped (enabled=false)."
            )
            return

        # ---- 8. Type-specific validation via descriptor ----
        is_valid, reason = descriptor["validate"](cfg)
        if not is_valid:
            self._log(f"[{IND_LOG_MODULE}] {filename} → INVALID: {reason}")
            return

        # ---- 9. Instantiate via descriptor factory ----
        try:
            instance = descriptor["factory"](cfg)
        except Exception as e:
            self._log(
                f"[{IND_LOG_MODULE}] {filename} → INVALID: "
                f"instantiation failed ({e})."
            )
            return

        # ---- 10. Register ----
        seen_ids.add(ind_id)
        seen_names.add(ind_name)
        self._registry[ind_name] = {
            "instance": instance,
            "ind_id":   ind_id,
            "type":     type_key,
        }
        summary = descriptor["summary"](cfg)
        self._log(
            f"[{IND_LOG_MODULE}] {filename} → OK: "
            f"{type_key} '{ind_name}' (ID={ind_id}, {summary}) loaded."
        )

    # -----------------------------------------------------------------------
    # Processing
    # -----------------------------------------------------------------------

    def process_history(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """
        Runs process_history() on every registered indicator.

        Parameters
        ----------
        df : pd.DataFrame
            Full historical candle DataFrame (columns: time, open, high, low, close).

        Returns
        -------
        dict mapping indicator name → pd.DataFrame with columns 'time' and 'value'.
        """
        results: dict[str, pd.DataFrame] = {}
        for name, entry in self._registry.items():
            try:
                results[name] = entry["instance"].process_history(df)
            except Exception as e:
                self._log(f"[{IND_LOG_MODULE}] process_history error for '{name}': {e}.")
                results[name] = pd.DataFrame(columns=["time", "value"])
        return results

    def process_tick(self, brick: pd.Series) -> dict[str, Optional[pd.Series]]:
        """
        Runs process_tick() on every registered indicator when a new candle/brick
        is completed.

        Parameters
        ----------
        brick : pd.Series
            Completed candle with fields: time, open, high, low, close.

        Returns
        -------
        dict mapping indicator name → pd.Series with fields 'time' and 'value',
        or None if the indicator returned None.
        """
        results: dict[str, Optional[pd.Series]] = {}
        for name, entry in self._registry.items():
            try:
                results[name] = entry["instance"].process_tick(brick)
            except Exception as e:
                self._log(f"[{IND_LOG_MODULE}] process_tick error for '{name}': {e}.")
                results[name] = None
        return results

    # -----------------------------------------------------------------------
    # Accessors (used by cl_GUI for chart line setup)
    # -----------------------------------------------------------------------

    def get_color(self, name: str) -> Optional[str]:
        """Returns the color string for the given indicator name, or None if not found."""
        entry = self._registry.get(name)
        if entry is None:
            return None
        return entry["instance"].color

    def registered_names(self) -> list[str]:
        """Returns a list of all registered (active) indicator names."""
        return list(self._registry.keys())

    def is_empty(self) -> bool:
        """Returns True if no indicators are registered."""
        return len(self._registry) == 0