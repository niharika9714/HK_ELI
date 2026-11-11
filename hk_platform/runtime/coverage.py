"""Structural coverage guards, never a claim of semantic equivalence."""
import json


def parameter_at(parameters,path):
    value=parameters
    for token in path.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        if isinstance(value,dict) and token in value:value=value[token]
        elif isinstance(value,list) and token.isdigit() and int(token)<len(value):value=value[int(token)]
        else:raise ValueError('Requirement binding references an absent parameter.')
    return value


def validate_coverage(plan,question=None,expected_requirements=None):
    requirements={r.id:r for r in plan.requirements};tasks={t.id:t for t in plan.tasks}
    if len(requirements)!=len(plan.requirements):raise ValueError('Duplicate requirement IDs.')
    original=question if question is not None else plan.intent.question
    if any(r.quote not in original for r in plan.requirements):raise ValueError('Requirement quote must occur in the original question.')
    if expected_requirements is not None:
        if [r.model_dump() for r in plan.requirements]!=[r.model_dump() for r in expected_requirements]:
            raise ValueError('Planner changed or omitted the independently inventoried requirements.')
    if len({c.requirement_id for c in plan.coverage})!=len(plan.coverage):raise ValueError('Duplicate coverage records.')
    if {c.requirement_id for c in plan.coverage}!=set(requirements):raise ValueError('Each requirement needs exactly one coverage record.')
    if not plan.tasks and (not plan.coverage or any(c.status!='unresolved' for c in plan.coverage)):
        raise ValueError('Empty plans require explicit unresolved requirements.')
    for item in plan.coverage:
        if len(set(item.task_ids))!=len(item.task_ids) or not set(item.task_ids).issubset(tasks):raise ValueError('Coverage references invalid task IDs.')
        if item.status=='unresolved':
            if item.task_ids or item.bindings:raise ValueError('Unresolved requirements cannot claim execution coverage.')
            continue
        if not item.task_ids:raise ValueError('Satisfied requirement must map to a task.')
        requirement=requirements[item.requirement_id]
        if requirement.expected_value is not None and not item.bindings:raise ValueError('Concrete requirements need parameter bindings.')
        if requirement.expected_value is not None and {b.task_id for b in item.bindings}!=set(item.task_ids):
            raise ValueError('Concrete requirements need a binding for every covered task.')
        for binding in item.bindings:
            if binding.task_id not in item.task_ids:raise ValueError('Binding must reference a covered task.')
            if binding.target=='task' and binding.parameter_path!='/source_mode':raise ValueError('Task-level coverage may bind only source_mode.')
            if requirement.kind=='source' and requirement.expected_value in ('LIVE','MOCK') and (binding.target!='task' or binding.parameter_path!='/source_mode'):
                raise ValueError('Source requirements must bind the declared task source mode.')
            actual=parameter_at(tasks[binding.task_id].model_dump() if binding.target=='task' else tasks[binding.task_id].parameters,binding.parameter_path)
            if requirement.expected_value is not None and json.dumps(actual,sort_keys=True,allow_nan=False)!=json.dumps(requirement.expected_value,sort_keys=True,allow_nan=False):
                raise ValueError('Task parameter does not preserve the requested requirement value.')
