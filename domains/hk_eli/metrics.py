"""Versioned demonstration semantics. Live metrics are governed by reviewed view contracts."""
import json
from pathlib import Path
from pydantic import Field
from hk_platform.contracts.models import Strict

class MetricDefinition(Strict):
    metric_id:str
    business_name:str
    description:str
    formula:str
    source_fields:list[str]
    data_grain:str
    date_role:str
    currency:str
    aggregation:str
    additive:bool
    null_handling:str
    snapshot_handling:str
    approved_filters:list[str]
    business_owner:str
    version:str
    approval:str

def load_metrics():
    path=Path(__file__).with_name('metrics.json')
    records=[MetricDefinition.model_validate(v) for v in json.loads(path.read_text(encoding='utf-8'))]
    if len({r.metric_id for r in records})!=len(records):raise ValueError('Duplicate metric identity.')
    for record in records:
        if record.additive and record.aggregation in ('ratio','weighted_mean','percentage'):raise ValueError('Non-additive metric cannot be summed.')
    return {r.metric_id:r for r in records}
