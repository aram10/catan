import math
import turtle
import tkinter
from collections import deque, Counter, defaultdict
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
COLOR_BRIDGE = "#9D7D3C"

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
    w = coord[2] if len(coord) == 3 else -v - u
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
    clone.forward(R)
    p = clone.pos()
    if dice_num != -1:
        clone.color('red' if dice_num in {6, 8} else 'black')
        clone.write(str(dice_num), align="center", font=("Arial", SIDE // 2, "normal"))
    return clone, p


def load_sprites():
    grain = Image.open("sprites/grain.png")
    grain = grain.resize((32, 32), Image.LANCZOS)
    sprites['grain'] = ImageTk.PhotoImage(grain)

    brick = Image.open("sprites/brick.png")
    brick = brick.resize((32, 32), Image.LANCZOS)
    sprites['brick'] = ImageTk.PhotoImage(brick)

    lumber = Image.open("sprites/lumber.png")
    lumber = lumber.resize((32, 32), Image.LANCZOS)
    sprites['lumber'] = ImageTk.PhotoImage(lumber)

    ore = Image.open("sprites/ore.png")
    ore = ore.resize((32, 32), Image.LANCZOS)
    sprites['ore'] = ImageTk.PhotoImage(ore)

    wool = Image.open("sprites/wool.png")
    wool = wool.resize((32, 32), Image.LANCZOS)
    sprites['wool'] = ImageTk.PhotoImage(wool)

    any = Image.open("sprites/any.png")
    any = any.resize((32, 32), Image.LANCZOS)
    sprites['any'] = ImageTk.PhotoImage(any)

    settlement = Image.open("sprites/settlements/settlement_red.png")
    settlement = settlement.resize((20, 20), Image.LANCZOS)
    sprites['settlement'] = ImageTk.PhotoImage(settlement)


def draw(board) -> None:
    # Initialize the turtle
    tortoise = Turtle(visible=False)
    tortoise.speed('fastest')
    tortoise.penup()

    screen = turtle.Screen()
    screen.tracer(0, 0)
    canvas = screen.getcanvas()

    load_sprites()

    icon_stack = deque([])

    # Keep track of positions of hexagon centers on canvas for later use
    # This will tell us exactly where all the vertices are, too
    tile_positions = {}

    # Need to draw "bridges" between port icons and the actual port vertices
    lines_to_draw = deque([])

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
        clone, p = hexagon(tortoise, SIDE, color, board.get_tile(hexcoord[0], hexcoord[1]).get_dice_num())
        tile_positions[tile.get_coords()] = p
        tile.set_canvas_pos(p)
        if r == RESOURCE.WATER:
            ports = [v for v in tile.get_vertices() if isinstance(v, Port)]
            c = Counter([v.get_resource() for v in ports])
            pr = max(c, key=c.get)
            ports_of_resource_in_question = [v for v in ports if v.get_resource() == pr]
            if r == RESOURCE.WATER and c[pr] >= 2:
                # could be 3 ports of same resource, but port tile only "owns" two of them
                if c[pr] == 2 and board.vertices_are_adjacent(ports_of_resource_in_question[0],
                                                              ports_of_resource_in_question[1]):
                    icon_stack.append((clone.pos(), sprites[pr.name.lower()]))
                    lines_to_draw.append((clone.pos(), ports_of_resource_in_question[0].get_vertex_id()))
                    lines_to_draw.append((clone.pos(), ports_of_resource_in_question[1].get_vertex_id()))
                elif c[pr] == 3:
                    if board.vertices_are_adjacent(ports_of_resource_in_question[0], ports_of_resource_in_question[1]):
                        icon_stack.append((clone.pos(), sprites[pr.name.lower()]))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[0].get_vertex_id()))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[1].get_vertex_id()))
                    elif board.vertices_are_adjacent(ports_of_resource_in_question[1],
                                                     ports_of_resource_in_question[2]):
                        icon_stack.append((clone.pos(), sprites[pr.name.lower()]))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[1].get_vertex_id()))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[2].get_vertex_id()))
                    elif board.vertices_are_adjacent(ports_of_resource_in_question[0],
                                                     ports_of_resource_in_question[2]):
                        icon_stack.append((clone.pos(), sprites[pr.name.lower()]))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[0].get_vertex_id()))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[2].get_vertex_id()))

    # calculate canvas positions of vertices/edges for future drawing
    for vertex in board.get_vertices():
        # average of tile center positions
        tile_pos_list = [tile.get_canvas_pos() for tile in board.get_tiles_from_vertex(vertex)]
        vertex.set_canvas_pos(((tile_pos_list[0][0] + tile_pos_list[1][0] + tile_pos_list[2][0]) / 3,
                               (tile_pos_list[0][1] + tile_pos_list[1][1] + tile_pos_list[2][1]) / 3))

    for edge in board.get_edges():
        # average of vertex positions
        vertex_pos_list = [v.get_canvas_pos() for v in board.get_vertices_from_edge(edge)]
        edge.set_canvas_pos(
            ((vertex_pos_list[0][0] + vertex_pos_list[1][0]) / 2, (vertex_pos_list[0][1] + vertex_pos_list[1][1]) / 2))

    clone = tortoise.clone()
    clone.color(COLOR_BRIDGE)
    clone.pensize(5)
    while lines_to_draw:
        p1, vert_id = lines_to_draw.popleft()
        p2 = tuple(sum(x) / 3 for x in zip(*[tile_positions[x] for x in vert_id]))
        clone.penup()
        clone.goto(p1)
        clone.pendown()
        clone.goto(p2)
    clone.penup()
    while icon_stack:
        pos, spr = icon_stack.pop()
        img_item = canvas.create_image(pos, image=spr)
        canvas.tag_bind(img_item, f'<Button-1>',
                        lambda event, pos=pos: print(f"Image clicked at position: x={pos[0]}, y={pos[1]}"))

    # Wait for the user to close the window
    screen = Screen()
    screen.tracer(False)
    done()
