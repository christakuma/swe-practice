# The order was saved, and the warehouse never heard: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

the-gap: 5
publish-inside: ships-uncommitted
the-outbox: insert-both, commit, relay-reads, relay-publishes, relay-marks-sent
what-the-relay-guarantees: at-least-once
change-data-capture: the-relay
