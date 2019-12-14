import datetime
import time


def NowDayZeroTime():
    time_tuple = datetime.datetime.now().date().timetuple()

    time_stamp = time.mktime(time_tuple)

    time_date = datetime.datetime.now().date()

    ZeroTime_UTC = datetime.datetime.utcfromtimestamp(time_stamp)

    ZeroTime_local = datetime.datetime.fromtimestamp(time_stamp)

    return {
        "time_tuple": time_tuple,
        "time_stamp": time_stamp,
        "time_date": time_date,
        "ZeroTime_UTC": ZeroTime_UTC,
        "ZeroTime_local": ZeroTime_local
    }
