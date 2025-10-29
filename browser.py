from url import URL
from consts import entities
import tkinter
import tkinter.font
import platform

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.scroll_y = 0
        self.window.bind("<Down>", self.scroll)
        if platform.system() == "Linux":
            self.window.bind("<Button-4>", self.handle_linux_scrollup)
            self.window.bind("<Button-5>", self.handle_linux_scrolldown)
        else:
            self.window.bind("<MouseWheel>", self.handle_wheel)

    def load(self, url: URL):
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.scroll_y_range = (0, self.display_list[-1][1] - HEIGHT)
        self.font = tkinter.font.Font(family="Noto Sans KR")
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll_y + HEIGHT:
                continue
            if y + VSTEP < self.scroll_y:
                continue
            self.canvas.create_text(x, y - self.scroll_y, text=c, font=self.font)
    
    def scroll(self, delta=SCROLL_STEP, multiplier=1):
        self.scroll_y += delta * multiplier 
        self.scroll_y = max(self.scroll_y_range[0], min(self.scroll_y, self.scroll_y_range[1]))
        self.draw()

    def handle_wheel(self, e: tkinter.Event):
        multiplier: int
        match platform.system():
            case "Windows":
                multiplier = 1
            case "Darwin":
                multiplier = -1
            case _:
                multiplier = 1

        self.scroll(e.delta, multiplier)

    def handle_linux_scrollup(self, e):
        self.scroll(multiplier=-1)
    
    def handle_linux_scrolldown(self, e):
        self.scroll(multiplier=1)

    
def layout(text: str):
    display_list: list[tuple[int, int, str]] = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        if c == "\n":
            cursor_y += int(VSTEP * 1.2)
            cursor_x = HSTEP
        
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP

        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP

    return display_list


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
    import sys

    url = f"file:///{os.path.dirname(__file__)}/about.txt"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    Browser().load(URL(url))
    tkinter.mainloop()


if __name__ == "__main__":
    main()
