"""Run periodically on the single instance; deletes only expired app-owned artifacts."""
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import load_config
from hk_platform.runtime.database import connect
from services.artifacts.service import ArtifactService
if __name__=='__main__':
    config=load_config();root=Path(config['app']['state_dir'])
    ArtifactService(root/'artifacts',root/'jobs.sqlite').cleanup()
    # Avoid constructing Conversations here: startup recovery is reserved for the app process.
    with connect(root/'jobs.sqlite') as db:
        db.execute('DELETE FROM turns WHERE conversation IN (SELECT id FROM conversations WHERE expires<?)',(time.time(),))
        db.execute('DELETE FROM conversations WHERE expires<?',(time.time(),))
        db.execute("DELETE FROM jobs WHERE expires<? AND status NOT IN ('pending','running')",(time.time(),))
        db.execute('DELETE FROM audit WHERE recorded<?',(time.time()-86400*30,))
