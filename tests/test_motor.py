from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType
from tolmans_sowbug_playground.systems.motor import Direction, MotorSystem


class TestDirection:
    def test_direction_values(self):
        assert Direction.NORTH.value == (0, -1)
        assert Direction.SOUTH.value == (0, 1)
        assert Direction.EAST.value == (1, 0)
        assert Direction.WEST.value == (-1, 0)
        assert Direction.STAY.value == (0, 0)


class TestMotorSystem:
    def test_move_north(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.NORTH, env)
        assert new_pos == (5, 4)

    def test_move_south(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.SOUTH, env)
        assert new_pos == (5, 6)

    def test_move_east(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.EAST, env)
        assert new_pos == (6, 5)

    def test_move_west(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.WEST, env)
        assert new_pos == (4, 5)

    def test_stay(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.STAY, env)
        assert new_pos == (5, 5)

    def test_blocked_by_boundary_north(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 0), Direction.NORTH, env)
        assert new_pos == (5, 0)

    def test_blocked_by_boundary_west(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((0, 5), Direction.WEST, env)
        assert new_pos == (0, 5)

    def test_blocked_by_obstacle(self):
        env = Environment(width=10, height=10)
        wall = Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0)
        env.add_stimulus(wall)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.NORTH, env)
        assert new_pos == (5, 5)
