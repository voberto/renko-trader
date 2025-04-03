from datetime import datetime


def tstamp_local_get():
    return(datetime.now().strftime('%Y.%m.%d %H:%M:%S.%f')[:-3])
