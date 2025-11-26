from typing import ClassVar


class Leave:
    Types: ClassVar[dict[str, int]] = {
        "project": 0,
        "holiday": 1,
        "sick": 2,
        "special": 3,
        "unpaid": 4,
        "annual": 5,
        "unemployed": 6,
    }

    def __init__(self, interval: object, type_idx: int) -> None:
        self.interval = interval
        self.type_idx = type_idx
