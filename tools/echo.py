"""Echo tool: returns the given message in a structured response."""


def execute(message: str = "") -> dict[str, str]:
    """Echo the input message."""
    return {"echoed": message}
