"""SQLite access layer with explicit transactions and audit trail.

Amounts are nonnegative INTEGER FCFA. Estimated margin is not accounting profit.
All inventory-changing operations run in BEGIN IMMEDIATE transactions to prevent
negative stock and to keep sales/stock movements consistent.
"""
from __future__ import annotations

import csv
import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

from .models import CartLine, Metrics, Product, SaleResult


class BusinessError(ValueError):
    """User-facing rule violation; the UI can show its message directly."""


def default_database_path() -> Path:
    override = os.environ.get("GESTCOM_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        home = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    else:
        home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return home / "gestcom-kkb" / "gestcom.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _integer(value: int, *, minimum: int, name: str) -> int:
    if type(value) is not int or value < minimum:
        raise BusinessError(f"{name} doit être un entier supérieur ou égal à {minimum}.")
    return value


def _label(value: str, *, name: str, limit: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise BusinessError(f"{name} doit contenir entre 1 et {limit} caractères.")
    return value.strip()


def _spreadsheet_safe(value: object) -> object:
    """Prevent CSV formula execution by spreadsheet applications."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else default_database_path()
        self.path = self.path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 10000")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def _initialize(self) -> None:
        with self._connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    name TEXT NOT NULL,
                    unit_price INTEGER NOT NULL CHECK (unit_price > 0),
                    unit_cost INTEGER NOT NULL CHECK (unit_cost >= 0),
                    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
                    reorder_level INTEGER NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    subtotal INTEGER NOT NULL CHECK (subtotal >= 0),
                    discount INTEGER NOT NULL CHECK (discount >= 0),
                    total INTEGER NOT NULL CHECK (total >= 0),
                    estimated_margin INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'valid' CHECK (status IN ('valid','cancelled')),
                    cancelled_at TEXT
                );
                CREATE TABLE IF NOT EXISTS sale_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL REFERENCES sales(id),
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    sku TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                    unit_cost INTEGER NOT NULL CHECK (unit_cost >= 0),
                    line_total INTEGER NOT NULL CHECK (line_total >= 0)
                );
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    delta INTEGER NOT NULL CHECK(delta <> 0),
                    reason TEXT NOT NULL,
                    sale_id INTEGER REFERENCES sales(id),
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_sales_date ON sales(created_at);
                CREATE INDEX IF NOT EXISTS ix_lines_sale ON sale_lines(sale_id);
                CREATE INDEX IF NOT EXISTS ix_stock_product ON stock_movements(product_id);
            """)

    @staticmethod
    def _product(row: sqlite3.Row) -> Product:
        return Product(
            id=int(row["id"]), sku=row["sku"], name=row["name"],
            unit_price=int(row["unit_price"]), unit_cost=int(row["unit_cost"]),
            stock=int(row["stock"]), reorder_level=int(row["reorder_level"]),
            active=bool(row["active"]),
        )

    def products(self, *, include_inactive: bool = False, query: str = "") -> list[Product]:
        query = query.strip()
        conditions = []
        params: list[object] = []
        if not include_inactive:
            conditions.append("active = 1")
        if query:
            conditions.append("(sku LIKE ? OR name LIKE ?)")
            params.extend((f"%{query}%", f"%{query}%"))
        sql = "SELECT * FROM products" + (" WHERE " + " AND ".join(conditions) if conditions else "") + " ORDER BY name COLLATE NOCASE, id"
        with self._connection() as db:
            return [self._product(row) for row in db.execute(sql, params)]

    def get_product(self, product_id: int) -> Product:
        with self._connection() as db:
            row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise BusinessError("Article introuvable.")
        return self._product(row)

    def add_product(self, sku: str, name: str, price: int, cost: int, stock: int = 0, reorder_level: int = 5) -> int:
        sku = _label(sku, name="La référence", limit=40)
        name = _label(name, name="Le nom")
        price = _integer(price, minimum=1, name="Le prix de vente")
        cost = _integer(cost, minimum=0, name="Le prix d'achat")
        stock = _integer(stock, minimum=0, name="Le stock")
        reorder_level = _integer(reorder_level, minimum=0, name="Le seuil d'alerte")
        with self._transaction() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO products(sku,name,unit_price,unit_cost,stock,reorder_level,created_at) VALUES (?,?,?,?,?,?,?)",
                    (sku, name, price, cost, stock, reorder_level, _now()),
                )
            except sqlite3.IntegrityError as exc:
                raise BusinessError("Cette référence existe déjà.") from exc
            product_id = int(cursor.lastrowid)
            if stock:
                self._movement(db, product_id, stock, "stock initial")
        return product_id

    def edit_product(self, product_id: int, *, name: str, price: int, cost: int, reorder_level: int, active: bool = True) -> None:
        name = _label(name, name="Le nom")
        price = _integer(price, minimum=1, name="Le prix de vente")
        cost = _integer(cost, minimum=0, name="Le prix d'achat")
        reorder_level = _integer(reorder_level, minimum=0, name="Le seuil d'alerte")
        with self._transaction() as db:
            cursor = db.execute(
                "UPDATE products SET name=?, unit_price=?, unit_cost=?, reorder_level=?, active=? WHERE id=?",
                (name, price, cost, reorder_level, int(active), product_id),
            )
            if not cursor.rowcount:
                raise BusinessError("Article introuvable.")

    @staticmethod
    def _movement(db: sqlite3.Connection, product_id: int, delta: int, reason: str, sale_id: int | None = None) -> None:
        if delta:
            db.execute("INSERT INTO stock_movements(product_id,delta,reason,sale_id,created_at) VALUES(?,?,?,?,?)", (product_id, delta, reason, sale_id, _now()))

    def adjust_stock(self, product_id: int, delta: int, reason: str) -> int:
        _integer(delta, minimum=-2_000_000_000, name="La quantité")
        if delta == 0:
            raise BusinessError("La variation de stock ne peut pas être nulle.")
        reason = _label(reason, name="Le motif", limit=100)
        with self._transaction() as db:
            row = db.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
            if row is None:
                raise BusinessError("Article introuvable.")
            remaining = int(row["stock"]) + delta
            if remaining < 0:
                raise BusinessError("Stock insuffisant pour ce mouvement.")
            db.execute("UPDATE products SET stock=? WHERE id=?", (remaining, product_id))
            self._movement(db, product_id, delta, reason)
        return remaining

    def sell(self, lines: Sequence[CartLine], *, discount: int = 0) -> SaleResult:
        if not lines:
            raise BusinessError("Le panier est vide.")
        discount = _integer(discount, minimum=0, name="La remise")
        quantities: Counter[int] = Counter()
        for line in lines:
            if type(line.product_id) is not int or line.product_id < 1:
                raise BusinessError("Identifiant d'article invalide.")
            _integer(line.quantity, minimum=1, name="La quantité")
            quantities[line.product_id] += line.quantity
        with self._transaction() as db:
            entries = []
            subtotal = 0
            margin = 0
            for product_id, quantity in quantities.items():
                row = db.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
                if row is None:
                    raise BusinessError(f"Article indisponible : {product_id}.")
                if int(row["stock"]) < quantity:
                    raise BusinessError(f"Stock insuffisant pour « {row['name']} » : {row['stock']} disponible(s).")
                line_total = int(row["unit_price"]) * quantity
                subtotal += line_total
                margin += (int(row["unit_price"]) - int(row["unit_cost"])) * quantity
                entries.append((row, quantity, line_total))
            if discount > subtotal:
                raise BusinessError("La remise ne peut pas dépasser le sous-total.")
            total = subtotal - discount
            margin -= discount
            cursor = db.execute(
                "INSERT INTO sales(created_at,subtotal,discount,total,estimated_margin) VALUES(?,?,?,?,?)",
                (_now(), subtotal, discount, total, margin),
            )
            sale_id = int(cursor.lastrowid)
            for row, quantity, line_total in entries:
                product_id = int(row["id"])
                updated = db.execute(
                    "UPDATE products SET stock=stock-? WHERE id=? AND stock>=?",
                    (quantity, product_id, quantity),
                )
                if updated.rowcount != 1:
                    raise BusinessError("Le stock a été modifié. Merci de réessayer.")
                db.execute(
                    "INSERT INTO sale_lines(sale_id,product_id,sku,product_name,quantity,unit_price,unit_cost,line_total) VALUES (?,?,?,?,?,?,?,?)",
                    (sale_id, product_id, row["sku"], row["name"], quantity, row["unit_price"], row["unit_cost"], line_total),
                )
                self._movement(db, product_id, -quantity, "vente", sale_id)
        return SaleResult(sale_id, subtotal, discount, total, margin)

    def cancel_sale(self, sale_id: int) -> None:
        with self._transaction() as db:
            row = db.execute("SELECT status FROM sales WHERE id=?", (sale_id,)).fetchone()
            if row is None:
                raise BusinessError("Vente introuvable.")
            if row["status"] != "valid":
                raise BusinessError("Cette vente a déjà été annulée.")
            for line in db.execute("SELECT product_id,quantity FROM sale_lines WHERE sale_id=?", (sale_id,)):
                db.execute("UPDATE products SET stock=stock+? WHERE id=?", (line["quantity"], line["product_id"]))
                self._movement(db, line["product_id"], line["quantity"], "annulation vente", sale_id)
            db.execute("UPDATE sales SET status='cancelled',cancelled_at=? WHERE id=?", (_now(), sale_id))

    def sales(self, *, limit: int = 200) -> list[sqlite3.Row]:
        _integer(limit, minimum=1, name="La limite")
        with self._connection() as db:
            return db.execute(
                "SELECT id,created_at,subtotal,discount,total,estimated_margin,status FROM sales ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def sale_detail(self, sale_id: int) -> tuple[sqlite3.Row, list[sqlite3.Row]]:
        with self._connection() as db:
            header = db.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
            lines = db.execute("SELECT * FROM sale_lines WHERE sale_id=? ORDER BY id", (sale_id,)).fetchall()
        if header is None:
            raise BusinessError("Vente introuvable.")
        return header, lines

    def movements(self, limit: int = 300) -> list[sqlite3.Row]:
        with self._connection() as db:
            return db.execute("SELECT m.id,m.created_at,p.sku,p.name,m.delta,m.reason,m.sale_id FROM stock_movements m JOIN products p ON p.id=m.product_id ORDER BY m.id DESC LIMIT ?", (limit,)).fetchall()

    def metrics(self, *, date_prefix: str | None = None) -> Metrics:
        where = "WHERE status='valid'"
        params: tuple[object, ...] = ()
        if date_prefix:
            where += " AND created_at LIKE ?"
            params = (date_prefix + "%",)
        with self._connection() as db:
            row = db.execute(f"SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS revenue, COALESCE(SUM(estimated_margin),0) AS margin FROM sales {where}", params).fetchone()
            count = db.execute(f"SELECT COALESCE(SUM(sl.quantity),0) FROM sale_lines sl JOIN sales s ON s.id=sl.sale_id {where}", params).fetchone()[0]
            low = db.execute("SELECT COUNT(*) FROM products WHERE active=1 AND stock<=reorder_level").fetchone()[0]
            return Metrics(int(row["n"]), int(row["revenue"]), int(row["margin"]), int(count), int(low))

    def top_products(self, limit: int = 5) -> list[sqlite3.Row]:
        with self._connection() as db:
            return db.execute("SELECT sl.sku,sl.product_name,SUM(sl.quantity) AS units,SUM(sl.line_total) AS revenue FROM sale_lines sl JOIN sales s ON sl.sale_id=s.id WHERE s.status='valid' GROUP BY sl.product_id ORDER BY units DESC, revenue DESC LIMIT ?", (limit,)).fetchall()

    def export_sales_csv(self, output: Path) -> int:
        rows = self.sales(limit=100000)
        with Path(output).open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["ID", "Date UTC", "Sous-total FCFA", "Remise FCFA", "Total FCFA", "Marge estimée FCFA", "Statut"])
            for row in rows:
                writer.writerow([_spreadsheet_safe(row[key]) for key in ("id", "created_at", "subtotal", "discount", "total", "estimated_margin", "status")])
        return len(rows)

    def backup(self, destination: Path) -> None:
        destination = Path(destination).expanduser().resolve()
        if destination == self.path:
            raise BusinessError("Le fichier de sauvegarde doit être différent de la base active.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as source, sqlite3.connect(destination) as target:
            source.backup(target)
