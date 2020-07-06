from typing import Optional
import os
import sys
import typer
import logging

from docbooktoxtm.bookclasses import BookInfo, Book
from docbooktoxtm.functions import get_zip

app = typer.Typer(help='Utility for prepping DocBook XML packages for use as XTM source files.')

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

@app.command(help='Restructures source file structure for more efficient parsing in XTM.')
def resource(target_fname: str = typer.Argument(..., help='name of target .zip package')) -> None:
    """
    This function restores the XML source files to their original structure, as
    well as restores any files that had been removed from scope during prep.
    :param target_fname: Name of target .ZIP package. This file will
     be processed in current working directory.
    :return target_file: Name of target restructured .ZIP package.
    """
    configure_log(os.getcwd())
    bi = BookInfo.from_zipf(target_fname)
    source_fname = get_zip(bi.course, bi.release_tag)
    book = Book(source_fname, target_fname)
    resourced_fname = book()
    typer.echo("Target file structure restored successfully!")
    typer.echo(f"Resourced file name: {resourced_fname}")


@app.command(help='Restores target files exported from XTM to original source file structure.')
def unsource(course: str = typer.Argument(..., help='course name or name of source .zip package'),
             release_tag: Optional[str] = typer.Option(
                 None, '-r', '--release-tag', help='optional GitHub release tag'
             ),
             ) -> None:
    """
    This function reorganizes the XML source files so that XTM will parse them
    in the same order as they appear in the published PDF.
    :param course: Course number to be prepped, e.g. RH124, CL310, DO180.
    :param release_tag: Indicates a specific release to download. Default is
    None and will result in the most recent release of the highest version number.
    :return zip_filename: Name of restructured .ZIP package that is
    ready to be uploaded to XTM for analysis.
    """
    configure_log(os.getcwd())
    source_fname = course if os.path.isfile(course) else get_zip(course, release_tag)
    book = Book(source_fname)
    unsourced_fname = book()
    typer.echo(f"Source file ({source_fname}) structure restructured successfully!")
    typer.echo(f"Unsourced file name: {unsourced_fname}")


if __name__ == "__main__":
    app()
