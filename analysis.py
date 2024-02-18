import json


def main() -> None:
    gives_self: dict[str, list[str]] = {}
    gives_other: dict[str, list[str]] = {}
    gives_something: dict[str, list[tuple[str, str]]] = {}
    from_something: dict[str, list[tuple[str, str]]] = {}
    double = {}
    with open("connections.json") as fp:
        for line in fp:
            a, b, c = json.loads(line)
            if a == b:
                double[a] = c
            elif a == c:
                gives_self.setdefault(a, []).append(b)
                gives_other.setdefault(b, []).append(a)
            elif b == c:
                gives_other.setdefault(a, []).append(b)
                gives_self.setdefault(b, []).append(a)
            else:
                gives_something.setdefault(a, []).append((b, c))
                gives_something.setdefault(b, []).append((a, c))
                from_something.setdefault(c, []).append((a, b))
    words = {*gives_self, *gives_other, *gives_something, *from_something, *double}
    assert "-" not in words
    for w in sorted(words):
        p = len(gives_self.get(w, ()))
        q = len(gives_other.get(w, ()))
        r = len(gives_something.get(w, ()))
        s = len(from_something.get(w, ()))
        combinations = p + q + r
        row = (
            "'" + w,
            int(double[w] == w) if w in double else "-",
            "'" + double[w] if w in double else "-",
            combinations,
            s,
            p / combinations if combinations else "-",
            q / combinations if combinations else "-",
            r / combinations if combinations else "-",
            s / combinations if combinations else "-",
        )
        print("\t".join(map(str, row)))


if __name__ == "__main__":
    main()
