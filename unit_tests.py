import unittest
import random
from unittest.mock import patch

from board import Board
from game import Game
from constants import Resource, PlayerColor, Development
from player import Player, RandomAgent
from vertex import Vertex
from edge import Edge
from exceptions import FailedBuildError, IllegalActionError
from actions import Action, ActionType


class TestTileAndEdgeNeighbors(unittest.TestCase):

    def test_tile_neighbors(self):
        b = Board(3)
        for tile in b.get_tiles():
            tile_set = b.get_neighboring_tiles(tile)
            neighbors = set.intersection(*[b.get_neighboring_tiles(t) for t in tile_set])
            self.assertTrue(len(neighbors) == 1 and list(neighbors)[0] == tile)

    def test_tile_edges(self):
        b = Board(3)
        flag = True
        tiles = b.get_tiles()
        for tile in tiles:
            edge_set = b.get_edges_from_tile(tile)
            tile_set = b.get_neighboring_tiles(tile)
            try:
                self.assertTrue(all([len(edge_set.intersection(b.get_edges_from_tile(n))) == 1 for n in tile_set]))
            except AssertionError:
                flag = False
                coords = str(tile.coords)
                print(f"Inconsistency with tile {coords}.")
                print("="*50)
                print(f"Tile {coords} has neighbors {str([t.coords for t in list(tile_set)])} and edges {str([e.coords for e in edge_set])}.")
                for neighbor in tile_set:
                    neighbor_coords = str(neighbor.coords)
                    neighbor_edges = b.get_edges_from_tile(neighbor)
                    print(f"Tile {neighbor_coords}'s edges are: {str([e.coords for e in neighbor_edges])}.")
                    print(f"Tile {coords} shares edges {str([e.coords for e in edge_set.intersection(neighbor_edges)])} with tile {neighbor_coords}.")
                print("="*50)
                print('\n')
        self.assertTrue(flag)

    def test_tile_vertices(self):
        b = Board(3)
        flag = True
        tiles = b.get_tiles()
        for tile in tiles:
            vertex_set = tile.vertices
            neighbor_tile_set = set.intersection(*[b.get_tiles_from_vertex(v) for v in vertex_set])
            try:
                if not (len(neighbor_tile_set) == 1 and list(neighbor_tile_set)[0] == tile):
                    # edge case for corner water tiles because we don't create vertices that aren't used in play
                    self.assertTrue(len(neighbor_tile_set) == 2 and len(b.get_neighboring_tiles(tile)) == 3 and tile in neighbor_tile_set)
            except AssertionError:
                flag = False
                coords = str(tile.coords)
                neighboring_tiles = b.get_neighboring_tiles(tile)
                print(f"Inconsistency with tile {coords}.")
                print("="*50)
                print(f"Tile {coords} has neighbors {str([t.coords for t in list(neighboring_tiles)])} and vertices {str([v.vertex_id for v in vertex_set])}.")
                for neighbor in neighboring_tiles:
                    neighbor_coords = str(neighbor.coords)
                    neighbor_vertices = b.get_vertices_from_tile(neighbor)
                    print(f"Tile {neighbor_coords}'s vertices are: {str([v.vertex_id for v in neighbor_vertices])}.")
                    print(f"Tile {coords} shares vertices {str([v.vertex_id for v in vertex_set.intersection(neighbor_vertices)])} with tile {neighbor_coords}.")
                print("="*50)
                print('\n')
        self.assertTrue(flag)


class TestGameBuildSettlement(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()

    def test_build_settlement_setup_phase(self):
        """During setup phase, player can place a settlement on any available spot."""
        spots = self.game.get_available_settlement_spots(0)
        self.assertTrue(len(spots) > 0)
        vertex = spots[0]
        self.game.build_settlement(0, vertex)
        self.assertEqual(vertex.player_id, 0)
        self.assertIn(vertex, self.game.player_buildings[0])

    def test_build_settlement_occupied_spot(self):
        """Cannot build on a spot that already has a settlement."""
        spots = self.game.get_available_settlement_spots(0)
        vertex = spots[0]
        self.game.build_settlement(0, vertex)
        with self.assertRaises(FailedBuildError):
            self.game.build_settlement(1, vertex)

    def test_build_settlement_marks_first_settlement(self):
        """First settlement in setup should mark first_settlement_played."""
        spots = self.game.get_available_settlement_spots(0)
        vertex = spots[0]
        self.game.build_settlement(0, vertex)
        self.assertTrue(self.game.players[0].first_settlement_played)


class TestGameBuildRoad(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()

    def test_build_road_setup_phase(self):
        """During setup phase, player can place a road adjacent to their settlement."""
        spots = self.game.get_available_settlement_spots(0)
        vertex = spots[0]
        self.game.build_settlement(0, vertex)
        road_spots = self.game.get_available_road_spots(0)
        self.assertTrue(len(road_spots) > 0)
        edge = road_spots[0]
        self.game.build_road(0, edge)
        self.assertEqual(edge.player_road_id, 0)
        self.assertIn(edge, self.game.player_roads[0])

    def test_build_road_occupied_edge(self):
        """Cannot build on an edge that already has a road."""
        spots = self.game.get_available_settlement_spots(0)
        self.game.build_settlement(0, spots[0])
        road_spots = self.game.get_available_road_spots(0)
        edge = road_spots[0]
        self.game.build_road(0, edge)
        with self.assertRaises(FailedBuildError):
            self.game.build_road(1, edge)


class TestGameBuildCity(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()

    def test_build_city_no_settlement(self):
        """Cannot build city without owning a settlement on that vertex."""
        spots = self.game.get_available_settlement_spots(0)
        vertex = spots[0]
        # Give player resources for a city
        self.game.players[0].resources = [0, 2, 0, 3, 0]
        self.game.players[0].settlements = 1
        with self.assertRaises(FailedBuildError):
            self.game.build_city(0, vertex)

    def test_build_city_already_city(self):
        """Cannot build city on a vertex that is already a city."""
        spots = self.game.get_available_settlement_spots(0)
        vertex = spots[0]
        self.game.build_settlement(0, vertex)
        # Give player resources for cities
        self.game.players[0].resources = [0, 4, 0, 6, 0]
        self.game.build_city(0, vertex)
        self.assertTrue(vertex.is_city)
        # Try again
        self.game.players[0].resources = [0, 2, 0, 3, 0]
        self.game.players[0].settlements = 1
        with self.assertRaises(FailedBuildError):
            self.game.build_city(0, vertex)


class TestGameTurnAdvancement(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()

    def test_advance_turn_setup(self):
        """Setup turn advancement should cycle through setup_turn_order."""
        first = self.game.current_turn
        self.game.advance_turn()
        second = self.game.current_turn
        # Should have advanced to next player in setup order
        self.assertEqual(second, self.game.setup_turn_order[1])

    def test_advance_turn_ends_setup(self):
        """After all setup turns, game should transition to normal phase."""
        num_setup_turns = len(self.game.setup_turn_order)
        for _ in range(num_setup_turns):
            self.game.advance_turn()
        self.assertFalse(self.game.is_game_start)


class TestPayOutResources(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()

    def test_payout_with_bank_shortage_single_player(self):
        """If bank can't pay all and only one player receives, that player gets the remainder."""
        # Find a non-desert, non-water tile
        tile = None
        for t in self.game.board.get_tiles():
            if t.resource not in (Resource.DESERT, Resource.WATER) and t.vertices:
                tile = t
                break
        self.assertIsNotNone(tile)

        # Place a settlement on the tile
        vertex = list(tile.vertices)[0]
        vertex.player_id = 0
        vertex.is_city = False

        # Set bank to have only 1 of this resource
        self.game.resource_cards[tile.resource] = 1

        self.game.pay_out_resources([tile])
        # Player should receive 1 (the remainder)
        self.assertEqual(self.game.players[0].resources[tile.resource], 1)

    def test_payout_with_bank_shortage_multiple_players(self):
        """If bank can't pay all and multiple players receive, nobody gets any."""
        tile = None
        for t in self.game.board.get_tiles():
            if t.resource not in (Resource.DESERT, Resource.WATER) and t.vertices and len(list(t.vertices)) >= 2:
                tile = t
                break
        self.assertIsNotNone(tile)

        vertices = list(tile.vertices)
        if len(vertices) >= 2:
            vertices[0].player_id = 0
            vertices[1].player_id = 1
            # Set bank to 1 (less than 2 needed)
            self.game.resource_cards[tile.resource] = 1
            # Reset player resources
            self.game.players[0].resources = [0] * 5
            self.game.players[1].resources = [0] * 5

            self.game.pay_out_resources([tile])
            # Neither should have received anything
            self.assertEqual(self.game.players[0].resources[tile.resource], 0)
            self.assertEqual(self.game.players[1].resources[tile.resource], 0)


class TestPlayerResources(unittest.TestCase):

    def test_give_and_take_resource(self):
        p = Player(0, PlayerColor.RED)
        p.give_resource(Resource.BRICK, 3)
        self.assertEqual(p.resources[Resource.BRICK], 3)
        p.take_resource(Resource.BRICK, 1)
        self.assertEqual(p.resources[Resource.BRICK], 2)

    def test_can_build_settlement(self):
        p = Player(0, PlayerColor.RED)
        self.assertFalse(p.can_build_settlement())
        p.resources = [1, 1, 1, 0, 1]
        self.assertTrue(p.can_build_settlement())

    def test_can_build_city(self):
        p = Player(0, PlayerColor.RED)
        p.resources = [0, 2, 0, 3, 0]
        p.settlements = 1
        self.assertTrue(p.can_build_city())

    def test_can_build_road(self):
        p = Player(0, PlayerColor.RED)
        p.resources = [1, 0, 1, 0, 0]
        self.assertTrue(p.can_build_road())

    def test_can_buy_dev_card(self):
        p = Player(0, PlayerColor.RED)
        p.resources = [0, 1, 0, 1, 1]
        self.assertTrue(p.can_buy_dev_card())

    def test_get_random_available_resource_empty_hand(self):
        p = Player(0, PlayerColor.RED)
        self.assertIsNone(p.get_random_available_resource(random.Random(0)))

    def test_get_random_available_resource_non_empty(self):
        p = Player(0, PlayerColor.RED)
        p.resources = [0, 0, 3, 0, 0]
        self.assertEqual(p.get_random_available_resource(random.Random(0)), Resource.LUMBER)


class TestActionSystem(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()

    def test_setup_legal_actions(self):
        """During setup, legal actions should include BUILD_SETTLEMENT."""
        pid = self.game.current_turn
        actions = self.game.get_legal_setup_actions(pid)
        self.assertTrue(all(a.action_type == ActionType.BUILD_SETTLEMENT for a in actions))
        self.assertTrue(len(actions) > 0)

    def test_apply_action_setup_settlement(self):
        """apply_action should successfully place a settlement during setup."""
        pid = self.game.current_turn
        actions = self.game.get_legal_setup_actions(pid)
        action = actions[0]
        self.game.apply_action(pid, action)
        self.assertEqual(action.target.player_id, pid)

    def test_apply_action_illegal(self):
        """apply_action should raise IllegalActionError for illegal actions."""
        pid = self.game.current_turn
        # Try to build a road when no settlement has been placed (no road spots available)
        fake_action = Action(ActionType.ROLL_DICE)
        with self.assertRaises(IllegalActionError):
            self.game.apply_action(pid, fake_action)

    def test_random_agent_setup_phase(self):
        """RandomAgent should be able to play through the setup phase without crashing."""
        game = Game()
        # Play through entire setup phase
        while game.is_game_start:
            pid = game.current_turn
            actions = game.get_legal_setup_actions(pid)
            if not actions:
                break
            agent = RandomAgent(game.players[pid], game)
            action = agent.choose_action(actions)
            game.apply_action(pid, action)

    def test_get_legal_actions_roll_dice(self):
        """After setup, first legal action should be ROLL_DICE."""
        game = Game()
        game.is_game_start = False
        game.dice_rolled_this_turn = False
        pid = game.current_turn
        actions = game.get_legal_actions(pid)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action_type, ActionType.ROLL_DICE)

    def test_get_legal_actions_end_turn_after_roll(self):
        """After rolling (non-7), END_TURN should be available."""
        game = Game()
        game.is_game_start = False
        game.dice_rolled_this_turn = True
        game.seven_rolled_this_turn = False
        pid = game.current_turn
        actions = game.get_legal_actions(pid)
        action_types = [a.action_type for a in actions]
        self.assertIn(ActionType.END_TURN, action_types)

    def test_initial_robber_tile_is_marked(self):
        game = Game()
        self.assertTrue(game.robber_tile.robber)

    def test_road_can_extend_from_existing_road_endpoint(self):
        game = Game()
        game.is_game_start = False
        for middle in game.board.vertex_graph.nodes:
            neighbors = list(game.board.vertex_graph.neighbors(middle))
            if len(neighbors) < 2:
                continue
            start, end = neighbors[:2]
            start_vertex = game.board.vertex_objects[start]
            middle_vertex = game.board.vertex_objects[middle]
            edge1 = game.board.get_edge_from_graph_edge((start, middle))
            edge2 = game.board.get_edge_from_graph_edge((middle, end))
            start_vertex.player_id = 0
            edge1.player_road_id = 0
            self.assertIn(edge2, game.get_available_road_spots(0))
            middle_vertex.player_id = 1
            self.assertNotIn(edge2, game.get_available_road_spots(0))
            return
        self.fail("Expected to find a vertex with at least two adjacent edges.")

    def test_get_legal_actions_waits_for_all_discards_before_robber_move(self):
        game = Game()
        game.is_game_start = False
        game.dice_rolled_this_turn = True
        game.seven_rolled_this_turn = True
        current_player = game.players[game.current_turn]
        other_player = next(player for player in game.players if player.id != current_player.id)
        current_player.start_of_turn_hand_count = 8
        current_player.resources = [4, 0, 0, 0, 0]
        other_player.start_of_turn_hand_count = 8
        other_player.resources = [5, 0, 0, 0, 0]

        self.assertEqual(game.get_legal_actions(current_player.id), [])
        self.assertEqual(
            [action.action_type for action in game.get_legal_actions(other_player.id)],
            [ActionType.DISCARD],
        )

    def test_setup_action_road_advances_turn(self):
        game = Game()
        pid = game.current_turn
        settlement_action = game.get_legal_setup_actions(pid)[0]
        game.apply_action(pid, settlement_action)
        road_action = game.get_legal_setup_actions(pid)[0]
        game.apply_action(pid, road_action)
        self.assertNotEqual(game.current_turn, pid)

    def test_setup_actions_out_of_turn_empty(self):
        game = Game()
        current = game.current_turn
        other = next(pid for pid in range(game.num_players) if pid != current)
        self.assertEqual(game.get_legal_setup_actions(other), [])

    def test_no_steal_target_still_allows_post_roll_actions(self):
        """When robber is moved to tile with no steal targets, stole_this_turn is auto-set."""
        game = Game()
        game.is_game_start = False
        game.dice_rolled_this_turn = True
        game.seven_rolled_this_turn = True
        # Ensure all players have no resources (no valid steal targets)
        for player in game.players:
            player.resources = [0] * 5
            player.start_of_turn_hand_count = 0
        # Find a tile with no players on it
        empty_tile = next(t for t in game.board.ordered_tiles
                         if t.resource != Resource.WATER and t != game.robber_tile
                         and all(v.player_id == -1 for v in t.vertices))
        game._apply_move_robber(empty_tile)
        # stole_this_turn should be auto-set since no steal targets
        self.assertTrue(game.stole_this_turn)
        actions = game.get_legal_actions(game.current_turn)
        action_types = [a.action_type for a in actions]
        self.assertNotIn(ActionType.STEAL, action_types)
        self.assertIn(ActionType.END_TURN, action_types)

    def test_roll_seven_snapshots_discard_baseline(self):
        game = Game()
        game.is_game_start = False
        for pid, player in enumerate(game.players):
            player.resources = [pid + 1, 0, 0, 0, 0]
            player.start_of_turn_hand_count = 0

        with patch.object(game.rng, "randrange", side_effect=[1, 6]):
            game._apply_roll(game.current_turn)

        self.assertTrue(game.seven_rolled_this_turn)
        for pid, player in enumerate(game.players):
            self.assertEqual(player.start_of_turn_hand_count, pid + 1)

    def test_apply_action_unknown_type_raises(self):
        game = Game()
        game.is_game_start = False

        class FakeActionType:
            name = "FAKE_ACTION"

        fake_type = FakeActionType()
        fake_action = Action(fake_type)
        game.get_legal_actions = lambda _player_id: [Action(fake_type)]

        with self.assertRaises(NotImplementedError):
            game.apply_action(game.current_turn, fake_action)


class TestMaskTurnIndex(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()
        self.game.is_game_start = False

    def test_mask_uses_current_turn_not_idx(self):
        """Mask should enable roll dice for the player whose turn it actually is."""
        from player import Mask
        from actions import ActionType
        pid = self.game.current_turn
        player = self.game.players[pid]
        mask = Mask(player, self.game)
        action_mask = mask.action_type_mask()
        # Roll dice should be enabled (ActionType.ROLL_DICE = 0)
        self.assertEqual(action_mask[ActionType.ROLL_DICE], 1.0)

        # A different player should NOT have roll dice enabled
        other_pid = (pid + 1) % self.game.num_players
        other_player = self.game.players[other_pid]
        other_mask = Mask(other_player, self.game)
        other_action_mask = other_mask.action_type_mask()
        self.assertEqual(other_action_mask[ActionType.ROLL_DICE], 0.0)

    def test_mask_blocks_end_turn_while_waiting_for_robber_move(self):
        from player import Mask
        from actions import ActionType
        self.game.dice_rolled_this_turn = True
        self.game.seven_rolled_this_turn = True
        self.game.robber_moved_this_turn = False
        player = self.game.players[self.game.current_turn]
        mask = Mask(player, self.game).action_type_mask()
        self.assertEqual(mask[ActionType.MOVE_ROBBER], 1.0)
        self.assertEqual(mask[ActionType.END_TURN], 0.0)

    def test_mask_blocks_robber_move_until_all_discards_complete(self):
        from player import Mask
        from actions import ActionType
        self.game.dice_rolled_this_turn = True
        self.game.seven_rolled_this_turn = True
        current_player = self.game.players[self.game.current_turn]
        current_player.start_of_turn_hand_count = 8
        current_player.resources = [4, 0, 0, 0, 0]
        other_player = next(player for player in self.game.players if player.id != current_player.id)
        other_player.start_of_turn_hand_count = 8
        other_player.resources = [5, 0, 0, 0, 0]

        mask = Mask(current_player, self.game).action_type_mask()
        self.assertEqual(mask[ActionType.MOVE_ROBBER], 0.0)
        self.assertEqual(mask[ActionType.END_TURN], 0.0)

    def test_mask_exchange_uses_exchange_feasibility(self):
        from player import Mask
        from actions import ActionType
        self.game.dice_rolled_this_turn = True
        player = self.game.players[self.game.current_turn]
        player.resources = [4, 0, 0, 0, 0]
        self.game.resource_cards[Resource.GRAIN] = 10
        self.game.resource_cards[Resource.BRICK] = 10
        mask = Mask(player, self.game).action_type_mask()
        self.assertEqual(mask[ActionType.EXCHANGE_RESOURCE], 1.0)


class TestMaskAdditional(unittest.TestCase):

    def setUp(self):
        random.seed(42)
        self.game = Game()
        self.game.is_game_start = False
        self.game.dice_rolled_this_turn = True

    def test_city_mask_excludes_existing_cities(self):
        """City mask should only include settlements, not existing cities."""
        from player import Mask
        pid = self.game.current_turn
        player = self.game.players[pid]
        # Directly set up a vertex as owned by this player
        vertex = self.game.board.ordered_vertices[0]
        vertex.player_id = pid
        self.game.player_buildings[pid].add(vertex)
        player.settlements = 1
        # First check: settlement should appear in city mask
        mask_obj = Mask(player, self.game)
        city_mask = mask_obj.city_mask()
        idx = self.game.board.ordered_vertices.index(vertex)
        self.assertEqual(city_mask[idx], 1)
        # Upgrade to city
        vertex.is_city = True
        city_mask = mask_obj.city_mask()
        # Should be 0 since it's already a city
        self.assertEqual(city_mask[idx], 0)

    def test_exchange_mask_requires_full_rate(self):
        """Exchange mask should require player to have >= exchange rate resources."""
        from player import Mask
        pid = self.game.current_turn
        player = self.game.players[pid]
        # Player has 3 brick, exchange rate is 4
        player.resources = [3, 0, 0, 0, 0]
        mask_obj = Mask(player, self.game)
        ex_mask = mask_obj.exchange_mask()
        # Should NOT be able to exchange brick (3 < 4)
        self.assertEqual(ex_mask[0], 0)

        # Give player 4 brick
        player.resources = [4, 0, 0, 0, 0]
        ex_mask = mask_obj.exchange_mask()
        self.assertEqual(ex_mask[0], 1)

    def test_steal_from_mask_size(self):
        """steal_from_mask should return array of size num_players."""
        from player import Mask
        pid = self.game.current_turn
        player = self.game.players[pid]
        # Place another player's settlement on robber tile
        robber_tile = self.game.robber_tile
        if robber_tile.vertices:
            other_pid = (pid + 1) % self.game.num_players
            list(robber_tile.vertices)[0].player_id = other_pid
        mask_obj = Mask(player, self.game)
        steal_mask = mask_obj.steal_from_mask()
        self.assertEqual(len(steal_mask), self.game.num_players)


class TestAdvanceTurnSetupReturn(unittest.TestCase):

    def test_advance_turn_setup_returns_player_id(self):
        """advance_turn_setup should return a valid player ID, not an index."""
        random.seed(42)
        game = Game()
        # Advance through all setup turns
        while game.is_game_start:
            result = game.advance_turn()
            if game.is_game_start:
                # Result should be a valid player ID in setup_turn_order
                self.assertIn(result, range(game.num_players))
            else:
                # When setup ends, should still return a valid player ID
                self.assertIn(result, range(game.num_players))


class TestOwnershipInvariant(unittest.TestCase):

    def test_building_ownership_consistent(self):
        """Verify that player_buildings dict is consistent with vertex.player_id."""
        random.seed(42)
        game = Game()
        # Place some settlements
        for pid in range(game.num_players):
            spots = game.get_available_settlement_spots(pid)
            if spots:
                game.build_settlement(pid, spots[0])

        # Check invariant
        for pid in range(game.num_players):
            buildings = game.player_buildings[pid]
            for vertex in buildings:
                self.assertEqual(vertex.player_id, pid)

    def test_road_ownership_consistent(self):
        """Verify that player_roads dict is consistent with edge.player_road_id."""
        random.seed(42)
        game = Game()
        # Place settlement and road for player 0
        spots = game.get_available_settlement_spots(0)
        game.build_settlement(0, spots[0])
        road_spots = game.get_available_road_spots(0)
        if road_spots:
            game.build_road(0, road_spots[0])

        for pid in range(game.num_players):
            roads = game.player_roads[pid]
            for edge in roads:
                self.assertEqual(edge.player_road_id, pid)


class TestDeterminism(unittest.TestCase):

    def test_same_seed_produces_identical_games(self):
        """Two Game instances with the same seed should produce identical boards and rolls."""
        g1 = Game(rng=random.Random(42))
        g2 = Game(rng=random.Random(42))
        # Boards must be identical
        tiles1 = [(t.resource, t.dice_num) for t in g1.board.ordered_tiles]
        tiles2 = [(t.resource, t.dice_num) for t in g2.board.ordered_tiles]
        self.assertEqual(tiles1, tiles2)
        # Robber tiles must match
        self.assertEqual(g1.robber_tile.coords, g2.robber_tile.coords)
        # Turn orders must match
        self.assertEqual(g1.turn_order, g2.turn_order)
        # Dev card decks must match
        self.assertEqual(g1.development_cards, g2.development_cards)


class TestGetConnectedEdges(unittest.TestCase):

    def test_connected_edges_on_simple_road_chain(self):
        """_get_connected_edges should find all edges belonging to a player's road chain."""
        game = Game(rng=random.Random(99))
        board = game.board
        # Find a chain of 3 edges: v1-v2-v3-v4
        for v1 in board.vertex_graph.nodes:
            neighbors_v1 = list(board.vertex_graph.neighbors(v1))
            if len(neighbors_v1) < 1:
                continue
            v2 = neighbors_v1[0]
            neighbors_v2 = [n for n in board.vertex_graph.neighbors(v2) if n != v1]
            if not neighbors_v2:
                continue
            v3 = neighbors_v2[0]
            neighbors_v3 = [n for n in board.vertex_graph.neighbors(v3) if n != v2]
            if not neighbors_v3:
                continue
            v4 = neighbors_v3[0]
            # Build 3 roads for player 0
            e1 = board.get_edge_from_graph_edge((v1, v2))
            e2 = board.get_edge_from_graph_edge((v2, v3))
            e3 = board.get_edge_from_graph_edge((v3, v4))
            e1.player_road_id = 0
            e2.player_road_id = 0
            e3.player_road_id = 0
            connected = board._get_connected_edges(v1, 0)
            self.assertEqual(len(connected), 3)
            # All 3 edge keys should be present
            edge_keys = {frozenset({v1, v2}), frozenset({v2, v3}), frozenset({v3, v4})}
            self.assertEqual(set(connected), edge_keys)
            return
        self.fail("Could not find a suitable 3-edge chain on the board.")

    def test_connected_edges_stops_at_other_player_roads(self):
        """_get_connected_edges should not cross roads belonging to another player."""
        game = Game(rng=random.Random(99))
        board = game.board
        for v1 in board.vertex_graph.nodes:
            neighbors_v1 = list(board.vertex_graph.neighbors(v1))
            if len(neighbors_v1) < 1:
                continue
            v2 = neighbors_v1[0]
            neighbors_v2 = [n for n in board.vertex_graph.neighbors(v2) if n != v1]
            if not neighbors_v2:
                continue
            v3 = neighbors_v2[0]
            # Player 0 owns v1-v2, player 1 owns v2-v3
            e1 = board.get_edge_from_graph_edge((v1, v2))
            e2 = board.get_edge_from_graph_edge((v2, v3))
            e1.player_road_id = 0
            e2.player_road_id = 1
            connected = board._get_connected_edges(v1, 0)
            self.assertEqual(len(connected), 1)
            self.assertEqual(connected[0], frozenset({v1, v2}))
            return
        self.fail("Could not find a suitable 2-edge chain on the board.")


if __name__ == '__main__':
    unittest.main()
