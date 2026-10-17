# PID 1 is special, and the shell form puts a shell there

## What `docker stop` actually does

It sends **SIGTERM to PID 1** inside the container, waits for the grace
period (ten seconds unless `--time` or the image's `--stop-timeout` say
otherwise), then sends **SIGKILL**. It does not signal the process tree.
Whatever is PID 1 is responsible for shutting down everything under it.

## Why PID 1 ignores SIGTERM

For any other process, a signal with no handler gets the default action,
which for SIGTERM is "terminate". The kernel makes an exception for PID 1 of
a PID namespace: signals with no installed handler are **ignored**, because
an init process dying takes the whole namespace with it. Your container's
PID 1 *is* its init.

So PID 1 has to be a process that installs a SIGTERM handler. `worker.py`
does. `/bin/sh` does not.

## Shell form versus exec form

```dockerfile
CMD python -u worker.py            # shell form
CMD ["python", "-u", "worker.py"]  # exec form
```

The shell form becomes `["/bin/sh", "-c", "python -u worker.py"]`. Docker
starts the shell, and the shell starts python as a child. `docker ps` shows
it in the COMMAND column: `"/bin/sh -c 'python …"`.

One subtlety was **measured for this exercise** rather than taken from
folklore. Some shells replace themselves with the last command when that is
all there is to do. bash does: `bash -c "python w.py"` ends with python as
PID 1. On `python:3.12-slim`, `/bin/sh` is **dash 0.5.12, and dash does not**.
PID 1 stays `/bin/sh -c python w.py`, with python as PID 7. That is why the
ticket reproduces on this image, and why "it works on my alpine image" is not
evidence: different shells, different answers.

## The fixes, and the ones that are not

- **Exec form** (the reference). Python is PID 1 and gets the signal.
- **`CMD exec python -u worker.py`** also works. `exec` tells the shell to
  replace itself with python, so python ends up as PID 1. The grader models
  this, and accepts it.
- **`["sh", "-c", "python -u worker.py"]`** is exec form by its brackets and
  still a shell by its program. Same bug.
- **`STOPSIGNAL SIGKILL`** turns ten seconds into zero by killing the worker
  outright. SIGKILL cannot be handled, so the batch is half-written every time.
- **`docker stop --time 1`** shortens the wait and changes nothing else. The
  worker is still killed, just sooner.

## When PID 1 needs to be an init

Sometimes PID 1 really has to be a shell script: an entrypoint that renders a
config file, or waits for something. Two good patterns:

- end the script with `exec "$@"` (or `exec python -u worker.py`), so the
  real process replaces the script as PID 1;
- run a tiny init that forwards signals and reaps zombies: `docker run
  --init`, or `tini` installed in the image as `ENTRYPOINT ["tini", "--"]`.

Exit code 137 in `docker ps -a` is the tell: 128 + 9 means it was SIGKILLed.
A clean shutdown is usually 0, or 143 (128 + SIGTERM's 15) for a process that
lets SIGTERM's default action kill it.
