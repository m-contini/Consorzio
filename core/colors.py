"""
Utility per la formattazione del testo nel terminale tramite codici colore ANSI.
"""

from pathlib import Path

from colorama import Fore


def red(text: str | Path) -> str:
    return f"{Fore.RED}{text}{Fore.RESET}"


def green(text: str | Path) -> str:
    return f"{Fore.GREEN}{text}{Fore.RESET}"


def yellow(text: str | Path) -> str:
    return f"{Fore.YELLOW}{text}{Fore.RESET}"


def cyan(text: str | Path) -> str:
    return f"{Fore.CYAN}{text}{Fore.RESET}"


def magenta(text: str | Path) -> str:
    return f"{Fore.MAGENTA}{text}{Fore.RESET}"


def white(text: str | Path) -> str:
    return f"{Fore.WHITE}{text}{Fore.RESET}"


def blue(text: str | Path) -> str:
    return f"{Fore.BLUE}{text}{Fore.RESET}"
