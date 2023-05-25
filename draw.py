import math
import turtle
import tkinter
from collections import deque, Counter
from math import sqrt
from turtle import *

from PIL import Image, ImageTk

from constants import RESOURCE
from port import Port

ROOT3_OVER_2 = sqrt(3) / 2

FONT_SIZE = 18
FONT = ('Arial', FONT_SIZE, 'normal')

# the scale used for drawing
SIDE = 50
R = SIDE / (2 * math.sin(math.pi / 6))

COLOR_BRICK = "#AA4A44"
COLOR_GRAIN = "#F7D108"
COLOR_LUMBER = "#228B22"
COLOR_ORE = "#888C8D"
COLOR_WOOL = "#7FC33F"
COLOR_DESERT = "#D7B278"
COLOR_WATER = "#0066FF"

color_map = {
    0: COLOR_BRICK,
    1: COLOR_GRAIN,
    2: COLOR_LUMBER,
    3: COLOR_ORE,
    4: COLOR_WOOL,
    5: COLOR_DESERT,
    6: COLOR_WATER
}

sprites = {}


def hex_to_rect(coord):
    v, u = coord[0], coord[1]
    w = coord[2] if len(coord) == 3 else -v-u
    x = -u / 2 + v - w / 2
    y = (u - w) * ROOT3_OVER_2
    return x * SIDE, y * SIDE


def hexagon(turtle, radius, color, dice_num):
    clone = turtle.clone()  # so we don't affect turtle's state
    clone.setheading(-30)
    clone.color('black', color)
    clone.pendown()
    clone.begin_fill()
    clone.left(90)
    for i in range(6):
        clone.forward(radius)
        clone.left(60)
    clone.end_fill()
    clone.penup()
    clone.left(60)
    clone.forward(SIDE * ROOT3_OVER_2)
    if dice_num != -1:
        clone.color('red' if dice_num in {6, 8} else 'black')
        clone.write(str(dice_num), align="center", font=("Arial", SIDE // 2, "normal"))
    return clone


def load_sprites():
    grain = Image.open("sprites/grain.png").resize((64, 64), Image.ANTIALIAS)
    sprites['grain'] = ImageTk.PhotoImage(grain)

    brick = Image.open("sprites/brick.png").resize((64, 64), Image.ANTIALIAS)
    sprites['brick'] = ImageTk.PhotoImage(brick)

    lumber = Image.open("sprites/lumber.png").resize((64, 64), Image.ANTIALIAS)
    sprites['lumber'] = ImageTk.PhotoImage(lumber)

    ore = Image.open("sprites/ore.png").resize((64, 64), Image.ANTIALIAS)
    sprites['ore'] = ImageTk.PhotoImage(ore)

    wool = Image.open("sprites/wool.png").resize((64, 64), Image.ANTIALIAS)
    sprites['wool'] = ImageTk.PhotoImage(wool)


def draw(board) -> None:
    # Initialize the turtle
    tortoise = Turtle(visible=False)
    tortoise.speed('fastest')
    tortoise.penup()

    screen = turtle.Screen()
    screen.tracer(0, 0)

    tiledata = [(tile.get_coords(), tile.get_resource()) for tile in board.get_tiles()]

    load_sprites()

    icon_stack = deque([])

    # Plot the points
    x_off, y_off = hex_to_rect((board.board_size, board.board_size, -2 * board.board_size))
    y_off += ROOT3_OVER_2 * SIDE
    x_off -= SIDE / 2
    for tile in board.get_tiles():
        hexcoord = tile.get_coords()
        r = tile.get_resource()
        color = color_map[r.value]
        pos = hex_to_rect(hexcoord)
        pos = (pos[0] - x_off, pos[1] - y_off)
        tortoise.goto(pos)
        clone = hexagon(tortoise, SIDE, color, board.get_tile(hexcoord[0], hexcoord[1]).get_dice_num())
        port_vertices = [v for v in tile.get_vertices() if isinstance(v, Port)]
        if r == RESOURCE.WATER and len(port_vertices) == 2:
            c = Counter([v.get_resource() for v in port_vertices])
            pr = max(c, key=c.get)
            if pr:
                icon_stack.append((clone.pos(), sprites[pr.name.lower()]))
    while icon_stack:
        pos, spr = icon_stack.pop()
        screen.getcanvas().create_image(pos, image=spr)

    # Wait for the user to close the window
    screen = Screen()
    screen.tracer(False)
    screen.exitonclick()
    done()
