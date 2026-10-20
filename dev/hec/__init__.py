"""Home Energy Controller – release metadata loaded once at startup."""
import json
from pathlib import Path

RELEASES = json.loads(Path(__file__).with_name('releases.json').read_text(encoding='utf-8'))
__version__ = RELEASES['current']
