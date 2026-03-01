import csv
import json
import tempfile

from tolmans_sowbug_playground.agents.sowbug import Sowbug
from tolmans_sowbug_playground.analysis.recorder import Recorder
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType


class TestRecorder:
    def _make_setup(self):
        env = Environment(width=10, height=10)
        food = Stimulus(StimulusType.FOOD, (3, 3), intensity=1.0, radius=5.0)
        env.add_stimulus(food)
        agent = Sowbug(position=(5, 5))
        recorder = Recorder(run_id="test_run")
        return env, agent, recorder

    def test_record_tick(self):
        env, agent, recorder = self._make_setup()
        recorder.record_tick(tick=0, agents=[agent], environment=env)
        assert len(recorder.records) == 1
        record = recorder.records[0]
        assert record["tick"] == 0
        assert "agents" in record
        assert "stimuli" in record

    def test_save_json(self):
        env, agent, recorder = self._make_setup()
        recorder.record_tick(tick=0, agents=[agent], environment=env)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        recorder.save_json(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["records"]) == 1
        assert data["run_id"] == "test_run"

    def test_save_csv(self):
        env, agent, recorder = self._make_setup()
        recorder.record_tick(tick=0, agents=[agent], environment=env)
        recorder.record_tick(tick=1, agents=[agent], environment=env)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        recorder.save_csv(path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert "tick" in rows[0]
        assert "position_x" in rows[0]
        assert "hunger" in rows[0]
