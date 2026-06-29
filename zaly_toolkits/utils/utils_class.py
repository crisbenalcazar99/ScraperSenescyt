from dataclasses import dataclass
from enum import auto
from enum import Enum

@dataclass(frozen=True)
class SourceSpec:
    name: str
    db_alias_load: str
    folder_name: str
    query_file: str

class RunMode(Enum):
    INICIAL = auto()
    INCREMENTAL = auto()

class ModePersistence(Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    IGNORE = "IGNORE"