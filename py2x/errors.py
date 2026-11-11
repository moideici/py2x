class Unsupported(Exception):
    """Construction Python hors du sous-ensemble supporté (message avec numéro de ligne)."""

    def __init__(self, msg, node=None):
        line = getattr(node, "lineno", None)
        super().__init__(f"ligne {line} : {msg}" if line else msg)
