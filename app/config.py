import os
import tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load_config(path=None):
    path=Path(path or os.getenv('HKELI_CONFIG',ROOT/'config/config.local.toml'))
    if not path.exists():path=ROOT/'config/config.example.toml'
    with path.open('rb') as stream:config=tomllib.load(stream)
    if config['app']['mode'] not in ('fixture','live'):raise ValueError('Use fixture or live mode.')
    for key in ('state_dir','knowledge_root'):
        value=Path(config['app'][key]);config['app'][key]=str(value.resolve() if value.is_absolute() else (ROOT/value).resolve())
    return config
