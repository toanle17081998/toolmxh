import unittest
from collections import Counter


class ScenarioGeneratorTest(unittest.TestCase):
    def test_scenario_has_events_and_action_in_first_five_seconds(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        scenario = ScenarioGenerator().generate(SimulationConfig(duration=60, seed=42))
        self.assertEqual(scenario.mode, 'simulation_video')
        self.assertLess(scenario.sections[0].start / scenario.speed, 5)
        self.assertTrue(scenario.events)
        self.assertEqual(scenario.vehicle['type'], 'brick_basic_car')


class SeedReproducibilityTest(unittest.TestCase):
    def test_seed_repeats_scenario_but_different_seed_changes_it(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        generator = ScenarioGenerator()
        a = generator.generate(SimulationConfig(duration=180, seed=847291))
        b = generator.generate(SimulationConfig(duration=180, seed=847291))
        c = generator.generate(SimulationConfig(duration=180, seed=847292))
        self.assertEqual(a.model_dump(), b.model_dump())
        self.assertNotEqual(a.model_dump(), c.model_dump())


class SegmentPlannerTest(unittest.TestCase):
    def test_custom_and_long_duration_have_exact_frames_and_continuity(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        for duration in (30, 31, 60, 180, 300, 600, 1800):
            scenario = ScenarioGenerator().generate(SimulationConfig(duration=duration, seed=7))
            self.assertEqual(sum(s.frame_count for s in scenario.segments), duration * scenario.fps)
            self.assertTrue(all(s.frame_count <= 30 * scenario.fps for s in scenario.segments))
            for left, right in zip(scenario.segments, scenario.segments[1:]):
                self.assertEqual(left.end_state, right.start_state)
                self.assertEqual(left.start_frame + left.frame_count, right.start_frame)
            self.assertEqual(scenario.segments[-1].end_state.progress, 1)


class ObstacleSelectionTest(unittest.TestCase):
    def test_long_course_avoids_consecutive_and_window_repetition(self):
        from app.simulation.models import SimulationConfig
        from app.simulation.scenario import ScenarioGenerator
        scenario = ScenarioGenerator().generate(SimulationConfig(duration=600, seed=6))
        types = [s.type for s in scenario.sections]
        self.assertTrue(all(a != b for a, b in zip(types, types[1:])))
        for start in range(len(types)):
            self.assertLessEqual(max(Counter(types[start:start+8]).values()), 2)
        self.assertEqual(len(set(types)), 5)
        self.assertGreater(max(s.difficulty for s in scenario.sections), scenario.sections[0].difficulty)


class TrackGeneratorTest(unittest.TestCase):
    def test_validation_rejects_overlap_spawn_boundaries_and_gap(self):
        from app.simulation.track import SimulationTrackGenerator, validateTrack
        sections = SimulationTrackGenerator().generate(60, 2, 'colorful_toy_world', 12)
        self.assertTrue(validateTrack(sections, 60 * 3.0))
        for change in ({'start': -1}, {'start': 0.1}, {'width': 0.1}, {'gap': 10}):
            damaged = [s.model_copy(deep=True) for s in sections]
            for key, value in change.items():
                setattr(damaged[0], key, value)
            with self.assertRaises(ValueError):
                validateTrack(damaged, 60 * 3.0)
        damaged = [s.model_copy(deep=True) for s in sections]
        damaged[1].start = damaged[0].start
        with self.assertRaises(ValueError):
            validateTrack(damaged, 60 * 3.0)

    def test_plugin_profiles_return_to_ground_at_boundaries(self):
        from app.simulation.obstacles import OBSTACLES
        from app.simulation.track import SimulationTrackGenerator
        for section in SimulationTrackGenerator().generate(180, 2, 'colorful_toy_world', 8):
            plugin = OBSTACLES[section.type](section.model_dump())
            self.assertEqual(plugin.height_at(section.start, 0), 0)
            self.assertAlmostEqual(plugin.height_at(section.start + section.length, 0), 0)
            self.assertTrue(plugin.validate())


if __name__ == '__main__':
    unittest.main()
