import math
import turtle
from math import sqrt
from turtle import *

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


def hex_to_rect(coord):
    v, u, w = coord
    x = -u / 2 + v - w / 2
    y = (u - w) * ROOT3_OVER_2
    return x * SIDE, y * SIDE


def hexagon(turtle, radius, color, coord_label, dice_num):
    clone = turtle.clone()  # so we don't affect turtle's state
    xpos, ypos = clone.position()
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
    clone.forward(SIDE*ROOT3_OVER_2)
    if dice_num != -1:
        clone.write(str(dice_num), align="center", font=("Arial", 15, "normal"))


def draw(board) -> None:
    # Initialize the turtle
    tortoise = Turtle(visible=False)
    tortoise.speed('fastest')
    tortoise.penup()

    screen = turtle.Screen()
    screen.tracer(0,0)

    coords = list(board.get_tile_coords())
    resources = []
    for q, r, _ in coords:
        if (tile := board.get_tile(q, r)) is not None:
            resources.append(tile.resource)
    colors = [color_map[resource.value] for resource in resources]

    # Plot the points
    x_off, y_off = hex_to_rect((board.board_size,board.board_size,-2*board.board_size))
    y_off += ROOT3_OVER_2 * SIDE
    x_off -= SIDE / 2
    for hexcoord, color in zip(coords, colors):
        pos = hex_to_rect(hexcoord)
        pos = (pos[0] - x_off, pos[1] - y_off)
        tortoise.goto(pos)
        hexagon(tortoise, SIDE, color, hexcoord, board.get_tile(hexcoord[0], hexcoord[1]).get_dice_num())

    # Wait for the user to close the window
    screen = Screen()
    screen.tracer(False)
    screen.exitonclick()
    done()
