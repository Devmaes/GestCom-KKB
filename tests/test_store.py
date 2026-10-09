"""Business-focused regression tests; GUI and external services not required."""
from __future__ import annotations

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from gestcom.database import BusinessError, Store, _spreadsheet_safe
from gestcom.models import CartLine


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "data.sqlite3")
        self.apple = self.store.add_product("ABC-01", "Article A", 2500, 1400, 10, 3)
        self.banana = self.store.add_product("XYZ-02", "Article B", 1500, 1000, 5, 2)

    def test_creates_products_and_starts_stock_movements(self):
        self.assertEqual(len(self.store.products()), 2)
        self.assertEqual(self.store.get_product(self.apple).stock, 10)
        self.assertEqual(len(self.store.movements()), 2)

    def test_rejects_duplicate_sku_case_insensitively(self):
        with self.assertRaises(BusinessError):
            self.store.add_product("abc-01", "Double", 500, 200)

    def test_rejects_negative_or_zero_values(self):
        for price, cost, qty in ((0, 0, 1), (100, -1, 1), (100, 10, -1)):
            with self.subTest(price=price, cost=cost, qty=qty):
                with self.assertRaises(BusinessError):
                    self.store.add_product("NEW", "Produit", price, cost, qty)

    def test_atomic_sale_reduces_stock_and_calculates_margin(self):
        result = self.store.sell([CartLine(self.apple, 2), CartLine(self.banana, 1)], discount=500)
        self.assertEqual(result.subtotal, 6500)
        self.assertEqual(result.total, 6000)
        self.assertEqual(result.estimated_margin, 2200)
        self.assertEqual(self.store.get_product(self.apple).stock, 8)
        self.assertEqual(self.store.get_product(self.banana).stock, 4)
        self.assertEqual(self.store.metrics().revenue, 6000)
        self.assertEqual(self.store.metrics().items_sold, 3)
        h, lines = self.store.sale_detail(result.id)
        self.assertEqual(len(lines), 2)
        self.assertEqual(h['status'], 'valid')

    def test_duplicate_cart_lines_aggregate_without_overselling(self):
        result = self.store.sell([CartLine(self.apple, 1), CartLine(self.apple, 2)])
        self.assertEqual(result.total, 7500)
        self.assertEqual(self.store.get_product(self.apple).stock, 7)
        self.assertEqual(len(self.store.sale_detail(result.id)[1]), 1)

    def test_insufficient_stock_rolls_back_everything(self):
        before = len(self.store.movements())
        with self.assertRaisesRegex(BusinessError, 'Stock insuffisant'):
            self.store.sell([CartLine(self.apple, 1), CartLine(self.banana, 100)])
        self.assertEqual(self.store.get_product(self.apple).stock, 10)
        self.assertEqual(self.store.get_product(self.banana).stock, 5)
        self.assertEqual(self.store.metrics().sales_count, 0)
        self.assertEqual(len(self.store.movements()), before)

    def test_discount_may_not_exceed_subtotal(self):
        with self.assertRaises(BusinessError):
            self.store.sell([CartLine(self.apple, 1)], discount=2501)
        self.assertEqual(self.store.get_product(self.apple).stock, 10)

    def test_cancellation_restores_stock_once_and_audit(self):
        sale = self.store.sell([CartLine(self.apple, 2)])
        self.store.cancel_sale(sale.id)
        self.assertEqual(self.store.get_product(self.apple).stock, 10)
        self.assertEqual(self.store.metrics().revenue, 0)
        self.assertEqual(self.store.metrics().items_sold, 0)
        self.assertEqual(self.store.sale_detail(sale.id)[0]['status'], 'cancelled')
        with self.assertRaisesRegex(BusinessError, 'déjà été annulée'):
            self.store.cancel_sale(sale.id)
        self.assertEqual(self.store.get_product(self.apple).stock, 10)

    def test_stock_moves_validation_and_count(self):
        self.assertEqual(self.store.adjust_stock(self.banana, -3, 'casse'), 2)
        self.assertEqual(self.store.metrics().low_stock_count, 1)
        with self.assertRaises(BusinessError):
            self.store.adjust_stock(self.banana, -3, 'trop')
        with self.assertRaises(BusinessError):
            self.store.adjust_stock(self.banana, 1, '')
        self.assertEqual(self.store.adjust_stock(self.banana, 5, 'réapprovisionnement'), 7)

    def test_sales_preserve_snapshotted_prices(self):
        sale = self.store.sell([CartLine(self.apple, 1)])
        self.store.edit_product(self.apple, name='Article modifié', price=4000, cost=2000, reorder_level=2)
        _, lines = self.store.sale_detail(sale.id)
        self.assertEqual(lines[0]['product_name'], 'Article A')
        self.assertEqual(lines[0]['unit_price'], 2500)

    def test_inactive_products_cannot_be_sold(self):
        product = self.store.get_product(self.apple)
        self.store.edit_product(product.id, name=product.name, price=product.unit_price, cost=product.unit_cost, reorder_level=3, active=False)
        self.assertEqual(len(self.store.products()), 1)
        with self.assertRaises(BusinessError):
            self.store.sell([CartLine(self.apple, 1)])

    def test_backup_is_consistent_and_restorable(self):
        sale = self.store.sell([CartLine(self.banana, 2)])
        backup = Path(self.tmp.name) / 'backup.sqlite3'
        self.store.backup(backup)
        clone = Store(backup)
        self.assertEqual(clone.metrics().revenue, sale.total)
        self.assertEqual(clone.get_product(self.banana).stock, 3)
        with self.assertRaises(BusinessError):
            self.store.backup(self.store.path)

    def test_csv_export_has_header_and_valid_sales(self):
        sale = self.store.sell([CartLine(self.apple, 1)])
        path = Path(self.tmp.name) / 'sales.csv'
        self.assertEqual(self.store.export_sales_csv(path), 1)
        with path.open(encoding='utf-8-sig', newline='') as file:
            rows = list(csv.reader(file, delimiter=';'))
        self.assertEqual(rows[1][0], str(sale.id))
        self.assertEqual(rows[1][4], str(sale.total))
        self.assertEqual(_spreadsheet_safe('=HYPERLINK("bad")'), "'=HYPERLINK(\"bad\")")

    def test_sqlite_integrity(self):
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main()
