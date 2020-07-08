import logging
import sys
import os

def configure_log(wd: str) -> None:
    logfile = os.path.join(wd, 'events.log')
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    log_format = "%(asctime)s [%(levelname)s] : %(message)s"
    date_format = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(formatter)
    ch.setLevel(logging.WARNING)
    log.addHandler(ch)
    fh = logging.FileHandler(logfile)
    fh.setFormatter(formatter)
    log.addHandler(fh)