import asyncio
import json
import random
from typing import Awaitable, Callable, Sequence, TypedDict

import aiohttp


default_elements = {"Water": "💧", "Fire": "🔥", "Wind": "🌬️", "Earth": "🌍"}


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
    headers = {"Referer": "https://neal.fun/infinite-craft/"}
    async with session.get(url, params=params, headers=headers) as response:
        if response.status != 200:
            print(
                f"HTTP {response.status} for GET {url}?first={first}&second={second}",
                flush=True,
            )
        s = await response.read()
        if response.status != 200:
            print(s.decode("utf-8", errors="replace"), flush=True)
            response.raise_for_status()
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
    print("", end="", flush=True)
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
        await mode4(context)


async def mode1(context: tuple[aiohttp.ClientSession, Database]) -> None:
    rng = random.Random(seed)
    search_space = list(default_elements)
    found = set(search_space)
    seen = set()
    first = rng.choice(search_space)
    second = rng.choice(search_space)
    while True:
        seen.add((first, second))
        result = await lookup(context, first, second)
        if result not in found:
            found.add(result)
            search_space.append(result)
        if first == result or (result, second) in seen or (result, result) in seen:
            first = rng.choice(search_space)
            second = rng.choice(search_space)
            continue
        if first == second and (result, result) not in seen:
            first = second = result
            continue
        first = result
        # mode = rng.choice(("new", "addition", "doubling"))
        # if mode == "new":
        #     first = rng.choice(search_space)
        #     second = rng.choice(search_space)
        # elif mode == "addition":
        #     first = result
        # elif mode == "doubling":
        #     first = second = result


async def mode2(context: tuple[aiohttp.ClientSession, Database]) -> None:
    rng = random.Random(seed)
    search_space = list(default_elements)
    found = set(search_space)
    while True:
        first = rng.choice(search_space)
        mode = rng.choice(("addition", "doubling"))
        if mode == "doubling":
            second = first
        else:
            second = rng.choice(search_space)
        seen = {first}
        if first == second:
            # Repeated addition of second to first
            while True:
                first = await lookup(context, first, second)
                if first in seen:
                    break
                if first not in found:
                    found.add(first)
                    search_space.append(first)
                seen.add(first)
        else:
            # Repeated doubling
            while True:
                first = await lookup(context, first, first)
                if first in seen:
                    break
                if first not in found:
                    found.add(first)
                    search_space.append(first)
                seen.add(first)


def init_explore(context: tuple[aiohttp.ClientSession, Database]) -> tuple[Sequence[str], Callable[[str, str], Awaitable[None]]]:
    xlist = list(default_elements)
    xset = set(xlist)
    seen_doubling = set()

    async def repeated_doubling(item: str) -> None:
        while item not in seen_doubling:
            seen_doubling.add(item)
            item = await lookup(context, item, item)
            if item not in xset:
                xset.add(item)
                xlist.append(item)

    seen_addition = set()

    async def repeated_addition(first: str, second: str) -> None:
        while (first, second) not in seen_addition:
            seen_addition.add((first, second))
            result = await lookup(context, first, second)
            if result not in xset:
                xset.add(result)
                xlist.append(result)
                await repeated_doubling(result)
            first = result

    async def explore(first: str, second: str) -> None:
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

    return xlist, explore


async def mode3(context: tuple[aiohttp.ClientSession, Database]) -> None:
    xlist, explore = init_explore(context)
    for i in range(1_000_000_000):
        for j in range(i + 1):
            await explore(xlist[i], xlist[j])


async def mode4(context: tuple[aiohttp.ClientSession, Database]) -> None:
    xlist, explore = init_explore(context)
    rng = random.Random(seed)
    while True:
        await explore(rng.choice(xlist), rng.choice(xlist))


if __name__ == "__main__":
    asyncio.run(main())
