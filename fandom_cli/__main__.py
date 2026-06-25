"""Allow ``python -m fandom_cli`` as a shortcut for ``python -m fandom_cli.cli``."""

from fandom_cli.cli import main

if __name__ == "__main__":
    main()
