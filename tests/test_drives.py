from tolmans_sowbug_playground.systems.drives import Drive, DriveSystem, DriveType


class TestDriveType:
    def test_enum_values(self):
        assert DriveType.HUNGER.value == "hunger"
        assert DriveType.THIRST.value == "thirst"
        assert DriveType.TEMPERATURE.value == "temperature"


class TestDrive:
    def test_creation_defaults(self):
        d = Drive(drive_type=DriveType.HUNGER)
        assert d.level == 0.0
        assert d.rate == 0.01

    def test_update_increases_level(self):
        d = Drive(DriveType.HUNGER, level=0.0, rate=0.05)
        d.update()
        assert d.level == 0.05

    def test_update_capped_at_one(self):
        d = Drive(DriveType.HUNGER, level=0.98, rate=0.05)
        d.update()
        assert d.level == 1.0

    def test_satisfy_decreases_level(self):
        d = Drive(DriveType.HUNGER, level=0.8, rate=0.01)
        d.satisfy(0.3)
        assert abs(d.level - 0.5) < 1e-9

    def test_satisfy_floored_at_zero(self):
        d = Drive(DriveType.HUNGER, level=0.2, rate=0.01)
        d.satisfy(0.5)
        assert d.level == 0.0


class TestDriveSystem:
    def test_creation_with_drives(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.5),
            Drive(DriveType.THIRST, level=0.3),
        ])
        assert ds.get_level(DriveType.HUNGER) == 0.5
        assert ds.get_level(DriveType.THIRST) == 0.3

    def test_update_all_drives(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.0, rate=0.1),
            Drive(DriveType.THIRST, level=0.0, rate=0.2),
        ])
        ds.update()
        assert ds.get_level(DriveType.HUNGER) == 0.1
        assert ds.get_level(DriveType.THIRST) == 0.2

    def test_get_most_urgent(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.3),
            Drive(DriveType.THIRST, level=0.7),
            Drive(DriveType.TEMPERATURE, level=0.1),
        ])
        urgent = ds.get_most_urgent()
        assert urgent is not None
        assert urgent.drive_type == DriveType.THIRST

    def test_get_most_urgent_empty(self):
        ds = DriveSystem()
        assert ds.get_most_urgent() is None

    def test_satisfy_specific_drive(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.8),
        ])
        ds.satisfy(DriveType.HUNGER, 0.3)
        assert abs(ds.get_level(DriveType.HUNGER) - 0.5) < 1e-9

    def test_get_levels(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.5),
            Drive(DriveType.THIRST, level=0.3),
        ])
        levels = ds.get_levels()
        assert levels == {DriveType.HUNGER: 0.5, DriveType.THIRST: 0.3}

    def test_get_level_missing_drive(self):
        ds = DriveSystem()
        assert ds.get_level(DriveType.HUNGER) == 0.0
