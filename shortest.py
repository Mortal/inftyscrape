import json


default_elements = {"Water": "💧", "Fire": "🔥", "Wind": "🌬️", "Earth": "🌍"}


def main() -> None:
    depth = {s: 0 for s in default_elements}
    while True:
        try:
            a, b, c = json.loads(input())
        except EOFError:
            break
        depth[c] = max(depth[a], depth[b]) + 1
    with open("connections.json") as fp:
        connections = [
            (a, b, c)
            for line in fp
            if line.startswith("[")
            for a, b, c in [json.loads(line)]
        ]
    while True:
        imp = 0
        for a, b, c in connections:
            d = max(depth[a], depth[b]) + 1
            if depth[c] > d:
                depth[c] = d
                imp += 1
        if not imp:
            break
    seen = set()
    for a, b, c in connections:
        d = max(depth[a], depth[b]) + 1
        if depth[c] == d and c not in seen:
            seen.add(c)
            print(json.dumps([a, b, c], ensure_ascii=False))


if __name__ == "__main__":
    main()
