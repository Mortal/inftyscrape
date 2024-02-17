import json
import os


default_elements = {"Water": "💧", "Fire": "🔥", "Wind": "🌬️", "Earth": "🌍"}


def main() -> None:
    edgelists: dict[str, list[tuple[str, str]]] = {}
    with open("connections.json") as fp:
        for line in fp:
            if line.startswith("["):
                a, b, c = json.loads(line)
                edgelists.setdefault(a, []).append((b, c))
                edgelists.setdefault(b, []).append((a, c))
    src = {s: (s, s) for s in default_elements}
    bfs = list(src)
    order = {s: i for i, s in enumerate(bfs)}
    i = 0
    while i < len(bfs):
        a = bfs[i]
        for b, c in edgelists.get(a, ()):
            if b in order and order[b] <= i and c not in src:
                order[c] = len(order)
                src[c] = a, b
                bfs.append(c)
                try:
                    print(json.dumps([min(a, b), max(a, b), c], ensure_ascii=False))
                except BrokenPipeError:
                    os._exit(0)
        i += 1


if __name__ == "__main__":
    main()
