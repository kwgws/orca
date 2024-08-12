import click

from . import config
from .model import create_tables
from .tasks import start_load_documents


@click.group()
def cli():
    """Command line interface for the application."""
    pass


@cli.command
def reset():
    """Reset database, create metadata.

    This needs to be run at least once before anything else happens.
    """
    click.echo(f"Deleting databsae at {config.DATABASE_PATH}")
    config.DATABASE_PATH.unlink()
    click.echo(f"Creating database and metadata at {config.DATABASE_PATH}")
    create_tables()
    click.echo("Ok!")


@cli.command
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
def load(path):
    """Load documents from the given PATH into the database."""
    click.echo(f"Starting to load documents from {path}")
    start_load_documents(path)


if __name__ == "__main__":
    cli()
