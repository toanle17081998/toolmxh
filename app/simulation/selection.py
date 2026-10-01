from collections import Counter


class ObstacleSelector:
    def __init__(self, rng, names, window=8, limit=2):
        self.rng, self.names = rng, list(names)
        self.window, self.limit = window, limit
        self.recent = []

    def choose(self, difficulty, vehicle, theme, segment_index):
        counts = Counter(self.recent[-(self.window - 1):])
        choices = [n for n in self.names if (not self.recent or n != self.recent[-1]) and counts[n] < self.limit]
        if not choices:
            raise ValueError('Repetition rules leave no available obstacles')
        # Hard courses favor moving mechanisms without overriding repetition rules.
        weights = [1 + (difficulty - 1) * 0.4 if n in ('hammer', 'rotating_bar', 'moving_platform') else 1 for n in choices]
        selected = self.rng.choices(choices, weights=weights, k=1)[0]
        self.recent.append(selected)
        return selected
