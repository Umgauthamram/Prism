import httpx
import asyncio
from typing import Optional
from models import PrismAction, PrismObservation, PrismState


class PrismEnvClient:
    """
    Typed HTTP client for the prism RL environment.
    Follows the OpenEnv client pattern.

    Usage (async):
        async with PrismEnvClient("https://gauthamram-prism.hf.space") as env:
            obs = await env.reset(seed=42, options={
                "task_domain": "debug",
                "agents": 2,
                "failure_rate": 0.0
            })
            result = await env.step(PrismAction(tool="checkpoint", args={}))

    Usage (sync):
        env = PrismEnvClient("http://localhost:7860").sync()
        obs = env.reset()
        result = env.step(PrismAction(tool="research_web", args={"q": "test"}))
    """

    DEFAULT_URL = "https://gauthamram-prism.hf.space"

    def __init__(self, base_url: str = DEFAULT_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._episode_id: Optional[str] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def reset(
        self,
        seed: int = 42,
        options: Optional[dict] = None
    ) -> PrismObservation:
        """Start a new episode. Returns the first observation."""
        if options is None:
            options = {"task_domain": "debug", "agents": 2, "failure_rate": 0.0}
        resp = await self._client.post("/reset", json={
            "seed": seed, "options": options
        })
        resp.raise_for_status()
        data = resp.json()
        self._episode_id = data.get("episode_id")
        return PrismObservation(**data)

    async def step(self, action: PrismAction) -> tuple:
        """
        Execute one action. Returns (observation, reward, terminated, truncated, info).
        Follows the Gymnasium step() convention.
        """
        resp = await self._client.post("/step", json={
            "action": action.model_dump(),
            "episode_id": self._episode_id
        })
        resp.raise_for_status()
        data = resp.json()
        obs = PrismObservation(**data["observation"])
        reward: float = data["reward"]
        terminated: bool = data["terminated"]
        truncated: bool = data["truncated"]
        info: dict = data["info"]
        return obs, reward, terminated, truncated, info

    async def state(self) -> PrismState:
        """Get full internal episode state."""
        resp = await self._client.get("/state")
        resp.raise_for_status()
        return PrismState(**resp.json())

    async def health(self) -> dict:
        """Check if environment is online."""
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def sync(self):
        """Return a synchronous wrapper for non-async contexts."""
        return _SyncWrapper(self)


class _SyncWrapper:
    """Synchronous wrapper around PrismEnvClient for simple scripts."""
    def __init__(self, client: PrismEnvClient):
        self._client = client
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(client.__aenter__())

    def reset(self, seed: int = 42, options: Optional[dict] = None):
        return self._loop.run_until_complete(
            self._client.reset(seed, options)
        )

    def step(self, action: PrismAction):
        return self._loop.run_until_complete(self._client.step(action))

    def state(self):
        return self._loop.run_until_complete(self._client.state())

    def close(self):
        self._loop.run_until_complete(self._client.__aexit__(None, None, None))
        self._loop.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
