"""
Data models for anime-tui.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Quality:
    label: str        # e.g. "1080p", "720p", "480p"
    url: str          # Direct stream URL (HLS .m3u8 or .mp4)
    headers: dict = field(default_factory=dict)  # Extra HTTP headers for mpv

    def __str__(self) -> str:
        return self.label


@dataclass
class Stream:
    qualities: list[Quality] = field(default_factory=list)

    def best(self) -> Optional[Quality]:
        """Return the highest quality available."""
        for label in ("1080p", "720p", "480p", "360p"):
            for q in self.qualities:
                if q.label == label:
                    return q
        return self.qualities[0] if self.qualities else None


@dataclass
class Episode:
    number: int | str
    title: Optional[str] = None
    # Provider-specific data stored here for stream resolution
    _meta: dict = field(default_factory=dict, repr=False)

    def display(self) -> str:
        if self.title:
            return f"Серія {self.number}: {self.title}"
        return f"Серія {self.number}"


@dataclass
class Anime:
    id: str                         # Provider-specific unique ID
    title_ru: str
    title_en: Optional[str] = None
    description: Optional[str] = None
    year: Optional[int] = None
    genres: list[str] = field(default_factory=list)
    status: Optional[str] = None
    provider: Optional[str] = None  # "anilibria" | "yummyanime" | "rezka"
    _meta: dict = field(default_factory=dict, repr=False)  # Raw data from provider

    def display(self) -> str:
        parts = [self.title_ru]
        if self.title_en and self.title_en != self.title_ru:
            parts.append(f"({self.title_en})")
        if self.year:
            parts.append(f"[{self.year}]")
        if self.status:
            parts.append(f"• {self.status}")
        return " ".join(parts)
