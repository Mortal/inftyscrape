import asyncio
import cmd
import json
import random
import re
import readline
from typing import TypedDict

import aiohttp

from aioreadline import rlprint as print


default_elements = {"Water": "💧", "Fire": "🔥", "Wind": "🌬️", "Earth": "🌍"}

number_names = """one two three four five six seven eight nine ten
eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen
twenty thirty forty fifty sixty seventy eighty ninety hundred thousand
million""".split()


seed = 14354


class Pair(TypedDict):
    result: str
    emoji: str
    isNew: bool


async def get_infinite_craft_pair(
    session: aiohttp.ClientSession, first: str, second: str
) -> Pair:
    assert first <= second
    url = "https://neal.fun/api/infinite-craft/pair"
    params = {"first": first, "second": second}
    headers = {
        "Referer": "https://neal.fun/infinite-craft/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    }
    while True:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    print(
                        f"HTTP {response.status} for GET {url}?first={first}&second={second}",
                        flush=True,
                    )
                s = await response.read()
                if response.status == 403 and b"_cf_chl_opt" in s:
                    print("You got hit with a Cloudflare robot check! Go to https://neal.fun/infinite-craft/ and play for a bit", flush=True)
                    raise SystemExit(43)
                if response.status != 200:
                    print(s.decode("utf-8", errors="replace"), flush=True)
                    response.raise_for_status()
                break
        except asyncio.TimeoutError:
            print(
                f"TimeoutError for GET {url}?first={first}&second={second}",
                flush=True,
            )
    try:
        return json.loads(s)
    except Exception:
        print(
            f"JSON decode exception for GET {url}?first={first}&second={second}",
            flush=True,
        )
        print(s.decode("utf-8", errors="replace"), flush=True)
        raise


class Database(TypedDict):
    emoji: dict[str, str]
    connections: dict[tuple[str, str], str]


def load_database() -> Database:
    emoji: dict[str, str] = {}
    connections: dict[tuple[str, str], str] = {}
    try:
        with open("elements.json") as fp:
            for line in fp:
                if not line.startswith("["):
                    continue
                e, thing, *isNew = json.loads(line)
                emoji[thing] = e
    except FileNotFoundError:
        emoji = {**default_elements}
        with open("elements.json", "x") as ofp:
            for thing, e in emoji.items():
                ofp.write(json.dumps([e, thing], ensure_ascii=False) + "\n")
    try:
        with open("connections.json") as fp:
            connections = {
                (a, b): c
                for line in fp
                if line.startswith("[")
                for a, b, c in [json.loads(line)]
            }
    except FileNotFoundError:
        connections = {}
    return {
        "emoji": emoji,
        "connections": connections,
    }


async def lookup(
    context: tuple[aiohttp.ClientSession, Database], first: str, second: str
) -> str:
    session, database = context
    first, second = min(first, second), max(first, second)
    if (first, second) in database["connections"]:
        r = database["connections"][first, second]
        # print(
        #     f"     {database['emoji'][r]} {r} = {first} + {second}"
        # )
        return r
    result = await get_infinite_craft_pair(session, first, second)
    database["connections"][first, second] = result["result"]
    with open("connections.json", "a") as ofp:
        ofp.write(
            json.dumps([first, second, result["result"]], ensure_ascii=False) + "\n"
        )
    if result["result"] not in database["emoji"]:
        if result.get("isNew"):
            print(
                f"NEW: {result['emoji']} {result['result']} = {first} + {second}",
                flush=True,
            )
            database["emoji"][result["result"]] = result["emoji"]
            with open("newconnections.json", "a") as ofp:
                ofp.write(
                    json.dumps([first, second, result], ensure_ascii=False) + "\n"
                )
        else:
            print(
                f"===> {result['emoji']} {result['result']} = {first} + {second}",
                flush=True,
            )
            database["emoji"][result["result"]] = result["emoji"]
        with open("elements.json", "a") as ofp:
            ofp.write(
                json.dumps([result["emoji"], result["result"]], ensure_ascii=False)
                + "\n"
            )
    else:
        print(
            f"---> {result['emoji']} {result['result']} = {first} + {second}",
            flush=True,
        )
    await asyncio.sleep(0.2)
    return result["result"]


async def main():
    database = load_database()
    async with aiohttp.ClientSession() as session:
        context = (session, database)
        queue: list[tuple[str, str]] = []
        go_explore_task = asyncio.create_task(go_explore(context, queue))
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, Shell(database, queue).cmdloop)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
        except asyncio.CancelledError:
            print("Please use CTRL-D to exit instead of CTRL-C")
        go_explore_task.cancel()
        try:
            await go_explore_task
        except asyncio.CancelledError:
            pass


number_name_regex = re.compile("|".join(f"\\b{n}\\b" for n in number_names), re.I)


def should_skip(s: str) -> bool:
    return bool(re.search(r'[0-9]', s) or len(re.findall(number_name_regex, s)) >= 2)


async def go_explore(context: tuple[aiohttp.ClientSession, Database], queue: list[tuple[str, str]]) -> None:
    xlist = list(default_elements)
    xset = set(xlist)
    seen_doubling = set()
    in_queue = False

    async def repeated_doubling(item: str) -> None:
        while item not in seen_doubling:
            if queue and not in_queue:
                return
            seen_doubling.add(item)
            item = await lookup(context, item, item)
            if item not in xset:
                xset.add(item)
                xlist.append(item)
            if re.search(r'[0-9]', item):
                # Don't do repeated doubling if there's numbers involved
                return

    seen_addition = set()

    async def repeated_addition(first: str, second: str) -> None:
        while (first, second) not in seen_addition:
            if queue and not in_queue:
                return
            seen_addition.add((first, second))
            result = await lookup(context, first, second)
            if result not in xset:
                xset.add(result)
                xlist.append(result)
                await repeated_doubling(result)
            if should_skip(first):
                if should_skip(second) or should_skip(result):
                    # Don't do repeated addition if there's numbers involved
                    return
            first = result

    async def explore(first: str, second: str) -> None:
        if queue and not in_queue:
            return
        if first == second:
            await repeated_doubling(first)
            return
        result = await lookup(context, first, second)
        if result not in xset:
            xset.add(result)
            xlist.append(result)
            await repeated_doubling(result)
        if result not in (first, second):
            await repeated_addition(result, second)
            await repeated_addition(result, first)

    rng = random.Random(seed)
    while True:
        while queue:
            in_queue = True
            a, b = queue.pop(0)
            await explore(a, b)
            in_queue = False
        first = rng.choice(xlist)
        second = rng.choice(xlist)
        if should_skip(first) or should_skip(second):
            continue
        await explore(first, second)


class Shell(cmd.Cmd):
    def __init__(self, database: Database, queue: list[tuple[str, str]], prompt="] "):
        super().__init__()
        self.prompt = prompt
        self.database = database
        self.queue = queue
        readline.set_completer_delims(" ")

    def default(self, command: str):
        if command.count("+") != 1:
            print("Please enter two words separated by plus, i.e. FOO + BAR")
            return
        a, b = command.split("+")
        a = a.strip()
        b = b.strip()
        if a not in self.database["emoji"]:
            print(f"Not yet discovered: '{a}'")
            return
        if b not in self.database["emoji"]:
            print(f"Not yet discovered: '{b}'")
            return
        self.queue.append((a, b))

    def emptyline(self):
        pass

    def _complete(self, text, line, start_index, end_index):
        pref = line[:end_index].split("+")[-1].lstrip()
        n = len(pref) - len(text)
        # print(f"{text=} {line=} {start_index=} {end_index=}")
        return sorted(
            k[n:] for k in self.database["emoji"] if k.startswith(pref)
        )

    def completenames(self, text, line, start_index, end_index):
        return self._complete(text, line, start_index, end_index)

    def completedefault(self, text, line, start_index, end_index):
        return self._complete(text, line, start_index, end_index)

    def do_exit(self, _):
        print("Press CTRL-D to exit")

    def do_EOF(self, _):
        """Exit by the Ctrl-D shortcut."""
        print("")
        return True


if __name__ == "__main__":
    asyncio.run(main())
