"""Resolve the working older app's credential contract without logging its values."""
import os
from pathlib import Path


def credentials(settings):
    resolved={}
    for key in ('one_bank_id','one_bank_password','ssl_cert_file'):
        name=settings.get(key+'_env')
        if not name:continue
        value=os.getenv(name,'')
        if not value.strip():raise ValueError('Stork environment setting is missing: '+name)
        if key=='ssl_cert_file' and not Path(value).is_file():
            raise ValueError('Stork SSL certificate path is not a readable file.')
        resolved[key]=value
    return resolved
