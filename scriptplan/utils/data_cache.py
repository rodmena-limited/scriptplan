from typing import Any, ClassVar, Optional


class DataCache:
    _instance: ClassVar[Optional["DataCache"]] = None

    def __init__(self) -> None:
        self._cache: dict[tuple[Any, ...], Any] = {}

    @classmethod
    def instance(cls) -> "DataCache":
        if cls._instance is None:
            cls._instance = DataCache()
        return cls._instance

    def flush(self) -> None:
        self._cache = {}

    def cached(self, obj: Any, tag: str, *args: Any, **kwargs: Any) -> Any:
        # Simple caching implementation
        # Key based on object id, tag, and args
        key = (id(obj), tag, args, tuple(kwargs.items()))
        if key in self._cache:
            return self._cache[key]

        # If block is passed?
        # In Python, we can't pass a block like Ruby.
        # We expect the last argument or a specific argument to be a callable if used like Ruby's block.
        # But here the caller is likely doing: @dCache.cached(...) do ... end
        # In Python: dCache.cached(..., lambda: ...)
        # So the last arg might be the function to execute.

        # However, treeSumR implementation:
        # @dCache.cached(self, cacheTag, startIdx, endIdx, *args) do ... end

        # In Python `ResourceScenario.treeSumR`:
        # self.dCache.cached(self, cacheTag, startIdx, endIdx, *args, lambda: ...) ?

        # I haven't implemented treeSumR in Python yet.
        # If I did, I would pass a callable.

        # Let's assume the last argument is the callable if it's a function.
        # Or better, explicit 'calculator' argument.

        # But since I haven't implemented treeSumR fully in ResourceScenario, this is future proofing.
        return None


class FileList(list[str]):
    pass
