import sys

from .functions import resource, unsource, BookInfo, get_book_info_from_zip, get_latest_release, get_zip

if __name__ == "__main__":
    if sys.argv[1] == 'resource':
        target_file = sys.argv[2]
        book = BookInfo(**get_book_info_from_zip(target_file))
        course = book.invpartnumber
        release = get_latest_release(course)
        source_file = get_zip(release)
        resource(source_file, target_file)
    if sys.argv[1] == 'unsource':
        course = sys.argv[2]
        print(course)
        release = get_latest_release(course)
        source_file = get_zip(release)
        unsource(source_file)