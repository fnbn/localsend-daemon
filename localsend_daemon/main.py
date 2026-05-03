import sys
from localsend_daemon.server import run


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "localsend-daemon.toml"
    run(config_path)


if __name__ == "__main__":
    main()
