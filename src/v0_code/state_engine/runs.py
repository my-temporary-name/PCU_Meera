"""Run counting and the life of one deviation item (spec R7 - R10), per measure. Pure: it sees only the position level and direction of each
NEW reading, so it is easy to test and the same rules apply live and in a replay."""

from dataclasses import dataclass

from v0_code.state_engine.config import LABEL_RANK


@dataclass
class Tracker:
    open_rank: int | str
    close_rank: int | str
    run_direction: str | None = None
    run_count: int = 0
    close_count: int = 0
    open: bool = False
    open_direction: str | None = None

    def __post_init__(self):
        self.open_rank = LABEL_RANK.get(self.open_rank, self.open_rank)
        self.close_rank = LABEL_RANK.get(self.close_rank, self.close_rank)

    def new_reading(self, level: str, direction: str | None, n_open: int, n_close: int, severe: bool = False) -> dict:
        """Feed one new accepted reading. Returns {"opened": bool, "closed": bool}; both can be true when an opposite-direction run replaces an item."""
        rank = LABEL_RANK[level]
        qualifies = rank >= self.open_rank and direction is not None
        # R7: the run
        if qualifies and direction == self.run_direction:
            self.run_count += 1
        elif qualifies:
            self.run_direction, self.run_count = direction, 1
        else:
            self.run_count = 0                                         # within "slightly" or better (below the opening label) resets; the last direction is kept for display
        closed = opened = False
        # R9 / R10: an open item counts consecutive readings at or better than the closing label (or leaving its direction)
        if self.open:
            ok = rank <= self.close_rank or (direction is not None and direction != self.open_direction)
            self.close_count = self.close_count + 1 if ok else 0
            if self.close_count >= n_close:
                self.open, self.open_direction, self.close_count, closed = False, None, 0, True
        # R8: opening
        if not self.open and direction is not None and (severe or self.run_count >= n_open):
            self.open, self.open_direction, self.close_count, opened = True, direction, 0, True
        return {"opened": opened, "closed": closed}

    def go_stale(self) -> dict:
        """R3: a measure that is not current has no active run and no open item."""
        closed = self.open
        self.run_count = self.close_count = 0
        self.open, self.open_direction = False, None
        return {"closed": closed}

    def snapshot(self) -> dict:
        return {"direction": self.run_direction, "count": self.run_count, "close_count": self.close_count}
