import pytest
from timeit import default_timer
import time
from typing import List, Optional, Dict

from stockfish import Stockfish, StockfishException


class TestStockfish:
    @pytest.fixture
    def stockfish(self) -> Stockfish:
        return Stockfish()

    # change to `autouse=True` to have the below fixture called before each test function, and then
    # the code after the 'yield' to run after each test.
    @pytest.fixture(autouse=False)
    def autouse_fixture(self, stockfish: Stockfish):
        yield stockfish
        # Some assert statement testing something about the stockfish object here.

    def test_constructor_defaults(self):
        sf = Stockfish()
        assert sf is not None and sf._path == "stockfish"
        assert sf._parameters == sf._DEFAULT_STOCKFISH_PARAMS
        assert sf._depth == 15 and sf._num_nodes == 1000000
        assert sf._turn_perspective is True

    def test_constructor_options(self):
        sf = Stockfish(
            depth=20,
            num_nodes=1000,
            turn_perspective=False,
            parameters={"Threads": 2, "UCI_Elo": 1500},
        )
        assert sf._depth == 20 and sf._num_nodes == 1000
        assert sf._turn_perspective is False
        assert sf._parameters["Threads"] == 2 and sf._parameters["UCI_Elo"] == 1500

    @pytest.mark.slow
    def test_get_best_move_remaining_time_not_first_move(self, stockfish: Stockfish):
        stockfish.is_move_correct("e2e4")
        stockfish.set_fen_position("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        stockfish.is_move_correct("e7e6")
        stockfish.set_fen_position("rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        best_move = stockfish.get_best_move(wtime=1000)
        assert best_move in ("d2d4", "a2a3", "d1e2", "b1c3")
        best_move = stockfish.get_best_move(btime=1000)
        assert best_move in ("d2d4", "b1c3")
