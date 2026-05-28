import asyncio
import logging
from aiohttp import web

logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "Price AI"})


async def start_health_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server running on port {port}")
    return runner
