from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenRegion:
    name: str
    x: int
    y: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)
