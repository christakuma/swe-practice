# Customers are charged twice when the card provider is slow: your answers

Answer each question on its own line: its id, a colon, then your answer.
Separate several option ids with commas, give a line by its number, and list
an order first to last. A fix question is answered by the code in the block
under its heading. Nothing else in this file is read.

what-happened: timeout-said-nothing
when-to-make-the-key: once-per-payment
retry-during-the-first: refuse-with-conflict
where-keys-live: database-table
same-key-new-body: reject-the-reuse
