"""Private bank SDK call contract supplied by the user; no public SDK substitution."""
import asyncio
import importlib
import inspect
from .stork_config import credentials


async def generate_async(settings,prompt):
    resolved=credentials(settings)
    adapter=settings.get('adapter','app.integrations.vertex_adapter:generate')
    if adapter not in ('app.integrations.vertex_adapter:generate','app.integrations.vertex_adapter:generate_async'):
        module,name=adapter.split(':',1)
        function=getattr(importlib.import_module(module),name)
        # A synchronous legacy adapter may call asyncio.run; run it outside this event loop.
        arguments=({**settings,**resolved},prompt)
        if inspect.iscoroutinefunction(function):
            result=await asyncio.wait_for(function(*arguments),settings['timeout_seconds'])
        else:
            result=await asyncio.wait_for(asyncio.to_thread(function,*arguments),settings['timeout_seconds'])
        if not isinstance(result,str):raise ValueError('Stork adapter must return response text.')
        return result
    from ada_genai.google_genai import VertexClient
    # Credentials/SSL are provisioned in process environment before constructing the SDK.
    # Preserve the user's private SDK singular `content` argument.
    client=VertexClient()
    response=await asyncio.wait_for(client.aio.models.generate_content(
        model=settings['model'],content=prompt),timeout=settings['timeout_seconds'])
    return response.text


def generate(settings,prompt):
    """Compatibility entry point for synchronous callers outside an active event loop."""
    return asyncio.run(generate_async(settings,prompt))
