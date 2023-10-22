import dataclasses

@dataclasses.dataclass
class WindowArg:
    row_start: int
    row_end: int
    col_start: int
    col_end: int