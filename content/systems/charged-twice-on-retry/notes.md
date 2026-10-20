# A timeout is not a failure

## What the app knew

When a request times out, the client knows one thing: it has no answer yet.
The request may never have arrived, may be running, or may have finished with
the answer lost on the way back. Retrying a request that changes something
is only safe if the server can tell the retry from a new request, and here it
could not, so a slow provider turned every retry into a second charge.

## Idempotency keys

The client creates a key **once per intent**, when the customer presses Pay,
stores it with the pending payment, and sends it on every attempt
(`Idempotency-Key: 6f1c…`). The server:

1. Inserts the key into a table with a unique constraint, together with a
   fingerprint of the request (method, path, body hash), marked in progress.
   The insert is the race: two concurrent requests with one key cannot both
   succeed.
2. If the key already exists:
   - **in progress:** answer 409 and let the client retry later;
   - **completed, same fingerprint:** return the stored response, charging
     nothing;
   - **different fingerprint:** reject it, because the key was reused for a
     different request.
3. Does the work, then stores the response against the key.

Keys need a lifetime longer than any client will retry (Stripe keeps them for
24 hours), and the store must be shared by every instance and survive a
deploy, which in practice means the database.

## The provider call is the hard part

The charge happens at a third party, outside the database transaction. If
the server crashes between charging and recording, the key says "in
progress" forever. The robust version passes the same key *on* to the
provider (most card APIs accept one), so a recovery job can safely repeat the
charge and get the original result back. Idempotency has to hold at every hop
that can be retried.
