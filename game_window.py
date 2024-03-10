import math
import tkinter
from collections import deque, Counter
from math import sqrt
from tkinter import LEFT, RIGHT, TOP, Y, ttk
from turtle import RawTurtle
from typing import Tuple

from PIL import Image, ImageTk

from constants import PLAYERCOLOR, RESOURCE
from port import Port
from vertex import Vertex

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


class GameWindow:

    def __init__(self, game: 'Game'):
        self.game = game
        self.board = game.board

        self.root = tkinter.Tk()
        self.root.geometry("1500x1000")

        # Create canvas
        self.canvas = tkinter.Canvas(self.root, width=1000, height=1000, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Create frame for menu
        self.menu_frame = tkinter.Frame(self.root, width=1500, height=800)
        self.menu_frame.pack(side="left", fill="y")

        # Create CLI
        self.cli = tkinter.Text(self.menu_frame, state="disabled", bg="black", fg="white")
        self.cli.pack(side="top", fill="both", expand=True)

        # Create scrollbar
        self.scroll = tkinter.Scrollbar(self.menu_frame, command=self.cli.yview)

        # Configure CLI to use scrollbar
        self.cli.configure(yscrollcommand=self.scroll.set)

        self.button_frame = tkinter.Frame(self.menu_frame)
        self.button_frame.pack(side="top")

        self.offer_trade_frame = tkinter.Frame(self.menu_frame)
        self.offer_trade_frame.pack(side="bottom")

        # Top region buttons
        roll_button = tkinter.Button(self.button_frame, text="Roll")
        roll_button.pack(side="top", padx=5, pady=5)

        settlement_button = tkinter.Button(self.button_frame, text="Build Settlement",
                                           command=self.show_available_settlement_spots)
        settlement_button.pack(side="top", padx=5, pady=5)

        city_button = tkinter.Button(self.button_frame, text="Build City")
        city_button.pack(side="top", padx=5, pady=5)

        dev_card_button = tkinter.Button(self.button_frame, text="Buy Development Card")
        dev_card_button.pack(side="top", padx=5, pady=5)

        # Offer Trade button
        offer_trade_button = tkinter.Button(self.offer_trade_frame, text="Offer Trade")
        offer_trade_button.pack(side="left", padx=5, pady=5)

        # Trade Inputs (Fillable Text Inputs and Dropdowns)
        from_input = tkinter.Entry(self.offer_trade_frame, width=10)
        from_input.pack(side="left", padx=5, pady=5)
        from_dropdown = ttk.Combobox(self.offer_trade_frame, width=10,
                                     values=["Resource 1", "Resource 2", "Resource 3"])
        from_dropdown.pack(side="left", padx=5, pady=5)

        to_input = tkinter.Entry(self.offer_trade_frame, width=10)
        to_input.pack(side="left", padx=5, pady=5)
        to_dropdown = ttk.Combobox(self.offer_trade_frame, width=10, values=["Resource 1", "Resource 2", "Resource 3"])
        to_dropdown.pack(side="left", padx=5, pady=5)

        # tk will check this every few frames to see if anything needs to be drawn
        self.update_stack = deque([])

        self.sprites = {}

        # keep track of object ids for settlement/road icons
        self.canvas_settlements = {}
        self.canvas_roads = {}

        # object ids of placeholder sprites, indicating a spot is open for a settlement/road
        self.canvas_phantom_settlements = {}
        self.canvas_phantom_roads = {}

        self.phantom_settlements_anim = True

        self._load_sprites()

    def draw(self) -> None:
        tortoise = RawTurtle(self.canvas)
        tortoise.speed('fastest')
        tortoise.hideturtle()
        tortoise.penup()

        icon_stack = deque([])

        # Keep track of positions of hexagon centers on canvas for later use
        # This will tell us exactly where all the vertices are, too
        tile_positions = {}

        # Need to draw "bridges" between port icons and the actual port vertices
        lines_to_draw = deque([])

        # Plot the points
        x_off, y_off = hex_to_rect((self.board.board_size, self.board.board_size, -2 * self.board.board_size))
        y_off += ROOT3_OVER_2 * SIDE
        x_off -= SIDE / 2
        for tile in self.board.get_tiles():
            hexcoord = tile.get_coords()
            r = tile.get_resource()
            color = color_map[r.value]
            pos = hex_to_rect(hexcoord)
            pos = (pos[0] - x_off, pos[1] - y_off)
            tortoise.goto(pos)
            clone, p = hexagon(tortoise, SIDE, color, self.board.get_tile(hexcoord[0], hexcoord[1]).get_dice_num())
            tile_positions[tile.get_coords()] = p
            tile.set_canvas_pos(p)
            if r == RESOURCE.WATER:
                ports = [v for v in tile.get_vertices() if isinstance(v, Port)]
                c = Counter([v.get_resource() for v in ports])
                pr = max(c, key=c.get)
                ports_of_resource_in_question = [v for v in ports if v.get_resource() == pr]
                if r == RESOURCE.WATER and c[pr] >= 2:
                    # could be 3 ports of same resource, but port tile only "owns" two of them
                    if c[pr] == 2 and self.board.vertices_are_adjacent(ports_of_resource_in_question[0],
                                                                       ports_of_resource_in_question[1]):
                        icon_stack.append((clone.pos(), self.sprites[pr.name.lower()]))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[0].get_vertex_id()))
                        lines_to_draw.append((clone.pos(), ports_of_resource_in_question[1].get_vertex_id()))
                    elif c[pr] == 3:
                        if self.board.vertices_are_adjacent(ports_of_resource_in_question[0],
                                                            ports_of_resource_in_question[1]):
                            icon_stack.append((clone.pos(), self.sprites[pr.name.lower()]))
                            lines_to_draw.append((clone.pos(), ports_of_resource_in_question[0].get_vertex_id()))
                            lines_to_draw.append((clone.pos(), ports_of_resource_in_question[1].get_vertex_id()))
                        elif self.board.vertices_are_adjacent(ports_of_resource_in_question[1],
                                                              ports_of_resource_in_question[2]):
                            icon_stack.append((clone.pos(), self.sprites[pr.name.lower()]))
                            lines_to_draw.append((clone.pos(), ports_of_resource_in_question[1].get_vertex_id()))
                            lines_to_draw.append((clone.pos(), ports_of_resource_in_question[2].get_vertex_id()))
                        elif self.board.vertices_are_adjacent(ports_of_resource_in_question[0],
                                                              ports_of_resource_in_question[2]):
                            icon_stack.append((clone.pos(), self.sprites[pr.name.lower()]))
                            lines_to_draw.append((clone.pos(), ports_of_resource_in_question[0].get_vertex_id()))
                            lines_to_draw.append((clone.pos(), ports_of_resource_in_question[2].get_vertex_id()))

        # calculate canvas positions of vertices/edges for future drawing
        for vertex in self.board.get_vertices():
            # average of tile center positions
            tile_pos_list = [tile.get_canvas_pos() for tile in self.board.get_tiles_from_vertex(vertex)]
            vertex.set_canvas_pos(((tile_pos_list[0][0] + tile_pos_list[1][0] + tile_pos_list[2][0]) / 3,
                                   (tile_pos_list[0][1] + tile_pos_list[1][1] + tile_pos_list[2][1]) / 3))
            vertex_canvas_pos = vertex.get_canvas_pos()
            self.canvas_phantom_settlements[vertex_canvas_pos] = self.canvas.create_image(vertex_canvas_pos,
                                                                                                image=self.sprites[
                                                                                                    'settlement_placeholder'],
                                                                                                state="hidden")

        for edge in self.board.get_edges():
            # average of vertex positions
            vertex_pos_list = [v.get_canvas_pos() for v in self.board.get_vertices_from_edge(edge)]
            edge.set_canvas_pos(
                ((vertex_pos_list[0][0] + vertex_pos_list[1][0]) / 2,
                 (vertex_pos_list[0][1] + vertex_pos_list[1][1]) / 2))

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
            img_item = self.canvas.create_image(pos, image=spr)
            self.canvas.tag_bind(img_item, '<Button-1>',
                                 lambda event, pos=pos: print(f"Image clicked at position: x={pos[0]}, y={pos[1]}"))

        def check_for_updates():
            while self.update_stack:
                pos, spr = self.update_stack.pop()
                self.canvas.create_image(pos, image=spr)
            self.root.update_idletasks()
            self.root.after(100, check_for_updates)

        self.root.after(0, check_for_updates)

        self.root.mainloop()

    def _load_sprites(self):
        grain = Image.open("sprites/grain.png")
        grain = grain.resize((32, 32), Image.LANCZOS)
        self.sprites['grain'] = ImageTk.PhotoImage(grain)

        brick = Image.open("sprites/brick.png")
        brick = brick.resize((32, 32), Image.LANCZOS)
        self.sprites['brick'] = ImageTk.PhotoImage(brick)

        lumber = Image.open("sprites/lumber.png")
        lumber = lumber.resize((32, 32), Image.LANCZOS)
        self.sprites['lumber'] = ImageTk.PhotoImage(lumber)

        ore = Image.open("sprites/ore.png")
        ore = ore.resize((32, 32), Image.LANCZOS)
        self.sprites['ore'] = ImageTk.PhotoImage(ore)

        wool = Image.open("sprites/wool.png")
        wool = wool.resize((32, 32), Image.LANCZOS)
        self.sprites['wool'] = ImageTk.PhotoImage(wool)

        any = Image.open("sprites/any.png")
        any = any.resize((32, 32), Image.LANCZOS)
        self.sprites['any'] = ImageTk.PhotoImage(any)

        for x in ['red', 'orange', 'blue', 'green', 'white', 'brown']:
            settlement = Image.open(f"sprites/settlements/settlement_{x}.png")
            settlement = settlement.resize((20, 20), Image.LANCZOS)
            self.sprites[f'settlement_{x}'] = ImageTk.PhotoImage(settlement)

        settlement = Image.open(f"sprites/settlements/settlement_placeholder.png")
        settlement = settlement.resize((20, 20), Image.LANCZOS)
        self.sprites['settlement_placeholder'] = ImageTk.PhotoImage(settlement)

    def draw_settlement(self, pos: Tuple[float, float]):
        """
        Draw a settlement at this position, whose color corresponds to the player whose turn it is
        """
        color_name = self.game.players[self.game.current_turn].color.name.lower()
        self.update_stack.append((pos, self.sprites[f'settlement_{color_name}']))

    def draw_and_clear(self, pos: Tuple[float, float]):
        """
        Draw a settlement at this position, whose color corresponds to the player whose turn it is.
        Then, stop any ongoing settlement animations.
        """
        self.draw_settlement(pos)
        self.phantom_settlements_anim = False
        for pos in self.canvas_phantom_settlements:
            self.canvas.itemconfigure(self.canvas_phantom_settlements[pos], state='hidden')
            self.canvas.tag_unbind(self.canvas_phantom_settlements[pos], "<Button-1>")

    def show_available_settlement_spots(self):
        # icons should place a settlement when clicked
        for pos in self.canvas_phantom_settlements:
            i = self.canvas.tag_bind(self.canvas_phantom_settlements[pos], "<Button-1>", lambda x, pos=pos: self.draw_and_clear(pos))
        self.toggle_available_settlement_spots(True)

    def toggle_available_settlement_spots(self, on: bool):
        if self.phantom_settlements_anim:
            for pos in self.canvas_phantom_settlements:
                self.canvas.itemconfigure(self.canvas_phantom_settlements[pos], state='normal' if on else 'hidden')
            self.canvas.after(500, lambda: self.toggle_available_settlement_spots(not on))
        else:
            self.phantom_settlements_anim = True
