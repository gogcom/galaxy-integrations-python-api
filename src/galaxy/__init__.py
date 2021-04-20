import logging


logging.getLogger(__name__).setLevel(logging.INFO)

__path__: str = __import__('pkgutil').extend_path(__path__, __name__)  # type: ignore
