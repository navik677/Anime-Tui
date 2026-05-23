"""
Abstract base class for all anime providers.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..models import Anime, Episode, Stream


class BaseProvider(ABC):
    """All providers must implement these three methods."""

    name: str = "unknown"

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[Anime]:
        """Search for anime titles by query string."""
        ...

    @abstractmethod
    def get_episodes(self, anime: Anime) -> list[Episode]:
        """Return list of episodes for the given anime."""
        ...

    @abstractmethod
    def get_stream(self, anime: Anime, episode: Episode) -> Stream:
        """Return a Stream object with available quality options."""
        ...
