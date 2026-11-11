"""Private bank SDK call contract supplied by the user; no public SDK substitution."""
import asyncio


async def generate_async(settings,prompt):
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
