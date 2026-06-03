from debate_arena.engine import DebateConfig

def test_config_defaults():
    cfg = DebateConfig()
    assert cfg.rounds == 3
    assert cfg.word_limit == 100
    assert cfg.judge_limit == 150

def test_config_custom():
    cfg = DebateConfig(rounds=5, word_limit=75, judge_limit=125)
    assert cfg.rounds == 5
