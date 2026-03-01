from dataclasses import dataclass
from enum import Enum


class DriveType(Enum):
    HUNGER = "hunger"
    THIRST = "thirst"
    TEMPERATURE = "temperature"


@dataclass
class Drive:
    drive_type: DriveType
    level: float = 0.0
    rate: float = 0.01
    satiety: float = 0.0
    satiety_decay_rate: float = 0.05

    def update(self) -> None:
        self.satiety *= (1.0 - self.satiety_decay_rate)
        effective_rate = self.rate * (1.0 - self.satiety)
        self.level = min(1.0, self.level + effective_rate)

    def satisfy(self, amount: float) -> None:
        self.level = max(0.0, self.level - amount)
        self.satiety = min(1.0, self.satiety + amount)


class DriveSystem:
    def __init__(self, drives: list[Drive] | None = None) -> None:
        self.drives: dict[DriveType, Drive] = {}
        for d in (drives or []):
            self.drives[d.drive_type] = d

    def update(self) -> None:
        for drive in self.drives.values():
            drive.update()

    def get_most_urgent(self) -> Drive | None:
        if not self.drives:
            return None
        return max(self.drives.values(), key=lambda d: d.level)

    def satisfy(self, drive_type: DriveType, amount: float) -> None:
        if drive_type in self.drives:
            self.drives[drive_type].satisfy(amount)

    def get_level(self, drive_type: DriveType) -> float:
        if drive_type in self.drives:
            return self.drives[drive_type].level
        return 0.0

    def get_levels(self) -> dict[DriveType, float]:
        return {dt: d.level for dt, d in self.drives.items()}

    def get_satiety_levels(self) -> dict[DriveType, float]:
        return {dt: d.satiety for dt, d in self.drives.items()}
