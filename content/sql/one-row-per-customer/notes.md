# Why a LEFT JOIN, and why `COUNT(o.id)`

Two mistakes, and the second one is the interesting one.

**The join.** An inner join keeps a row only where the `ON` condition matched
something. That is the right behaviour when you are asking *which orders were
placed*, and the wrong behaviour when you are asking *how many orders did each
customer place* — because the answer for a customer who placed none is zero, not
silence. A `LEFT JOIN` keeps every row of the left table and fills the right
side with NULLs where there was no match.

The failure mode is what makes this worth drilling: the inner-join answer is not
obviously wrong. It returns plausible data, in the right shape, with the right
numbers in it. It is just missing a row — and the customer it is missing is
exactly the one somebody would have wanted to know about.

**The count.** Having fixed the join, `COUNT(*)` is still wrong, and more
quietly. After the outer join `dana` has one row: her own columns, plus a row of
NULLs where an order would have been. `COUNT(*)` counts *rows in the group*, so
it counts that one and reports 1. `COUNT(o.id)` counts *non-NULL values of that
column*, so it reports 0.

This is the same rule that makes `COUNT(column)` and `COUNT(*)` differ on any
nullable column, and it is worth holding onto as a sentence: **`COUNT(*)` counts
rows; `COUNT(x)` counts values.** Almost every "the totals are one too high"
bug in a report is this.

**Why the grader cannot be fooled.** Both wrong answers are graded on the rows
they return, not on the SQL they are written in — so there is no form of words
that passes. The `kept-the-quiet-customer` check exists so that the verdict
names the row that is wrong instead of printing four that are nearly right.
