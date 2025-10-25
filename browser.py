from url import URL


def show(body: str):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")


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
