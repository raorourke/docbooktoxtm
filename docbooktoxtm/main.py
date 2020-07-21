import os
from typing import Optional

import typer

from docbooktoxtm import __version__
from docbooktoxtm.bookclasses import BookInfo, Book
from docbooktoxtm.functions import get_zip
from docbooktoxtm.logconfig import configure_log

app = typer.Typer(help='Utility for prepping DocBook XML packages for use as XTM source files.')


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context,
         version: bool = typer.Option(
    None, '-v', '-V', '--version', help='Show current version'
)
) -> None:
    if version:
        typer.echo(f"docbooktoxtm {__version__}")
    elif ctx.invoked_subcommand is None:
        typer.echo('Try "docbooktoxtm --help" for help.')


@app.command(help='Reorganizes files for more efficient parsing in XTM.')
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


@app.command(help='Restores original file structure of target files from XTM.')
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
    typer.echo(f"Source file ({source_fname}) restructured successfully!")
    typer.echo(f"Unsourced file name: {unsourced_fname}")


if __name__ == "__main__":
    app()
