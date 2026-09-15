---
name: arch-scaffold-worker
description: Create a worker role the way the Software Design and Architecture Guidelines prescribe: a claim-lease-handle-complete loop over the table-backed work queue, a handler interface and impl calling managers through the container, lease renewal and self-fencing, drain-first shutdown, the maintenance sweep, the console entry point, the Dockerfile, and tests. Python only.
allowed-tools: Read Grep Glob Write Edit Bash(make *) Bash(uv run *) Bash(ls *) Bash(git status *) Bash(git diff *)
---

# arch-scaffold-worker

Follow `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` first.
Sections that shape this skill: 11 (Worker Roles), 9 (Topics,
Idempotency), 10 (Long-Running Orchestrations), 16 (The App Container)
of `${CLAUDE_SKILL_DIR}/../../architecture.md`.

## Input

`$ARGUMENTS`: `<worker-name> <WorkKind> [--queue <name>]`. Example:
`shipment-notifier SHIPMENT_NOTIFY`. The queue defaults to `default`.
When the work queue itself does not exist yet in the object model, this
skill creates it first (the `WorkItem` entity, its table in the `queue`
role, the claim, complete, defer, extend, and requeue-stale storage and
manager operations), then the worker.

## Files

Under `workers/<worker-name>/`:

| File                                     | Holds                                                                  |
|------------------------------------------|------------------------------------------------------------------------|
| `pyproject.toml`                         | the distribution and a console entry point                             |
| `src/<root>/workers/<worker>/main.py`    | settings, container, `run_forever()`, stop handlers, `serve` subcommand |
| `src/<root>/workers/<worker>/handler.py` | `<Kind>HandlerInterface.handle(ctx, item)` and `<Kind>HandlerImpl` taking managers by interface |
| `src/<root>/workers/<worker>/loop.py`    | the loop: claim within capacity, run each item as a task with lease renewal, self-fence when renewal fails, complete or requeue, sweep on a timer |
| `tests/test_handler.py`                  | the handler over the memory container, run twice with the same item to prove idempotency |
| `tests/test_loop.py`                     | claim, lease renewal, lease loss cancels the task, drain on stop       |
| `deployment/docker/<worker>.Dockerfile`  | same shape as a service image, no exposed port                         |

Changed: the root workspace members, the `WorkKind` enum, the local
dev script that starts processes, and the compose file when relevant.

## Procedure

1. Read the existing worker, if any, and mirror its settings names,
   lease length, heartbeat interval, and capacity flag.
2. The handler rebuilds the enqueuer's principal from the work item
   under the service role, through the manager operation that exists
   for it; it never constructs a context by hand.
3. The loop wakes on the `WORK_AVAILABLE` topic and falls back to a
   short poll. It never runs more items than its capacity.
4. Shutdown drains first: cancel tasks, return items to the queue with
   a note, then stop the heartbeat, then mark offline.
5. The maintenance sweep is a method the loop calls on a timer; every
   step in it is idempotent and wrapped so one failure does not stop
   the rest.
6. Run the fast gate and the worker's tests.

## Output

The file list and command outcomes, as the conventions state.
