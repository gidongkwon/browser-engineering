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
    import sys
    load(URL(sys.argv[1]))


if __name__ == "__main__":
    main()
