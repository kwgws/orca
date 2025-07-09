import asyncio

from .interfaces.cli import repl

if __name__ == "__main__":
    asyncio.run(repl())
