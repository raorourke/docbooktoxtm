#!/usr/bin/env python3

import sys

from weautomate.docbooktoxtm.docbooktoxtm import functions as rhserv

if __name__ == "__main__":
    try:
        target_file = sys.argv[1]
        book = rhserv.BookInfo(**rhserv.get_book_info_from_zip(target_file))
        course = book.invpartnumber
        release = rhserv.get_latest_release(course)
        source_file = rhserv.get_zip(release)
        rhserv.unsource(source_file, target_file)
    except IndexError:
        print(f"Must indicate course number as first argument.")
