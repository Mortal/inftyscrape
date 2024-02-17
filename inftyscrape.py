import asyncio
import json
import random
import re
from typing import TypedDict

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
        if response.status == 403 and b"_cf_chl_opt" in s:
            print("You got hit with a Cloudflare robot check! Go to https://neal.fun/infinite-craft/ and play for a bit", flush=True)
            raise SystemExit(43)
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
        await go_explore(context)


async def go_explore(context: tuple[aiohttp.ClientSession, Database]) -> None:
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
            if re.search(r'[0-9]', item):
                # Don't do repeated doubling if there's numbers involved
                return

    seen_addition = set()

    async def repeated_addition(first: str, second: str) -> None:
        while (first, second) not in seen_addition:
            seen_addition.add((first, second))
            result = await lookup(context, first, second)
            if result not in xset:
                xset.add(result)
                xlist.append(result)
                await repeated_doubling(result)
            if re.search(r'[0-9]', first):
                if re.search(r'[0-9]', second) or re.search(r'[0-9]', result):
                    # Don't do repeated addition if there's numbers involved
                    return
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

    rng = random.Random(seed)
    while True:
        await explore(rng.choice(xlist), rng.choice(xlist))


if __name__ == "__main__":
    asyncio.run(main())
