#!/usr/bin/env python3

import sys

from . import functions as rhserv

if __name__ == "__main__":
    try:
        course = sys.argv[1]
        release = rhserv.get_latest_release(course)
        source_file = rhserv.get_zip(release)
        rhserv.unsource(source_file)
    except IndexError:
        print(f"Must indicate course number as first argument.")