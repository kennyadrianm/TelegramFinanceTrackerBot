"""Module execution entry point for python -m app."""

import asyncio
from app.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

