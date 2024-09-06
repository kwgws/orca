import asyncio
from pathlib import Path

import click
import uvicorn

from orca import app, config
from orca.model.db import init_async_engine
from orca.server import api as wsgi_app


@click.group()
def cli():
    """Orca Document Query 🐋"""
    pass


@cli.command()
@click.option("--uri", default=None, help="Database connection URI")
@click.option(
    "--path",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Path to the SQL file",
)
def init_db(uri, path):
    """Initialize the SQL database."""
    uri = uri or config.db.uri
    path = Path(path or config.db.sql_path)

    print("Initializing database with the following settings:")
    print(f"URI: {uri}")
    print(f"SQL Path: {path}")

    asyncio.run(app.init_database(uri, path))
    print("Database initialization complete! 🌊")


@cli.command()
@click.option(
    "--data-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Base data path for albums",
)
@click.option("--batch-name", default=None, help="Name of the batch to import")
@click.option(
    "--index-path",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    default=None,
    help="Path to the search index",
)
def import_albums(data_path, batch_name, index_path):
    """Import albums and documents into the system."""
    data_path = Path(data_path or config.data_path)
    batch_name = batch_name or config.batch_name
    index_path = Path(index_path or config.index_path)

    print("Starting album import...")
    print(f"Data Path: {data_path}")
    print(f"Batch Name: {batch_name}")
    print(f"Index Path: {index_path}")

    asyncio.run(app.import_albums(data_path, batch_name, index_path))
    print("Album import complete! 📚")


@cli.command()
@click.argument("search_str")
@click.option(
    "--data-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Base data path",
)
@click.option(
    "--index-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    default=None,
    help="Path to the search index",
)
@click.option(
    "--megadoc-types", default=None, help="Comma-separated list of megadoc types"
)
def search(search_str, data_path, index_path, megadoc_types):
    """Search and create megadocs from the results."""
    data_path = Path(data_path or config.data_path)
    index_path = Path(index_path or config.index_path)
    megadoc_types = (
        tuple(megadoc_types.split(",")) if megadoc_types else config.megadoc_types
    )

    print("Searching...")
    print(f"Search String: {search_str}")
    print(f"Data Path: {data_path}")
    print(f"Index Path: {index_path}")
    print(f"Megadoc Types: {megadoc_types}")

    asyncio.run(
        app.search_to_megadocs(search_str, data_path, index_path, megadoc_types)
    )
    print("Megadoc creation complete! 📚")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host IP for the debug server")
@click.option("--port", default=8000, help="Port number for the debug server")
def debug(host, port):
    """Run the debug server."""
    print(f"Launching debug server at {host}:{port} 🖥️")
    asyncio.run(init_async_engine())
    uvicorn.run(wsgi_app, host=host, port=port)


if __name__ == "__main__":
    cli()
