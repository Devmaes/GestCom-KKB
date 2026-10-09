"""Strongly typed, database-independent data transfer objects."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    sku: str
    name: str
    unit_price: int
    unit_cost: int
    stock: int
    reorder_level: int
    active: bool

    @property
    def margin(self) -> int:
        return self.unit_price - self.unit_cost


@dataclass(frozen=True, slots=True)
class CartLine:
    product_id: int
    quantity: int


@dataclass(frozen=True, slots=True)
class SaleResult:
    id: int
    subtotal: int
    discount: int
    total: int
    estimated_margin: int


@dataclass(frozen=True, slots=True)
class Metrics:
    sales_count: int
    revenue: int
    estimated_margin: int
    items_sold: int
    low_stock_count: int
