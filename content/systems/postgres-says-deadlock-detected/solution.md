# Postgres says "deadlock detected" every night at two: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

which-statement-holds-it: 9
what-postgres-did: one-aborted
which-changes-prevent-it: same-table-order, lock-account-up-front
what-the-api-does-on-40p01: retry-the-transaction
