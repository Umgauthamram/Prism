from openenv.core import Action, Observation, GenericEnvClient, SyncEnvClient
from models import PrismAction as BaseAction
from models import PrismObservation as BaseObservation
from models import PrismState
from typing import Dict, Any

class PrismAction(Action, BaseAction):
    pass

class PrismObservation(Observation, BaseObservation):
    pass

class PrismEnv(SyncEnvClient[PrismAction, PrismObservation, PrismState]):
    def __init__(self, base_url="http://localhost:8000"):
        async_client = GenericEnvClient(base_url=base_url)
        super().__init__(async_client=async_client)
