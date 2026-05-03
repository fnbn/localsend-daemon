import argparse
import logging
from localsend_daemon.server import run


def main() -> None:
    parser = argparse.ArgumentParser(description="LocalSend daemon")
    parser.add_argument("config", nargs="?", default="localsend-daemon.toml")
    parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: ERROR)",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(levelname)s: %(message)s",
    )
    run(args.config, log_level=args.log_level)


if __name__ == "__main__":
    main()
