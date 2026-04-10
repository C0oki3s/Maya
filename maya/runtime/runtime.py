from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class SandboxInfo:
    workspace_id: str
    server_url: str
    auth_token: str
    agent_id: str


class Runtime(ABC):
    @abstractmethod
    def create_sandbox(
        self,
        agent_id: str,
        auth_token: str,
        local_sources: list[str] | None = None,
        host_gateway: str = "host.docker.internal",
    ) -> SandboxInfo:
        raise NotImplementedError

    @abstractmethod
    def destroy_sandbox(self, agent_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def destroy_all(self) -> None:
        raise NotImplementedError
