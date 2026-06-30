# indicators/__init__.py
# Single wiring point: registers all indicator descriptors into cl_IndicatorEngine.
# To add a new indicator type, import its descriptor here and add one register call.

from .indicators import cl_IndicatorEngine
from .ind_MA.ind_MA import IND_MA_DESCRIPTOR


def build_indicator_engine(logger_callback) -> cl_IndicatorEngine:
    """
    Factory function: instantiates cl_IndicatorEngine and registers
    all known indicator descriptors before returning it.

    Parameters
    ----------
    logger_callback : Callable[[str], None]
        Logger function passed through to the engine.

    Returns
    -------
    cl_IndicatorEngine ready for discover_and_load().
    """
    engine = cl_IndicatorEngine(logger_callback)
    engine.register_descriptor(IND_MA_DESCRIPTOR)
    # engine.register_descriptor(IND_RSI_DESCRIPTOR)  # example: next indicator
    return engine