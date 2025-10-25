from url import URL
from consts import entities


def lookahead(string: str, index: int, count: int):
    string_length = len(string)
    assert index >= 0 and index < string_length
    assert count > 0

    end = min(index + count, string_length)
    return string[index:end]


def show(body: str):
    in_tag = False
    index = 0
    while index < len(body):
        char = body[index]
        if char == "&":
            # hack wow
            maybe_entity = lookahead(body, index, 4)
            if maybe_entity in entities.keys():
                print(entities[maybe_entity], end="")
                index += len(maybe_entity)
                continue
        if char == "<":
            in_tag = True
        elif char == ">":
            in_tag = False
        elif not in_tag:
            print(char, end="")
        index += 1
    print()


def load(url: URL):
    body = url.request()
    show(body)


def main():
    import os, sys

    url = f"file:///{os.path.dirname(__file__)}/about.txt"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    load(URL(url))


if __name__ == "__main__":
    main()
