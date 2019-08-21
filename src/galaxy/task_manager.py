import asyncio
import logging
from collections import OrderedDict
from itertools import count

class TaskManager:
    def __init__(self, name):
        self._name = name
        self._tasks = OrderedDict()
        self._task_counter = count()

    def create_task(self, coro, description, handle_exceptions=True):
        """Wrapper around asyncio.create_task - takes care of canceling tasks on shutdown"""

        async def task_wrapper(task_id):
            try:
                result = await coro
                logging.debug("Task manager %s: finished task %d (%s)", self._name, task_id, description)
                return result
            except asyncio.CancelledError:
                if handle_exceptions:
                    logging.debug("Task manager %s: canceled task %d (%s)", self._name, task_id, description)
                else:
                    raise
            except Exception:
                if handle_exceptions:
                    logging.exception("Task manager %s: exception raised in task %d (%s)", self._name, task_id, description)
                else:
                    raise
            finally:
                del self._tasks[task_id]

        task_id = next(self._task_counter)
        logging.debug("Task manager %s: creating task %d (%s)", self._name, task_id, description)
        task = asyncio.create_task(task_wrapper(task_id))
        self._tasks[task_id] = task
        return task

    def cancel(self):
        for task in self._tasks.values():
            task.cancel()

    async def wait(self):
        # Tasks can spawn other tasks
        while True:
            tasks = self._tasks.values()
            if not tasks:
                return
            await asyncio.gather(*tasks, return_exceptions=True)
