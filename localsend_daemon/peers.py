class PeerRegistry:
    """Maps peer source IP to their announced server port, for fingerprint extraction."""

    def __init__(self) -> None:
        self._peers: dict[str, int] = {}

    def register(self, ip: str, port: int) -> None:
        self._peers[ip] = port

    def get_port(self, ip: str) -> int | None:
        return self._peers.get(ip)
