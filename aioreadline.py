import ctypes
import readline


libreadline = ctypes.CDLL("libreadline.so")


def rlprint(s: str, *, flush: bool = True) -> None:
    print(f"\r\x1b[K{s}\n", end="", flush=True)
    libreadline.rl_on_new_line()
    readline.redisplay()
