import argparse
import json


parser = argparse.ArgumentParser()
parser.add_argument("word", nargs="+")


def main() -> None:
    args = parser.parse_args()
    bt: dict[str, tuple[str, str]] = {}

    def visit(c: str, seen: set[str]) -> None:
        if c not in bt:
            return
        a, b = bt[c]
        if a not in seen:
            seen.add(a)
            visit(a, seen)
        if b not in seen:
            seen.add(b)
            visit(b, seen)
        print(json.dumps([a, b, c], ensure_ascii=False))

    words = set(args.word)
    seen: set[str] = set()
    while True:
        try:
            a, b, c = json.loads(input())
        except EOFError:
            break
        bt[c] = a, b
        if c in words:
            visit(c, seen)


if __name__ == "__main__":
    main()
