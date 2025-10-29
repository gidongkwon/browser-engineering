from tkinter import PhotoImage
from tkinter.constants import BOTH
from url import URL
from consts import entities
import tkinter
import tkinter.font
import platform
import regex
import argparse

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
SCROLLBAR_WIDTH = 10


class Browser:
    emoji_pattern = regex.compile(r"\p{Extended_Pictographic}", regex.UNICODE)
    emoji_image_cache: dict[str, PhotoImage] = {}

    # identifies RTL letter runs (R, AL) with combining marks
    rtl_pattern = regex.compile(
        r"(?:[\p{bc=R}\p{bc=AL}](?:[\p{M}\p{bc=R}\p{bc=AL}])*)",
        regex.UNICODE,
    )

    def __init__(self, direction="ltr"):
        self.direction = direction
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.document_width = WIDTH
        self.document_height = HEIGHT

        self.canvas.pack(fill=BOTH, expand=True)
        self.scroll_y = 0

        # Scroll events
        self.window.bind("<Down>", self.scroll)
        if platform.system() == "Linux":
            self.window.bind("<Button-4>", self.handle_linux_scrollup)
            self.window.bind("<Button-5>", self.handle_linux_scrolldown)
        else:
            self.window.bind("<MouseWheel>", self.handle_wheel)

        # Resize event
        self.window.bind("<Configure>", self.handle_configure)

    def load(self, url: URL):
        body = url.request()
        self.text = lex(body)
        self.layout(self.text)

        self.font = tkinter.font.Font(family="Noto Sans KR")
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll_y + self.document_height:
                continue
            if y + VSTEP < self.scroll_y:
                continue
            if self.emoji_pattern.match(c):
                if c not in self.emoji_image_cache:
                    self.emoji_image_cache[c] = PhotoImage(
                        file=f"openmoji/{format(ord(c), '04X')}.png"
                    ).subsample(3)
                self.canvas.create_image(
                    x,
                    y - self.scroll_y,
                    image=self.emoji_image_cache[c],
                )
            else:
                self.canvas.create_text(x, y - self.scroll_y, text=c, font=self.font)

        # Scrollbar
        if self.needs_scrollbar():
            # Background
            bar_x = self.document_width
            self.canvas.create_rectangle(
                bar_x,
                0,
                bar_x + SCROLLBAR_WIDTH,
                self.document_height,
                fill="#aaaaaa",
                outline="",
            )
            # Bar
            scroll_bottom = self.scroll_y_range[1]
            bar_y = self.scroll_y / scroll_bottom * self.document_height
            bar_height = self.document_height**2 / scroll_bottom
            self.canvas.create_rectangle(
                bar_x,
                bar_y,
                bar_x + SCROLLBAR_WIDTH,
                bar_y + bar_height,
                fill="blue",
            )

    def scroll(self, delta=SCROLL_STEP, multiplier=1):
        self.scroll_y += delta * multiplier
        self.scroll_y = max(
            self.scroll_y_range[0],
            min(self.scroll_y, self.scroll_y_range[1] - self.document_height),
        )
        self.draw()

    def handle_wheel(self, e: tkinter.Event):
        delta: int
        multiplier: int
        match platform.system():
            case "Windows":
                delta = e.delta
                multiplier = 1
            case "Darwin":
                # On macOS, e.delta is scaled by 1: https://wiki.tcl-lang.org/page/mousewheel
                delta = SCROLL_STEP
                multiplier = -1
            case _:
                delta = SCROLL_STEP
                multiplier = 1

        self.scroll(delta, multiplier)

    def handle_linux_scrollup(self, e):
        self.scroll(multiplier=-1)

    def handle_linux_scrolldown(self, e):
        self.scroll(multiplier=1)

    def handle_configure(self, e: tkinter.Event):
        self.document_width, self.document_height = e.width, e.height
        if self.needs_scrollbar():
            self.document_width -= SCROLLBAR_WIDTH
        self.layout(self.text)
        self.scroll(delta=0)  # redraw + scroll clipping

    def layout(self, text: str):
        self.display_list: list[tuple[int, int, str]] = []
        is_ltr = self.direction == "ltr"
        LINE_START_X = HSTEP if is_ltr else self.document_width - HSTEP
        CHAR_DELTA = HSTEP if is_ltr else -HSTEP
        cursor_x = LINE_START_X
        cursor_y = VSTEP

        if not is_ltr:
            text = self.reorder_text_for_rtl(text)

        for c in text:
            if c == "\n":
                cursor_y += int(VSTEP * 1.2)
                cursor_x = LINE_START_X
                continue

            self.display_list.append((cursor_x, cursor_y, c))
            cursor_x += CHAR_DELTA

            if (is_ltr and cursor_x >= self.document_width - HSTEP) or (
                not is_ltr and cursor_x <= HSTEP
            ):
                cursor_y += VSTEP
                cursor_x = LINE_START_X

        # top to top
        self.scroll_y_range = (0, self.display_list[-1][1])

    def reorder_text_for_rtl(self, text: str) -> str:
        # Heuristic bidi reordering for RTL paragraphs:
        # 1) Reverse the whole line to preserve logical run order visually.
        # 2) Reverse back RTL letter runs (R/AL) so they keep RTL orientation
        #    when we place characters right-to-left.
        lines = text.splitlines(True)

        def reorder_line(line: str) -> str:
            content = line.rstrip("\r\n")
            suffix = line[len(content) :]
            if not content:
                return line

            # 1) Reverse whole content to fix run order
            rev = content[::-1]
            # 2) Un-reverse RTL runs so they render correctly with RTL placement
            rev = self.rtl_pattern.sub(lambda m: m.group(0)[::-1], rev)
            return rev + suffix

        return "".join(reorder_line(line) for line in lines)

    def needs_scrollbar(self):
        return self.scroll_y_range[1] > self.document_height


def lookahead(string: str, index: int, count: int):
    string_length = len(string)
    assert index >= 0 and index < string_length
    assert count > 0

    end = min(index + count, string_length)
    return string[index:end]


def lex(body: str):
    text = ""
    in_tag = False
    index = 0

    while index < len(body):
        char = body[index]
        if char == "&":
            # hack wow
            maybe_entity = lookahead(body, index, 4)
            if maybe_entity in entities.keys():
                text += entities[maybe_entity]
                index += len(maybe_entity)
                continue
        if char == "<":
            in_tag = True
        elif char == ">":
            in_tag = False
        elif not in_tag:
            text += char
        index += 1
    return text


def main():
    import os

    parser = argparse.ArgumentParser(
        "PythonBrowser",
        "browser.py [url] [--direction=ltr]",
    )
    parser.add_argument(
        "url", nargs="?", default=f"file:///{os.path.dirname(__file__)}/about.txt"
    )
    parser.add_argument("--direction", default="ltr")
    args = parser.parse_args()

    Browser(args.direction).load(URL(args.url))
    tkinter.mainloop()


if __name__ == "__main__":
    main()
