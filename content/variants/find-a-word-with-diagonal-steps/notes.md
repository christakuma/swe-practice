# Same search, more ways out of each cell

Revealed after grading. "Word Search" (LeetCode 79) with the king's moves —
the rule the board game Boggle actually uses.

The backtracking is untouched: mark the cell, try each neighbour, unmark on
the way out. Only the neighbour list grows from four to eight.

What does change is the cost. The branching factor doubles, so a search that
was `4^L` in the worst case is `8^L`, and that is why this version's board is
smaller. When a constraint is loosened, the algorithm often survives and the
feasible input size does not — worth checking before promising the same
limits.
