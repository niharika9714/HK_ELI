import asyncio
import threading
import pytest
from hk_platform.runtime.registry import SkillRegistry,Executor,SkillContext
from domains.hk_eli.skills import Skill,ArtifactInput
from hk_platform.contracts.models import ExecutionPlan,TaskSpec,UserIntent,SkillOutput

def plan(*tasks):return ExecutionPlan(intent=UserIntent(question='test'),tasks=list(tasks))

def test_validation(identity):
    r=SkillRegistry()
    async def fn(i,c):return SkillOutput()
    r.register(Skill('test','analytics',ArtifactInput,fn))
    for tasks in [
        [TaskSpec(id='a',skill_id='test',dependencies=['b']),TaskSpec(id='b',skill_id='test',dependencies=['a'])],
        [TaskSpec(id='a',skill_id='test',dependencies=['missing'])],
        [TaskSpec(id='a',skill_id='test'),TaskSpec(id='a',skill_id='test')],
        [TaskSpec(id='a',skill_id='test',parameters={'sql':'DROP'})],
        [TaskSpec(id='a',skill_id='test',skill_version='wrong')]]:
        with pytest.raises(ValueError):r.validate_dependencies(plan(*tasks),identity)
    with pytest.raises(PermissionError):r.validate_dependencies(plan(TaskSpec(id='a',skill_id='test')),identity.model_copy(update={'permissions':[]}))

def test_concurrency_and_dependencies(identity):
    r=SkillRegistry();active=0;peak=0
    async def fn(i,c):
        nonlocal active,peak
        active+=1;peak=max(active,peak);await asyncio.sleep(.03);active-=1;return SkillOutput(data={'ok':True})
    async def fail(i,c):raise ValueError('sensitive exception')
    r.register(Skill('test','analytics',ArtifactInput,fn));r.register(Skill('fail','analytics',ArtifactInput,fail))
    tasks=[TaskSpec(id=f't{i}',skill_id='test') for i in range(6)]+[TaskSpec(id='bad',skill_id='fail'),TaskSpec(id='dependent',skill_id='test',dependencies=['bad'])]
    outputs,statuses,warnings=asyncio.run(Executor(r,2).execute(plan(*tasks),SkillContext(identity,'run',{},threading.Event())))
    assert peak==2 and len(outputs)==6 and statuses['dependent']=='skipped'
    assert all('sensitive' not in w for w in warnings)

def test_timeout_cancel_and_retries(identity):
    async def scenario():
        r=SkillRegistry();calls=0
        async def flaky(i,c):
            nonlocal calls
            calls+=1
            if calls==1:raise ConnectionError()
            return SkillOutput()
        skill=Skill('flaky','analytics',ArtifactInput,flaky);skill.meta.retries=1;r.register(skill)
        _,statuses,_=await Executor(r).execute(plan(TaskSpec(id='a',skill_id='flaky')),SkillContext(identity,'r',{},threading.Event()))
        assert calls==2 and statuses['a']=='complete'
        async def slow(i,c):await asyncio.sleep(2);return SkillOutput()
        skill=Skill('slow','analytics',ArtifactInput,slow);skill.meta.timeout_seconds=.02;r.register(skill)
        _,statuses,_=await Executor(r).execute(plan(TaskSpec(id='a',skill_id='slow')),SkillContext(identity,'r',{},threading.Event()))
        assert statuses['a']=='failed'
        event=threading.Event();event.set()
        with pytest.raises(asyncio.CancelledError):await Executor(r).execute(plan(TaskSpec(id='a',skill_id='slow')),SkillContext(identity,'r',{},event))
    asyncio.run(scenario())
