from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    raw: str
    name: str
    host: str
    port: int
