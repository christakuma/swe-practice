# A column rename broke the site for the length of a deploy: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

why-it-broke: two-versions-one-schema
the-safe-sequence: add-column, write-both, backfill, switch-reads, stop-writing-name, drop-name
how-to-backfill: in-batches
why-rollback-is-safe: still-writing-name
before-the-alter: lock-timeout
