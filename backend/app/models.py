"""Model request/response (Pydantic v2)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

ChartType = Literal["line", "area", "bar", "barh", "donut", "scatter", "waterfall"]
Agg = Literal["SUM", "AVG", "COUNT", "MIN", "MAX"]


class Measure(BaseModel):
    column: str
    sign: int = 1


class ChartSpec(BaseModel):
    chart_type: ChartType
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    aggregation: Agg = "SUM"
    top_n: Optional[int] = Field(default=None, ge=1, le=100)
    measures: Optional[list[Measure]] = None


class DateFilter(BaseModel):
    column: str
    start: Optional[str] = None
    end: Optional[str] = None


class CatFilter(BaseModel):
    column: str
    values: list[str] = Field(default_factory=list)


class Filters(BaseModel):
    date: Optional[DateFilter] = None
    categories: list[CatFilter] = Field(default_factory=list)


class BatchItem(ChartSpec):
    id: str


class BatchQuery(BaseModel):
    dataset_id: str
    items: list[BatchItem]
    filters: Filters = Field(default_factory=Filters)


class SingleQuery(BaseModel):
    dataset_id: str
    spec: ChartSpec
    filters: Filters = Field(default_factory=Filters)


class ShareBatchQuery(BaseModel):
    items: list[BatchItem]
    filters: Filters = Field(default_factory=Filters)


class AskRequest(BaseModel):
    dataset_id: str
    question: str = Field(min_length=2, max_length=500)
    filters: Filters = Field(default_factory=Filters)


class ShareRequest(BaseModel):
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)
