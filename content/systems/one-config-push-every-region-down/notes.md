# Config is code that skipped the deploy pipeline

## Blast radius

Every change to production has a **blast radius**: how much breaks if the
change is bad. A code deploy here had a small one by design: one canary
server, then one region, then the next, over two hours, so a bad build
hurts a few servers and is stopped. The config push had the largest
possible one: every server in every region, within seconds. The typo was
ordinary. Delivering it everywhere at once is what made it an outage.

This pattern is behind a remarkable share of large public incidents: a
configuration or policy change, propagated globally in seconds, that every
copy of the software then failed on in the same way. Config changes
production behaviour exactly as code does, and deserves the same pipeline.

## Rolling config out like code

1. **Validate before it leaves the branch.** A schema check, and loading
   the file with the real parser in CI. `2O0` fails both.
2. **Canary.** A few servers, watched for errors, restarts and latency.
3. **One region, then the rest one at a time**, each a blast radius of its
   own.
4. **Revert automatically** when a stage's health checks fail, so stopping
   does not wait for a person to notice a graph.

Review is still worth having, and it is a different control: it lowers the
chance of a bad change and does nothing about its reach.

## Fail static

A server that is running on a good config and receives one it cannot load
should **keep the good one, refuse the new one and say so**. Exiting
instead turns every server into a crash loop, because each restart reads
the same bad file. Falling back to built-in defaults, or applying the parts
that parsed, is worse in a subtler way: the server stays up and behaves
according to a combination nobody wrote.

## Recovery must not depend on what failed

The revert was found in five minutes and took forty more to apply, because
the console that applies it was served by the crashed fleet. Recovery tools
need to work when the system is down: a CLI that talks to the config store
directly, a break-glass path documented and rehearsed before it is needed.
The same reasoning keeps status pages, paging and dashboards off the
infrastructure they report on.
