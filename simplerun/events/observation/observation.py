from dataclasses import dataclass

from simplerun.events.event import Event


@dataclass
class Observation(Event):
    content: str
