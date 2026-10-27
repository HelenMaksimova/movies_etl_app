from logging import Logger
from math import cos, log, pi, sqrt
from random import random
from time import sleep
from typing import Any, Callable

__all__ = (
    "backoff",
    "exceptions_handler",
)


class _WithLoggerDecorator:
    """Базовый класс-декоратор с методами для установки логгера"""

    def __init__(self, logger: Logger | None = None):
        self._logger = logger

    @property
    def logger(self):
        if self._logger:
            return self._logger

        raise ValueError(f"[{self.__class__.__name__}] Logger was not set")

    def _set_logger(self, *args):
        if args:
            app = getattr(args[0], "app", None)
            if app:
                self._logger = getattr(app, "_logger", self._logger)
            else:
                self._logger = getattr(args[0], "_logger", self._logger)


class exceptions_handler(_WithLoggerDecorator):
    """Декоратор для перехвата ошибок приложения"""

    def __call__(self, callable_obj: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            self._set_logger(*args)

            try:
                return callable_obj(*args, **kwargs)
            except KeyboardInterrupt:
                raise
            except Exception as err:
                self.logger.error(err)
                return None

        return wrapper


class backoff(_WithLoggerDecorator):
    """Декоратор для реализации экспоненциальных задержек
    при повторных запросах к сервисам"""

    def __init__(
        self,
        start: float = 0.5,
        factor: int = 2,
        cap: float = 10.0,
        tries: int = 10,
        jitter: float = 0.1,
        exceptions: set[type[Exception]] | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.start: float = start
        self.factor: int = factor
        self.cap: float = cap
        self.tries: int = tries
        self.exceptions: set[Exception] = exceptions or set()
        self.jitter: float = jitter

    def __call__(self, callable_obj: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            self._set_logger(*args)
            failures = 0
            backoff = self.start

            while failures < self.tries:
                try:
                    return callable_obj(*args, **kwargs)
                except Exception as err:
                    if type(err) in self.exceptions:
                        self.logger.error(err)
                    else:
                        raise

                sleep(backoff)

                failures += 1
                if backoff < self.cap:
                    backoff = self.start * self.factor**failures
                backoff += self._get_jitter(backoff)

            return callable_obj(*args, **kwargs)

        return wrapper

    def _get_jitter(self, delay: float) -> float:
        u1 = random()
        u2 = random()
        return sqrt(-2 * log(u1)) * cos(2 * pi * u2) * delay * self.jitter
