import asyncio
import logging
from galaxy.api.jsonrpc import ApplicationError
from galaxy.api.errors import ImportInProgress, UnknownError

logger = logging.getLogger(__name__)


class Importer:
    def __init__(
            self,
            task_manger,
            name,
            get,
            prepare_context,
            notification_success,
            notification_failure,
            notification_finished,
            complete,
    ):
        self._task_manager = task_manger
        self._name = name
        self._get = get
        self._prepare_context = prepare_context
        self._notification_success = notification_success
        self._notification_failure = notification_failure
        self._notification_finished = notification_finished
        self._complete = complete

        self._import_in_progress = False

    async def _import_element(self, id_, context_):
        try:
            element = await self._get(id_, context_)
            self._notification_success(id_, element)
        except ApplicationError as error:
            self._notification_failure(id_, error)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Unexpected exception raised in %s importer", self._name)
            self._notification_failure(id_, UnknownError())

    async def _import_elements(self, ids_, context_):
        try:
            imports = [self._import_element(id_, context_) for id_ in ids_]
            await asyncio.gather(*imports)
            self._notification_finished()
            self._complete()
        except asyncio.CancelledError:
            logger.debug("Importing %s cancelled", self._name)
        finally:
            self._import_in_progress = False

    async def start(self, ids):
        if self._import_in_progress:
            raise ImportInProgress()

        self._import_in_progress = True
        try:
            context = await self._prepare_context(ids)
            self._task_manager.create_task(
                self._import_elements(ids, context),
                "{} import".format(self._name),
                handle_exceptions=False
            )
        except:
            self._import_in_progress = False
            raise


class CollectionImporter(Importer):
    def __init__(self, notification_partially_finished, *args):
        super().__init__(*args)
        self._notification_partially_finished = notification_partially_finished

    async def _import_element(self, id_, context_):
        try:
            async for element in self._get(id_, context_):
                self._notification_success(id_, element)
        except ApplicationError as error:
            self._notification_failure(id_, error)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Unexpected exception raised in %s importer", self._name)
            self._notification_failure(id_, UnknownError())
        finally:
            self._notification_partially_finished(id_)


class SynchroneousImporter(Importer):
    async def _import_elements(self, ids_, context_):
        try:
            for id_ in ids_:
                await self._import_element(id_, context_)
            self._notification_finished()
            self._complete()
        except asyncio.CancelledError:
            logger.debug("Importing %s cancelled", self._name)
        finally:
            self._import_in_progress = False
