from math import sqrt
from turtle import *

ROOT3_OVER_2 = sqrt(3) / 2

FONT_SIZE = 18
FONT = ('Arial', FONT_SIZE, 'normal')

# the scale used for drawing
SIDE = 50

COLOR_BRICK = "#AA4A44"
COLOR_GRAIN = "#F7D108"
COLOR_LUMBER = "#228B22"
COLOR_ORE = "#888C8D"
COLOR_WOOL = "#7FC33F"
COLOR_DESERT = "#D7B278"

color_map = {
    0: COLOR_BRICK,
    1: COLOR_GRAIN,
    2: COLOR_LUMBER,
    3: COLOR_ORE,
    4: COLOR_WOOL,
    5: COLOR_DESERT
}


def hex_to_rect(coord):
    v, u, w = coord
    x = -u / 2 + v - w / 2
    y = (u - w) * ROOT3_OVER_2
    return x * SIDE, y * SIDE


def hexagon(turtle, radius, color):
    clone = turtle.clone()  # so we don't affect turtle's state
    xpos, ypos = clone.position()
    clone.setposition(xpos - radius / 2, ypos - ROOT3_OVER_2 * radius)
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
    clone.setposition(xpos, ypos - FONT_SIZE / 2)


def draw(board) -> None:
    # Initialize the turtle
    tortoise = Turtle(visible=False)
    tortoise.speed('fastest')
    tortoise.penup()

    coords = list(board.get_tile_coords())
    resources = []
    for q, r, _ in coords:
        if (tile := board.get_tile(q, r)) is not None:
            resources.append(tile.resource)
    colors = [color_map[resource.value] for resource in resources]

    # Plot the points
    for hexcoord, color in zip(coords, colors):
        tortoise.goto(hex_to_rect(hexcoord))
        hexagon(tortoise, SIDE, color)

    # Wait for the user to close the window
    screen = Screen()
    screen.tracer(False)
    screen.exitonclick()
    done()
