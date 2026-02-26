from pydantic import BaseModel


class Chunk(BaseModel):
    file: str
    line_start: int
    line_end: int
    text: str


class MemoryAtom(BaseModel):
    id: str
    type: str
    summary: str
    source_file: str
    source_line_start: int
    source_line_end: int
