"""
Utility per la formattazione del testo nel terminale tramite codici colore ANSI.
"""

from pathlib import Path

from colorama import Fore
from .const import IS_CLOUD

def red(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.RED}{text}{Fore.RESET}"


def green(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.GREEN}{text}{Fore.RESET}"


def yellow(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.YELLOW}{text}{Fore.RESET}"


def cyan(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.CYAN}{text}{Fore.RESET}"


def magenta(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.MAGENTA}{text}{Fore.RESET}"


def white(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.WHITE}{text}{Fore.RESET}"


def blue(text: str | Path) -> str:
    if IS_CLOUD:
        return f"{text}"
    return f"{Fore.BLUE}{text}{Fore.RESET}"
