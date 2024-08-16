from pathlib import Path

import click

from orca.app import reset_db, start_load, start_search


@click.group()
def cli():
    """Command line interface for the application."""
    pass


@cli.command
def reset():
    click.echo("Resetting database...", nl=False)
    reset_db()
    click.echo("done!")


@cli.command
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
def load(path):
    path = Path(path)
    subdirs = len([p for p in path.iterdir() if p.is_dir()])
    click.echo(f"Found {subdirs} albums in {path}")
    click.echo("Starting load...", nl=False)
    start_load(path)
    click.echo("ok!")


@cli.command
@click.argument("search_str")
def search(search_str):
    if not search_str or search_str == "":
        click.echo("No search string entered!")
        return

    click.echo(f"Starting search for `{search_str}`...", nl=False)
    start_search(search_str)
    click.echo("ok!")
