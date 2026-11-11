from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import asyncio
import threading
from ..contracts.errors import PublicError
from ..contracts.models import Identity, SkillMetadata, SkillOutput, ExecutionPlan
from .coverage import validate_coverage


@dataclass
class SkillContext:
    identity: Identity
    run_id: str
    services: dict
    cancelled: object
    outputs: dict = field(default_factory=dict)


class BaseSkill(ABC):
    @abstractmethod
    def metadata(self) -> SkillMetadata: ...

    @abstractmethod
    async def execute(self, inputs, context: SkillContext) -> SkillOutput: ...


def require(identity, permissions):
    if not set(permissions).issubset(identity.permissions):
        raise PermissionError('Skill permission denied.')


def resource(identity, key):
    if key not in identity.resources:
        raise PermissionError('Resource is outside the authorized scope.')


class SkillRegistry:
    def __init__(self):
        self.skills = {}

    def register(self, skill):
        meta = skill.metadata()
        key = (meta.id, meta.version)
        if key in self.skills:
            raise ValueError('Duplicate skill version.')
        self.skills[key] = skill

    def resolve(self, name, version='1.0.0'):
        if (name, version) not in self.skills:
            raise ValueError('Unknown skill/version.')
        return self.skills[name, version]

    def list_authorized(self, identity):
        return [s.metadata() for s in self.skills.values() if set(s.metadata().permissions).issubset(identity.permissions)]

    def validate_dependencies(self, plan: ExecutionPlan, identity):
        validate_coverage(plan)
        ids = [t.id for t in plan.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate task IDs.')
        pending = {t.id: set(t.dependencies) for t in plan.tasks}
        for assessment in plan.source_assessments:
            if not set(assessment.task_ids).issubset(ids):raise ValueError('Assessment references unknown tasks.')
            if assessment.match=='complete_match' and assessment.remaining_gaps:
                raise ValueError('Complete match cannot have unmet requirements.')
        for task in plan.tasks:
            skill = self.resolve(task.skill_id, task.skill_version)
            require(identity, skill.metadata().permissions)
            if task.source_mode and task.source_mode not in skill.metadata().source_modes:raise ValueError('Task source mode is unsupported by this skill.')
            skill.input_model.model_validate(task.parameters)
            source = task.parameters.get('source_task')
            if source and source not in task.dependencies:
                raise ValueError('Input task must be declared as dependency.')
            if source:
                upstream=next(t for t in plan.tasks if t.id==source)
                if task.source_mode and upstream.source_mode and task.source_mode!=upstream.source_mode:
                    raise ValueError('Derived task cannot relabel its input source mode.')
            if task.expected_output != 'SkillOutput':
                raise ValueError('Unsupported expected output type.')
            if len(task.dependencies) != len(set(task.dependencies)) or not set(task.dependencies).issubset(ids):
                raise ValueError('Invalid dependency IDs.')
        while pending:
            ready = {k for k, deps in pending.items() if not deps}
            if not ready:
                raise ValueError('Dependency cycle.')
            pending = {k: deps-ready for k, deps in pending.items() if k not in ready}


class Executor:
    def __init__(self, registry, concurrency=8, timeout=120):
        self.registry, self.concurrency, self.timeout = registry, concurrency, timeout
        self.slots = threading.BoundedSemaphore(concurrency)

    async def execute(self, plan, context, progress=None):
        self.registry.validate_dependencies(plan, context.identity)
        semaphore = asyncio.Semaphore(self.concurrency)
        pending = {t.id: t for t in plan.tasks}
        statuses, outputs, warnings = {}, {}, []

        async def execute_task(task):
            skill = self.registry.resolve(task.skill_id, task.skill_version)
            meta = skill.metadata()
            require(context.identity, meta.permissions)
            async with semaphore:
                while not self.slots.acquire(blocking=False):
                    if context.cancelled.is_set():raise asyncio.CancelledError()
                    await asyncio.sleep(.02)
                try:return await invoke(task,skill,meta)
                finally:self.slots.release()

        async def invoke(task,skill,meta):
                if context.cancelled.is_set():
                    raise asyncio.CancelledError()
                if progress: progress(task.id, 'running')
                for attempt in range(meta.retries+1):
                    try:
                        value = await asyncio.wait_for(skill.execute(skill.input_model.model_validate(task.parameters), context), meta.timeout_seconds)
                        value=SkillOutput.model_validate(value)
                        modes={e.source_mode for e in value.evidence}|{v['source_mode'] for v in value.visualizations if v.get('source_mode')}
                        if value.data.get('source_mode'):modes.add(value.data['source_mode'])
                        if task.source_mode and modes-{task.source_mode}:raise ValueError('Output source mode differs from the declared branch.')
                        return task.id,value,None
                    except (ConnectionError, TimeoutError) as error:
                        if not meta.idempotent or attempt == meta.retries:
                            return task.id, None, type(error).__name__
                    except PermissionError:
                        raise
                    except PublicError as error:
                        return task.id,None,error.code+': '+str(error)
                    except Exception as error:
                        # Never leak exception messages that can contain source credentials or raw records.
                        return task.id, None, type(error).__name__

        async def monitor():
            while not context.cancelled.is_set():await asyncio.sleep(.05)
            raise asyncio.CancelledError()

        watcher=asyncio.create_task(monitor())
        runner=asyncio.current_task()
        watcher.add_done_callback(lambda t: runner.cancel() if t.cancelled() and context.cancelled.is_set() else None)
        try:
          async with asyncio.timeout(self.timeout):
            while pending:
                if context.cancelled.is_set():
                    raise asyncio.CancelledError()
                ready = [t for t in pending.values() if all(d in statuses for d in t.dependencies)]
                execute = []
                for task in ready:
                    del pending[task.id]
                    if any(statuses[d] != 'complete' for d in task.dependencies):
                        statuses[task.id] = 'skipped'
                        warnings.append(task.id+': dependency unavailable')
                        if progress: progress(task.id, 'skipped')
                    else:
                        execute.append(task)
                for key, output, error in await asyncio.gather(*(execute_task(t) for t in execute)):
                    statuses[key] = 'complete' if output and output.status == 'complete' else 'partial' if output else 'failed'
                    if output: outputs[key] = output
                    if error: warnings.append(key+': '+error)
                    if progress: progress(key, statuses[key])
                context.outputs.update(outputs)
        finally:
            watcher.cancel()
        return outputs, statuses, warnings
