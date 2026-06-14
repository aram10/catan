from collections import defaultdict, Counter
import itertools
import random

from networkx import Graph

from actions import Action, ActionType
from board import Board
from constants import PlayerColor, Development, Resource, MAX_TRADE_PROPOSALS, VICTORY_POINTS_TO_WIN, LONGEST_ROAD_MINIMUM
from edge import Edge
from player import Player, Agent, RandomAgent
from tile import Tile
from trade import TradeProposal
from vertex import Vertex
from exceptions import FailedBuildError, IllegalActionError


class Game:

    def __init__(self, six_players=False, rng: random.Random = None):
        self.rng = rng or random.Random()
        self.players = [Player(i, PlayerColor(i)) for i in range(4)]
        if six_players:
            self.board = Board(4, rng=self.rng)
            for i in range(4, 6):
                self.players.append(Player(i, PlayerColor(i)))
        else:
            self.board = Board(3, rng=self.rng)
        self.agents = {}
        for player in self.players[1:]:
            self.agents[player.id] = RandomAgent(player, self)
        self.num_players = len(self.players)

        self.robber_tile = self.rng.choice(list(self.board.get_desert_tiles()))
        self.robber_tile.robber = True
        self.player_buildings = defaultdict(set)
        self.player_roads = defaultdict(set)
        self.resource_cards = [19] * 5
        self.development_cards = [Development.KNIGHT] * 14 + [Development.ROAD_BUILDING] * 2 + [
            Development.YEAR_OF_PLENTY] * 2 + [Development.MONOPOLY] * 2 + [Development.VICTORY_POINT] * 5
        self.rng.shuffle(self.development_cards)
        self.dev_card_idx = 0

        # turn logic
        # the user of the GUI is always player 0
        self.current_turn_idx = 0
        self.turn_order = list(range(self.num_players))
        self.rng.shuffle(self.turn_order)
        self.dice_rolled_this_turn = False
        self.robber_moved_this_turn = False
        self.stole_this_turn = False
        self.seven_rolled_this_turn = False
        self.dev_card_played_this_turn = False
        self.num_dev_cards_bought_this_turn = [0] * 5
        # robber movement may be triggered by rolling a 7 or by playing a knight
        self.awaiting_robber_move = False
        # free roads granted by a Road Building development card
        self.free_roads_remaining = 0
        # player ID currently holding the largest army bonus (-1 if nobody)
        self.largest_army_player_id = -1
        # player ID currently holding the longest road bonus (-1 if nobody)
        self.longest_road_player_id = -1
        self.trades_proposed_this_turn = 0
        # (from, to)
        self.current_trade_on_table: tuple[int, int] | None = None
        # the TradeProposal currently awaiting a response, if any
        self.pending_trade: TradeProposal | None = None

        # terminal state: set once a player reaches the winning victory point total
        self.game_over = False
        self.winner_id: int | None = None

        # setup turn logic (only for beginning phase)
        self.current_setup_turn_idx = 0
        self.setup_turn_order = self.turn_order + self.turn_order[::-1]
        self.is_game_start = True

    @property
    def current_turn(self):
        return self.turn_order[self.current_turn_idx] if not self.is_game_start else self.setup_turn_order[
            self.current_setup_turn_idx]

    @property
    def remaining_dev_cards(self):
        return 25 - self.dev_card_idx

    def remaining_resource(self, resource: Resource):
        return self.resource_cards[resource]

    def dispense_resource(self, resource: Resource, amt: int):
        if amt > self.resource_cards[resource]:
            raise ValueError(f"Cannot dispense {amt} of {resource}; only {self.resource_cards[resource]} remain")
        self.resource_cards[resource] -= amt

    def pay_out_resources(self, producing_tiles: list[Tile]):
        """
        This method causes every tile not occupied by the robber to produce resources for the players with properties on
        its vertices. The bank may not have enough of a particular resource to pay out what is owed. Suppose there is
        not enough of resource R to pay out all players. If only 1 player is due to collect resource R this turn, that
        player receives the remainder of resource R in the bank. Otherwise, nobody receives any of resource R.
        """
        resource_count = [0]*5
        resource_payout = [[0]*5 for _ in range(self.num_players)]
        # Track which players receive each resource (index by resource)
        players_receiving = [set() for _ in range(5)]
        for tile in producing_tiles:
            if tile.robber:
                continue
            for vertex in tile.vertices:
                if vertex.player_id == -1:
                    continue
                payout = 2 if vertex.is_city else 1
                resource_payout[vertex.player_id][tile.resource] += payout
                resource_count[tile.resource] += payout
                players_receiving[tile.resource].add(vertex.player_id)
        for r in range(5):
            if resource_count[r] > (remaining := self.remaining_resource(Resource(r))):
                if len(players_receiving[r]) == 1:
                    sole_player = next(iter(players_receiving[r]))
                    resource_payout[sole_player][r] = remaining
                else:
                    for pid in range(self.num_players):
                        resource_payout[pid][r] = 0
        for pid in range(self.num_players):
            for r in range(5):
                self.dispense_resource(Resource(r), resource_payout[pid][r])
                self.players[pid].give_resource(Resource(r), resource_payout[pid][r])

    def _refund_to_bank(self, costs: dict):
        """Credit spent resources back to the bank's supply."""
        for resource, amount in costs.items():
            self.resource_cards[resource] += amount

    def build_settlement(self, player_id: int, vertex: Vertex):
        """Builds a settlement for a player."""
        if vertex.player_id != -1:
            raise FailedBuildError(
                f"Player {player_id} may not build on a spot that Player {vertex.player_id} has already built on.")
        player = self.players[player_id]
        if self.is_game_start:
            player.place_settlement(vertex)
            self.player_buildings[player_id].add(vertex)
            if not player.first_settlement_played:
                player.first_settlement_played = True
        elif not player.can_build_settlement():
            raise FailedBuildError(f"Player {player_id} cannot build a settlement.")
        else:
            player.build_settlement(vertex)
            self.player_buildings[player_id].add(vertex)
            self._refund_to_bank({Resource.BRICK: 1, Resource.LUMBER: 1,
                                  Resource.GRAIN: 1, Resource.WOOL: 1})
        # A settlement may sever an opponent's road, so re-evaluate the bonus.
        self._recompute_longest_road()

    def build_road(self, player_id: int, edge: Edge):
        """Builds a road for a player."""
        if edge.player_road_id != -1:
            raise FailedBuildError(
                f"Player {player_id} may not build on a spot that Player {edge.player_road_id} has already built on.")
        player = self.players[player_id]
        if self.is_game_start:
            player.place_road(edge)
        elif self.free_roads_remaining > 0:
            # Road Building development card grants free roads (no resource cost)
            player.place_road(edge)
            self.free_roads_remaining -= 1
        elif not player.can_build_road():
            raise FailedBuildError(f"Player {player_id} cannot build a road.")
        else:
            player.build_road(edge)
            self._refund_to_bank({Resource.BRICK: 1, Resource.LUMBER: 1})
        self.player_roads[player_id].add(edge)
        self._recompute_longest_road()

    def build_city(self, player_id: int, vertex: Vertex):
        """Builds a city for a player."""
        player = self.players[player_id]
        if not player.can_build_city():
            raise FailedBuildError(f"Player {player_id} cannot build a city.")
        if vertex.player_id != player_id:
            raise FailedBuildError(f"Player {player_id} cannot build a city without first building a settlement.")
        if vertex.is_city:
            raise FailedBuildError("A city already exists at this spot.")
        player.build_city(vertex)
        self._refund_to_bank({Resource.GRAIN: 2, Resource.ORE: 3})

    def get_players_on_tile(self, tile: Tile) -> set[Player]:
        """Get all players that have a building on this tile."""
        return {self.players[v.player_id] for v in tile.vertices if v.player_id != -1}

    def get_player_subgraph(self, player: Player) -> Graph:
        """
        Returns the smallest subgraph of the board's vertex subgraph that includes
        all vertices and edges that this player has built on. The subgraph has at most 2 components.
        """
        return self.board.vertex_graph.subgraph(
            [x.vertex_id for x in self.player_buildings[player.id]])

    def get_available_road_spots(self, player_id: int) -> list[Edge]:
        """Given a player, return all edges that this player can build a road on."""
        res = []
        for edge in self.board.vertex_graph.edges:
            edge_obj = self.board.get_edge_from_graph_edge(edge)
            if edge_obj.player_road_id != -1:
                continue
            v1, v2 = self.board.vertex_objects[edge[0]], self.board.vertex_objects[edge[1]]
            if self.is_game_start:
                can_build = v1.player_id == player_id or v2.player_id == player_id
            else:
                can_build = (self._can_build_road_from_vertex(player_id, v1)
                             or self._can_build_road_from_vertex(player_id, v2))
            if can_build:
                res.append(edge_obj)
        return res

    def _can_build_road_from_vertex(self, player_id: int, vertex: Vertex) -> bool:
        if vertex.player_id == player_id:
            return True
        if vertex.player_id != -1:
            return False
        return any(edge.player_road_id == player_id for edge in self.board.get_edges_from_vertex(vertex))

    def _player_must_discard(self, player: Player) -> bool:
        baseline = player.start_of_turn_hand_count
        return baseline > 7 and player.total_resource_count() > baseline - baseline // 2

    def _all_required_discards_complete(self) -> bool:
        return not any(self._player_must_discard(player) for player in self.players)

    def get_available_settlement_spots(self, player_id: int) -> list[Vertex]:
        """
        Return all vertices that this player can build a settlement on.
        During setup, only the distance rule applies. Otherwise, must also be adjacent to own road.
        """
        res = []
        for vertex in self.board.vertex_graph.nodes:
            vertex_obj = self.board.vertex_objects[vertex]
            if vertex_obj.player_id != -1:
                continue
            if any(self.board.vertex_objects[n].player_id != -1
                   for n in self.board.vertex_graph.neighbors(vertex)):
                continue
            if self.is_game_start:
                res.append(vertex_obj)
            elif any(e.player_road_id == player_id
                     for e in self.board.get_edges_from_vertex(vertex_obj)):
                res.append(vertex_obj)
        return res

    def advance_turn(self) -> int:
        return self.advance_turn_setup() if self.is_game_start else self.advance_turn_non_setup()

    def advance_turn_non_setup(self) -> int:
        """Start the turn of the next player, and return that player ID."""
        self.current_turn_idx = (self.current_turn_idx + 1) % self.num_players
        return self.turn_order[self.current_turn_idx]

    def advance_turn_setup(self) -> int:
        """Start the setup turn of the next player, and return that player ID."""
        if self.current_setup_turn_idx + 1 == len(self.setup_turn_order):
            self.is_game_start = False
            return self.turn_order[self.current_turn_idx]
        self.current_setup_turn_idx += 1
        return self.setup_turn_order[self.current_setup_turn_idx]

    def get_player(self, player_id: int) -> Player:
        return self.players[player_id]

    def get_agent(self, player_id: int) -> Agent:
        assert player_id != 0
        return self.agents[player_id]

    def get_players(self) -> list[Player]:
        return self.players

    def get_legal_actions(self, player_id: int) -> list[Action]:
        """Returns all legal actions for the given player in the current game state."""
        player = self.get_player(player_id)

        # Discard (any player may need to discard after a 7 is rolled)
        # TODO: track per-player discard obligations in persistent game state.
        if self.seven_rolled_this_turn:
            if self._player_must_discard(player):
                return [Action(ActionType.DISCARD, Resource(i))
                        for i in range(5) if player.resources[i] > 0]
            if not self._all_required_discards_complete():
                return []

        if self.current_turn != player_id:
            if self.current_trade_on_table and self.current_trade_on_table[1] == player_id:
                responses = [Action(ActionType.RESPOND_TO_TRADE, False)]
                if self.pending_trade is not None and self.pending_trade.is_trade_possible:
                    responses.append(Action(ActionType.RESPOND_TO_TRADE, True))
                return responses
            return []

        # While a proposed trade is awaiting a response, the proposer must wait.
        if self.current_trade_on_table is not None:
            return []

        # Must roll first
        if not self.dice_rolled_this_turn:
            return [Action(ActionType.ROLL_DICE)]

        # Must move robber after rolling 7 or playing a knight
        if (self.seven_rolled_this_turn or self.awaiting_robber_move) and not self.robber_moved_this_turn:
            return [Action(ActionType.MOVE_ROBBER, t) for t in self.board.ordered_tiles
                    if t != self.robber_tile and t.resource != Resource.WATER]

        # Must steal after moving robber
        if self.robber_moved_this_turn and not self.stole_this_turn:
            steal_actions = [Action(ActionType.STEAL, p.id)
                            for p in self.get_players_on_tile(self.robber_tile)
                            if p.id != player_id and p.total_resource_count() > 0]
            if steal_actions:
                return steal_actions

        # Road Building: spend the free roads granted by the dev card before anything else
        if self.free_roads_remaining > 0:
            road_spots = self.get_available_road_spots(player_id)
            if road_spots and player.roads < player.available_roads:
                return [Action(ActionType.BUILD_ROAD, e) for e in road_spots]

        # Normal turn actions
        actions = [Action(ActionType.END_TURN)]

        if player.can_buy_dev_card() and self.remaining_dev_cards > 0:
            actions.append(Action(ActionType.BUY_DEV_CARD))

        if player.can_build_road():
            actions.extend(Action(ActionType.BUILD_ROAD, e)
                           for e in self.get_available_road_spots(player_id))

        if player.can_build_settlement():
            actions.extend(Action(ActionType.BUILD_SETTLEMENT, v)
                           for v in self.get_available_settlement_spots(player_id))

        if player.can_build_city():
            actions.extend(Action(ActionType.BUILD_CITY, v)
                           for v in self.board.ordered_vertices
                           if v.player_id == player_id and not v.is_city)

        if not self.dev_card_played_this_turn and player.start_of_turn_dev_card_count > 0:
            actions.extend(self._playable_dev_card_actions(player))

        for i in range(5):
            if player.resources[i] >= player.resource_exchange_rate[Resource(i)]:
                actions.extend(Action(ActionType.EXCHANGE_RESOURCE, (Resource(i), Resource(j)))
                               for j in range(5)
                               if i != j and self.remaining_resource(Resource(j)) > 0)

        if self.trades_proposed_this_turn < MAX_TRADE_PROPOSALS:
            actions.append(Action(ActionType.PROPOSE_TRADE))

        return actions

    def get_legal_setup_actions(self, player_id: int) -> list[Action]:
        """Returns legal actions during the setup phase."""
        if player_id != self.current_turn:
            return []
        # Players alternate settlement → road; road needed when settlements > roads
        if len(self.player_buildings[player_id]) > len(self.player_roads[player_id]):
            spots = self.get_available_road_spots(player_id)
            return [Action(ActionType.BUILD_ROAD, e) for e in spots]
        else:
            spots = self.get_available_settlement_spots(player_id)
            return [Action(ActionType.BUILD_SETTLEMENT, v) for v in spots]

    def apply_action(self, player_id: int, action: Action):
        """
        Apply a single action for a player. Dispatches to internal methods.
        Raises IllegalActionError if the action is not legal.
        """
        if self.game_over:
            raise IllegalActionError("The game is over; no further actions may be applied.")
        if self.is_game_start:
            legal = self.get_legal_setup_actions(player_id)
        else:
            legal = self.get_legal_actions(player_id)

        # Validate action is legal. PROPOSE_TRADE carries a caller-supplied
        # TradeProposal target, so it is validated by type only.
        if action.action_type == ActionType.PROPOSE_TRADE:
            action_legal = any(a.action_type == ActionType.PROPOSE_TRADE for a in legal)
        else:
            action_legal = any(
                a.action_type == action.action_type and a.target == action.target
                for a in legal
            )
        if not action_legal:
            raise IllegalActionError(
                f"Action {action} is not legal for player {player_id} in current state.")

        if action.action_type == ActionType.ROLL_DICE:
            self._apply_roll(player_id)
        elif action.action_type == ActionType.BUILD_SETTLEMENT:
            self.build_settlement(player_id, action.target)
        elif action.action_type == ActionType.BUILD_ROAD:
            self.build_road(player_id, action.target)
            if self.is_game_start:
                self.advance_turn()
        elif action.action_type == ActionType.BUILD_CITY:
            self.build_city(player_id, action.target)
        elif action.action_type == ActionType.BUY_DEV_CARD:
            self._apply_buy_dev_card(player_id)
        elif action.action_type == ActionType.PLAY_DEV_CARD:
            self._apply_play_dev_card(player_id, action.target)
        elif action.action_type == ActionType.EXCHANGE_RESOURCE:
            self._apply_exchange_resource(player_id, action.target[0], action.target[1])
        elif action.action_type == ActionType.MOVE_ROBBER:
            self._apply_move_robber(action.target)
        elif action.action_type == ActionType.STEAL:
            self._apply_steal(player_id, action.target)
        elif action.action_type == ActionType.DISCARD:
            self._apply_discard(player_id, action.target)
        elif action.action_type == ActionType.END_TURN:
            self._apply_end_turn()
        elif action.action_type == ActionType.RESPOND_TO_TRADE:
            self._apply_respond_to_trade(player_id, action.target)
        elif action.action_type == ActionType.PROPOSE_TRADE:
            self._apply_propose_trade(player_id, action.target)
        else:
            raise NotImplementedError(f"Unhandled action type: {action.action_type}")

        self._check_for_winner(player_id)

    def _check_for_winner(self, player_id: int):
        """Flag the game as over if the player who just acted has reached the winning total.

        Victory points only ever increase on a player's own turn (building, dev cards,
        largest army from their own knight), so it is sufficient to check the acting player.
        """
        if self.game_over:
            return
        if self.get_player(player_id).victory_points >= VICTORY_POINTS_TO_WIN:
            self.game_over = True
            self.winner_id = player_id

    def _apply_roll(self, player_id: int):
        self.dice_rolled_this_turn = True
        roll_val = self.rng.randrange(1, 7) + self.rng.randrange(1, 7)
        if roll_val == 7:
            self.seven_rolled_this_turn = True
            self.awaiting_robber_move = True
            for player in self.players:
                player.start_of_turn_hand_count = player.total_resource_count()
        else:
            producing_tiles = self.board.get_tiles_with_chit(roll_val)
            self.pay_out_resources(producing_tiles)

    def _apply_buy_dev_card(self, player_id: int):
        player = self.get_player(player_id)
        player.resources[Resource.GRAIN] -= 1
        player.resources[Resource.WOOL] -= 1
        player.resources[Resource.ORE] -= 1
        self._refund_to_bank({Resource.GRAIN: 1, Resource.WOOL: 1, Resource.ORE: 1})
        card = self.development_cards[self.dev_card_idx]
        self.dev_card_idx += 1
        player.dev_cards[card] += 1
        self.num_dev_cards_bought_this_turn[card] += 1
        if card == Development.VICTORY_POINT:
            player.victory_points += 1

    def _playable_dev_card_actions(self, player: Player) -> list[Action]:
        """Enumerate the legal PLAY_DEV_CARD actions for a player (excludes victory points)."""
        actions = []
        owned = [player.dev_cards[i] - self.num_dev_cards_bought_this_turn[i] for i in range(5)]
        if owned[Development.KNIGHT] > 0:
            actions.append(Action(ActionType.PLAY_DEV_CARD, Development.KNIGHT))
        if owned[Development.ROAD_BUILDING] > 0:
            if self.get_available_road_spots(player.id) and player.roads < player.available_roads:
                actions.append(Action(ActionType.PLAY_DEV_CARD, Development.ROAD_BUILDING))
        if owned[Development.YEAR_OF_PLENTY] > 0:
            for combo in itertools.combinations_with_replacement(range(5), 2):
                need = Counter(combo)
                if all(self.remaining_resource(Resource(r)) >= n for r, n in need.items()):
                    actions.append(Action(ActionType.PLAY_DEV_CARD,
                                          (Development.YEAR_OF_PLENTY,
                                           (Resource(combo[0]), Resource(combo[1])))))
        if owned[Development.MONOPOLY] > 0:
            actions.extend(Action(ActionType.PLAY_DEV_CARD, (Development.MONOPOLY, Resource(r)))
                           for r in range(5))
        return actions

    def _apply_play_dev_card(self, player_id: int, target):
        """Apply a played development card. ``target`` is a Development enum, or a
        ``(Development, payload)`` tuple for cards that require a choice."""
        player = self.get_player(player_id)
        if isinstance(target, tuple):
            card, payload = target
        else:
            card, payload = target, None
        player.dev_cards[card] -= 1
        self.dev_card_played_this_turn = True
        if card == Development.KNIGHT:
            self._play_knight(player)
        elif card == Development.MONOPOLY:
            self._play_monopoly(player, payload)
        elif card == Development.YEAR_OF_PLENTY:
            self._play_year_of_plenty(player, payload)
        elif card == Development.ROAD_BUILDING:
            self._play_road_building(player)

    def _play_knight(self, player: Player):
        player.knights_played += 1
        self._update_largest_army(player)
        # A knight forces the robber to be moved (and a steal), like rolling a 7.
        self.awaiting_robber_move = True
        self.robber_moved_this_turn = False
        self.stole_this_turn = False

    def _update_largest_army(self, player: Player):
        """Award or transfer the largest army bonus (needs >= 3 knights, strictly most)."""
        if player.knights_played < 3:
            return
        if self.largest_army_player_id == -1:
            player.give_largest_army()
            self.largest_army_player_id = player.id
        elif self.largest_army_player_id != player.id:
            holder = self.get_player(self.largest_army_player_id)
            if player.knights_played > holder.knights_played:
                holder.remove_largest_army()
                player.give_largest_army()
                self.largest_army_player_id = player.id

    def _recompute_longest_road(self):
        """Award or transfer the Longest Road bonus after the road network changes.

        Rules: a player qualifies with a continuous road of at least
        ``LONGEST_ROAD_MINIMUM``. The first qualifier earns the bonus; a current
        holder keeps it on a tie and only loses it to a single player whose road is
        strictly longer (or when their own road drops below the minimum). When the
        title is vacant it is granted only to an unambiguous (single) leader.
        """
        lengths = {p.id: self.board.longest_road_length(p.id) for p in self.players}
        holder = self.longest_road_player_id

        if holder != -1 and lengths[holder] < LONGEST_ROAD_MINIMUM:
            self.get_player(holder).remove_longest_road()
            self.longest_road_player_id = -1
            holder = -1

        best_len = max(lengths.values(), default=0)
        if best_len < LONGEST_ROAD_MINIMUM:
            return
        leaders = [pid for pid, length in lengths.items() if length == best_len]

        if holder == -1:
            if len(leaders) == 1:
                self.get_player(leaders[0]).give_longest_road()
                self.longest_road_player_id = leaders[0]
        elif best_len > lengths[holder] and len(leaders) == 1 and leaders[0] != holder:
            self.get_player(holder).remove_longest_road()
            self.get_player(leaders[0]).give_longest_road()
            self.longest_road_player_id = leaders[0]

    def _play_monopoly(self, player: Player, resource: Resource):
        total = 0
        for other in self.players:
            if other.id == player.id:
                continue
            amt = other.resources[resource]
            if amt > 0:
                other.take_resource(resource, amt)
                total += amt
        player.give_resource(resource, total)

    def _play_year_of_plenty(self, player: Player, resources):
        for resource in resources:
            self.dispense_resource(resource, 1)
            player.give_resource(resource, 1)

    def _play_road_building(self, player: Player):
        self.free_roads_remaining = max(0, min(2, player.available_roads - player.roads))

    def _apply_exchange_resource(self, player_id: int, resource_given: Resource, resource_received: Resource):
        player = self.get_player(player_id)
        rate = player.resource_exchange_rate[resource_given]
        player.resources[resource_given] -= rate
        self.resource_cards[resource_given] += rate
        player.resources[resource_received] += 1
        self.resource_cards[resource_received] -= 1

    def _apply_move_robber(self, tile: Tile):
        self.robber_tile.robber = False
        tile.robber = True
        self.robber_tile = tile
        self.robber_moved_this_turn = True
        # If no valid steal targets exist, skip steal phase immediately
        stealable = any(p.id != self.current_turn and p.total_resource_count() > 0
                        for p in self.get_players_on_tile(tile))
        if not stealable:
            self.stole_this_turn = True

    def _apply_steal(self, player_id: int, target_player_id: int):
        player = self.get_player(player_id)
        target = self.get_player(target_player_id)
        resource = target.get_random_available_resource(self.rng)
        if resource is not None:
            target.take_resource(resource, 1)
            player.give_resource(resource, 1)
        self.stole_this_turn = True

    def _apply_discard(self, player_id: int, resource: Resource):
        player = self.get_player(player_id)
        player.take_resource(resource, 1)
        self.resource_cards[resource] += 1

    def _apply_end_turn(self):
        self.advance_turn_non_setup()
        self.dice_rolled_this_turn = False
        self.robber_moved_this_turn = False
        self.stole_this_turn = False
        self.seven_rolled_this_turn = False
        self.awaiting_robber_move = False
        self.free_roads_remaining = 0
        self.dev_card_played_this_turn = False
        self.num_dev_cards_bought_this_turn = [0] * 5
        self.trades_proposed_this_turn = 0
        self.current_trade_on_table = None
        # Update start-of-turn tracking for next player
        next_player = self.get_player(self.current_turn)
        next_player.start_of_turn_hand_count = next_player.total_resource_count()
        next_player.start_of_turn_dev_card_count = next_player.total_dev_card_count()

    def _apply_propose_trade(self, player_id: int, proposal: TradeProposal):
        if proposal is None:
            return
        if proposal.proposer.id != player_id:
            raise IllegalActionError(
                f"Player {player_id} cannot propose a trade on behalf of player {proposal.proposer.id}.")
        self.pending_trade = proposal
        self.current_trade_on_table = (proposal.proposer.id, proposal.target.id)
        self.trades_proposed_this_turn += 1

    def _apply_respond_to_trade(self, player_id: int, accept: bool):
        """Resolve the pending trade. On acceptance the resources are exchanged."""
        if accept and self.pending_trade is not None and self.pending_trade.is_trade_possible:
            self.pending_trade.accept_trade()
        self.pending_trade = None
        self.current_trade_on_table = None
