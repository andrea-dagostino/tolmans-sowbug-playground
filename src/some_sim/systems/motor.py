from enum import Enum

from some_sim.core.environment import Environment


class Direction(Enum):
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)
    STAY = (0, 0)


class MotorSystem:
    def move(
        self,
        position: tuple[int, int],
        direction: Direction,
        environment: Environment,
    ) -> tuple[int, int]:
        dx, dy = direction.value
        new_position = (position[0] + dx, position[1] + dy)
        if environment.is_within_bounds(new_position) and environment.is_passable(
            new_position
        ):
            return new_position
        return position
