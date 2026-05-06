"""Спільні текстові утиліти."""


def esc(text: str) -> str:
    """MarkdownV2 екранування для довільного тексту."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
