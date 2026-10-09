"""Desktop interface (Tkinter + ttkbootstrap). No database logic in widgets."""
from __future__ import annotations

import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as ttk

from .database import BusinessError, Store
from .models import CartLine, Product


NAVIGATION = (
    ("dashboard", "◈  Tableau de bord"),
    ("products", "▦  Articles"),
    ("checkout", "◉  Nouvelle vente"),
    ("stock", "↕  Mouvements de stock"),
    ("sales", "≡  Historique des ventes"),
    ("statistics", "▥  Statistiques"),
    ("settings", "⚙  Configuration"),
)


def money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " FCFA"


class GestComApp:
    """UI orchestration: delegates all persistence and validation to Store."""

    def __init__(self, store: Store):
        self.store = store
        self.root = ttk.Window(themename="darkly")
        self.root.title("GestCom KKB | Gestion commerciale")
        self.root.geometry("1230x760")
        self.root.minsize(1000, 650)
        icon = Path(__file__).resolve().parents[1] / "src" / "images" / "logo_kkbgestcom (1).ico"
        if icon.is_file() and sys.platform.startswith("win"):
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

        self.active_page = "dashboard"
        self.cart: dict[int, int] = {}
        self.product_rows: dict[str, Product] = {}
        self.sale_rows: dict[str, int] = {}
        self._nav_buttons: dict[str, ttk.Button] = {}
        self._build_layout()
        self.navigate("dashboard")
        self._tick_clock()

    def _build_layout(self) -> None:
        self.sidebar = ttk.Frame(self.root, padding=16, bootstyle="secondary")
        self.sidebar.pack(side="left", fill="y")
        ttk.Label(self.sidebar, text="KKB", font=("Helvetica", 26, "bold"), bootstyle="inverse-secondary").pack(anchor="w")
        ttk.Label(self.sidebar, text="GESTCOM  •  V2", font=("Helvetica", 12, "bold"), bootstyle="inverse-secondary").pack(anchor="w", pady=(0, 26))
        for page, label in NAVIGATION:
            btn = ttk.Button(
                self.sidebar, text=label, width=26,
                command=lambda selected=page: self.navigate(selected), bootstyle="secondary-outline",
            )
            btn.pack(fill="x", pady=5, ipady=7)
            self._nav_buttons[page] = btn
        ttk.Label(
            self.sidebar, text="Stockage local SQLite\nDeveloped by Devmaes",
            justify="left", bootstyle="inverse-secondary",
        ).pack(side="bottom", anchor="w", pady=(20, 4))

        self.main = ttk.Frame(self.root, padding=(22, 17, 22, 16))
        self.main.pack(side="left", fill="both", expand=True)
        title_bar = ttk.Frame(self.main)
        title_bar.pack(fill="x", pady=(0, 12))
        self.page_title = ttk.Label(title_bar, text="", font=("Helvetica", 24, "bold"))
        self.page_title.pack(side="left")
        self.clock = ttk.Label(title_bar, text="", bootstyle="secondary")
        self.clock.pack(side="right")
        self.content = ttk.Frame(self.main)
        self.content.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Prêt")
        ttk.Label(self.main, textvariable=self.status, bootstyle="secondary").pack(anchor="w", pady=(12, 0))

    def _tick_clock(self) -> None:
        self.clock.configure(text=datetime.now().strftime("%d/%m/%Y · %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def _clear(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.product_rows.clear()
        self.sale_rows.clear()

    def navigate(self, name: str) -> None:
        self.active_page = name
        self._clear()
        label = dict(NAVIGATION)[name].split("  ", 1)[-1]
        self.page_title.configure(text=label)
        for key, button in self._nav_buttons.items():
            button.configure(bootstyle="warning" if key == name else "secondary-outline")
        try:
            getattr(self, "_page_" + name)()
        except (BusinessError, ValueError, OSError) as exc:
            self._error(exc)

    def _notify(self, message: str) -> None:
        self.status.set(message)

    def _error(self, exc: Exception) -> None:
        messagebox.showerror("GestCom KKB — Erreur", str(exc), parent=self.root)
        self._notify("Erreur : " + str(exc))

    def _run_action(self, callback, *, page: str | None = None) -> None:
        try:
            callback()
            if page is not None:
                self.navigate(page)
        except (BusinessError, ValueError, OSError) as exc:
            self._error(exc)

    @staticmethod
    def _table(parent, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True, pady=10)
        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=12, selectmode="browse", bootstyle="info")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=70, anchor="w" if col in ("Nom", "Référence", "Date", "Motif", "Statut") else "e")
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        return tree

    def _panel(self, parent, label: str) -> ttk.Labelframe:
        panel = ttk.Labelframe(parent, text=label, padding=14, bootstyle="primary")
        panel.pack(fill="x", pady=10)
        return panel

    def _metric(self, parent, title: str, value: str, color: str = "info") -> None:
        card = ttk.Frame(parent, padding=16, bootstyle=color)
        card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(card, text=title, font=("Helvetica", 11, "bold"), bootstyle=f"inverse-{color}").pack(anchor="w")
        ttk.Label(card, text=value, font=("Helvetica", 19, "bold"), bootstyle=f"inverse-{color}").pack(anchor="w", pady=(8, 2))

    def _page_dashboard(self) -> None:
        metrics = self.store.metrics()
        row = ttk.Frame(self.content)
        row.pack(fill="x", pady=(10, 24))
        self._metric(row, "Ventes valides", str(metrics.sales_count), "primary")
        self._metric(row, "Chiffre d'affaires", money(metrics.revenue), "success")
        self._metric(row, "Marge estimée", money(metrics.estimated_margin), "info")
        self._metric(row, "Alertes stock", str(metrics.low_stock_count), "warning")
        low = [p for p in self.store.products() if p.stock <= p.reorder_level]
        panel = self._panel(self.content, "Articles sous le seuil d'alerte")
        if not low:
            ttk.Label(panel, text="Aucune alerte. Les stocks sont au-dessus des seuils définis.").pack(anchor="w")
        else:
            for product in low[:12]:
                ttk.Label(panel, text=f"⚠  {product.sku} — {product.name} : {product.stock} restant(s), seuil {product.reorder_level}", bootstyle="warning").pack(anchor="w", pady=2)
        buttons = ttk.Frame(self.content)
        buttons.pack(anchor="w", pady=20)
        ttk.Button(buttons, text="+ Enregistrer une vente", bootstyle="success", command=lambda: self.navigate("checkout")).pack(side="left", padx=(0, 12))
        ttk.Button(buttons, text="Voir les articles", bootstyle="outline-info", command=lambda: self.navigate("products")).pack(side="left")

    def _page_products(self) -> None:
        tools = ttk.Frame(self.content)
        tools.pack(fill="x")
        q = tk.StringVar()
        ttk.Entry(tools, textvariable=q, width=32).pack(side="left", padx=(0, 8))
        ttk.Button(tools, text="Rechercher", command=lambda: self._fill_products(table, q.get())).pack(side="left", padx=(0, 8))
        ttk.Button(tools, text="Ajouter un article", bootstyle="success", command=self._add_product_dialog).pack(side="right")
        table = self._table(self.content,
            ("Référence", "Nom", "Vente", "Achat", "Stock", "Seuil", "Statut"),
            (130, 230, 110, 110, 80, 75, 85))
        self._fill_products(table)
        actions = ttk.Frame(self.content)
        actions.pack(fill="x", pady=6)
        ttk.Button(actions, text="Modifier", command=lambda: self._select_product(table, self._edit_product_dialog)).pack(side="left", padx=4)
        ttk.Button(actions, text="Entrée / sortie de stock", bootstyle="warning", command=lambda: self._select_product(table, self._adjust_dialog)).pack(side="left", padx=4)
        ttk.Button(actions, text="Désactiver / Réactiver", bootstyle="secondary-outline", command=lambda: self._select_product(table, self._toggle_product)).pack(side="left", padx=4)

    def _fill_products(self, tree, query: str = "") -> None:
        tree.delete(*tree.get_children())
        self.product_rows.clear()
        for p in self.store.products(include_inactive=True, query=query):
            key = str(p.id)
            self.product_rows[key] = p
            tree.insert("", "end", iid=key, values=(p.sku, p.name, money(p.unit_price), money(p.unit_cost), p.stock, p.reorder_level, "Actif" if p.active else "Inactif"))

    def _select_product(self, tree, action) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Sélection", "Sélectionnez un article dans le tableau.", parent=self.root)
            return
        action(self.store.get_product(int(selected[0])))

    def _product_form(self, product: Product | None) -> dict[str, object] | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Nouvel article" if product is None else "Modifier l'article")
        dialog.geometry("430x420")
        dialog.transient(self.root)
        dialog.grab_set()
        values = {
            "sku": product.sku if product else "", "name": product.name if product else "",
            "price": str(product.unit_price) if product else "", "cost": str(product.unit_cost) if product else "0",
            "stock": str(product.stock) if product else "0", "level": str(product.reorder_level) if product else "5",
        }
        entries: dict[str, ttk.Entry] = {}
        labels = (("sku", "Référence / SKU"), ("name", "Désignation"), ("price", "Prix de vente (FCFA)"), ("cost", "Prix d'achat (FCFA)"), ("stock", "Stock initial" if not product else "Stock (voir mouvements)"), ("level", "Seuil d'alerte"))
        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)
        for row, (field, title) in enumerate(labels):
            ttk.Label(form, text=title).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=10)
            entry = ttk.Entry(form, width=24)
            entry.insert(0, values[field])
            entry.grid(row=row, column=1, sticky="ew", pady=10)
            if product is not None and field in {"sku", "stock"}:
                entry.configure(state="disabled")
            entries[field] = entry
        result: dict[str, object] = {}

        def submit():
            try:
                result.update({
                    "sku": values["sku"] if product else entries["sku"].get(),
                    "name": entries["name"].get(),
                    "price": int(entries["price"].get()), "cost": int(entries["cost"].get()),
                    "stock": product.stock if product else int(entries["stock"].get()),
                    "level": int(entries["level"].get()),
                })
            except ValueError:
                messagebox.showerror("Valeurs invalides", "Les prix et les quantités doivent être des entiers.", parent=dialog)
                return
            dialog.destroy()

        ttk.Button(form, text="Enregistrer", bootstyle="success", command=submit).grid(row=7, column=0, columnspan=2, pady=15)
        dialog.wait_window()
        return result or None

    def _add_product_dialog(self) -> None:
        values = self._product_form(None)
        if values is None:
            return
        def execute():
            self.store.add_product(values["sku"], values["name"], values["price"], values["cost"], values["stock"], values["level"])
            self._notify("Article créé avec succès.")
        self._run_action(execute, page="products")

    def _edit_product_dialog(self, product: Product) -> None:
        values = self._product_form(product)
        if values is None:
            return
        self._run_action(lambda: self.store.edit_product(product.id, name=values["name"], price=values["price"], cost=values["cost"], reorder_level=values["level"], active=product.active), page="products")

    def _adjust_dialog(self, product: Product) -> None:
        amount = simpledialog.askinteger("Mouvement de stock", f"{product.name}\nVariation : + pour entrée, - pour sortie :", parent=self.root)
        if amount is None:
            return
        reason = simpledialog.askstring("Justification", "Motif du mouvement (obligatoire) :", parent=self.root)
        if reason is None:
            return
        self._run_action(lambda: self.store.adjust_stock(product.id, amount, reason), page="products")

    def _toggle_product(self, product: Product) -> None:
        action = "désactiver" if product.active else "réactiver"
        if messagebox.askyesno("Confirmation", f"Voulez-vous {action} « {product.name} » ?", parent=self.root):
            self._run_action(lambda: self.store.edit_product(product.id, name=product.name, price=product.unit_price, cost=product.unit_cost, reorder_level=product.reorder_level, active=not product.active), page="products")

    def _page_checkout(self) -> None:
        parts = ttk.Frame(self.content)
        parts.pack(fill="both", expand=True)
        left = ttk.Labelframe(parts, text="Catalogue", padding=10, bootstyle="primary")
        right = ttk.Labelframe(parts, text="Panier", padding=10, bootstyle="success")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right.pack(side="left", fill="both", expand=True)
        self.available = self.store.products()
        catalog = self._table(left, ("ID", "Article", "Prix", "Stock"), (50, 205, 120, 70))
        for product in self.available:
            catalog.insert("", "end", iid=str(product.id), values=(product.id, product.name, money(product.unit_price), product.stock))
        qty_frame = ttk.Frame(left)
        qty_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(qty_frame, text="Quantité :").pack(side="left")
        quantity = tk.StringVar(value="1")
        ttk.Entry(qty_frame, textvariable=quantity, width=7).pack(side="left", padx=8)

        def add():
            selected = catalog.selection()
            if not selected:
                raise BusinessError("Sélectionnez d'abord un article.")
            n = int(quantity.get())
            if n <= 0:
                raise BusinessError("La quantité doit être positive.")
            product_id = int(selected[0])
            product = self.store.get_product(product_id)
            if self.cart.get(product_id, 0) + n > product.stock:
                raise BusinessError("La quantité choisie dépasse le stock disponible.")
            self.cart[product_id] = self.cart.get(product_id, 0) + n
            self._render_cart()

        ttk.Button(qty_frame, text="+ Ajouter", bootstyle="success", command=lambda: self._run_action(add)).pack(side="left")
        self.cart_tree = self._table(right, ("Article", "Qté", "Sous-total"), (205, 55, 120))
        ttk.Button(right, text="Retirer l'article sélectionné", bootstyle="danger-outline", command=self._remove_cart).pack(anchor="w", pady=5)
        price_row = ttk.Frame(right)
        price_row.pack(fill="x", pady=12)
        ttk.Label(price_row, text="Remise (FCFA) :").pack(side="left")
        self.discount = tk.StringVar(value="0")
        ttk.Entry(price_row, textvariable=self.discount, width=12).pack(side="left", padx=10)
        self.cart_total = ttk.Label(right, text="Total : 0 FCFA", font=("Helvetica", 20, "bold"), bootstyle="success")
        self.cart_total.pack(anchor="w", pady=6)
        ttk.Button(right, text="✓ Valider et enregistrer la vente", bootstyle="success", command=self._checkout).pack(fill="x", pady=10, ipady=9)
        self._render_cart()

    def _render_cart(self) -> None:
        self.cart_tree.delete(*self.cart_tree.get_children())
        subtotal = 0
        for product_id, quantity in list(self.cart.items()):
            product = self.store.get_product(product_id)
            amount = product.unit_price * quantity
            subtotal += amount
            self.cart_tree.insert("", "end", iid=str(product_id), values=(product.name, quantity, money(amount)))
        self.cart_total.configure(text="Sous-total : " + money(subtotal))

    def _remove_cart(self) -> None:
        selected = self.cart_tree.selection()
        if selected:
            self.cart.pop(int(selected[0]), None)
            self._render_cart()

    def _checkout(self) -> None:
        def execute():
            try:
                discount = int(self.discount.get())
            except ValueError as exc:
                raise BusinessError("La remise doit être un entier en FCFA.") from exc
            if not self.cart:
                raise BusinessError("Le panier est vide.")
            if not messagebox.askyesno("Valider la vente", "Confirmer et débiter le stock ?", parent=self.root):
                return
            sale = self.store.sell([CartLine(pid, qty) for pid, qty in self.cart.items()], discount=discount)
            self.cart.clear()
            self._notify(f"Vente #{sale.id} enregistrée — {money(sale.total)}")
            self.navigate("checkout")
            self._receipt_dialog(sale.id)
        self._run_action(execute)

    def _receipt_dialog(self, sale_id: int) -> None:
        header, lines = self.store.sale_detail(sale_id)
        receipt = ["KKB GESTCOM — REÇU DE VENTE", f"Vente #{sale_id} | {header['created_at']} (UTC)", "-" * 45]
        for line in lines:
            receipt.append(f"{line['product_name']} x{line['quantity']}  {money(line['line_total'])}")
        receipt.extend(["-" * 45, f"Sous-total : {money(header['subtotal'])}", f"Remise : {money(header['discount'])}", f"TOTAL : {money(header['total'])}", "", "Document interne — non fiscal"])
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Reçu #{sale_id}")
        dialog.geometry("560x460")
        dialog.transient(self.root)
        text = tk.Text(dialog, wrap="word", font=("Courier New", 11), padx=20, pady=20)
        text.insert("1.0", "\n".join(receipt))
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)
        def save():
            path = filedialog.asksaveasfilename(parent=dialog, title="Exporter le reçu", defaultextension=".txt", filetypes=[("Fichier texte", "*.txt")], initialfile=f"recu_kkb_{sale_id}.txt")
            if path:
                Path(path).write_text("\n".join(receipt) + "\n", encoding="utf-8")
                self._notify("Reçu exporté.")
        ttk.Button(dialog, text="Enregistrer le reçu (.txt)", command=lambda: self._run_action(save)).pack(pady=10)

    def _page_stock(self) -> None:
        ttk.Label(self.content, text="Journal de toutes les entrées, sorties, ventes et annulations.", bootstyle="secondary").pack(anchor="w")
        tree = self._table(self.content, ("ID", "Date", "Référence", "Nom", "Variation", "Motif", "Vente"), (60, 200, 110, 195, 95, 160, 70))
        for row in self.store.movements():
            tree.insert("", "end", values=(row["id"], row["created_at"], row["sku"], row["name"], row["delta"], row["reason"], row["sale_id"] or "—"))
        ttk.Button(self.content, text="Modifier un stock via Articles", command=lambda: self.navigate("products")).pack(anchor="w", pady=8)

    def _page_sales(self) -> None:
        tree = self._table(self.content, ("ID", "Date", "Sous-total", "Remise", "Total", "Marge estimée", "Statut"), (65, 190, 115, 95, 115, 140, 100))
        for row in self.store.sales():
            tree.insert("", "end", iid=str(row["id"]), values=(row["id"], row["created_at"], money(row["subtotal"]), money(row["discount"]), money(row["total"]), money(row["estimated_margin"]), "Validée" if row["status"] == "valid" else "Annulée"))
        actions = ttk.Frame(self.content)
        actions.pack(fill="x", pady=10)
        def selected_id() -> int:
            selected = tree.selection()
            if not selected:
                raise BusinessError("Sélectionnez une vente.")
            return int(selected[0])
        ttk.Button(actions, text="Voir le reçu", command=lambda: self._run_action(lambda: self._receipt_dialog(selected_id()))).pack(side="left", padx=(0, 10))
        def cancel():
            sale_id = selected_id()
            if messagebox.askyesno("Annulation", f"Annuler la vente #{sale_id} et restituer les stocks ?", parent=self.root):
                self.store.cancel_sale(sale_id)
                self._notify(f"Vente #{sale_id} annulée ; stocks restitués.")
                self.navigate("sales")
        ttk.Button(actions, text="Annuler une vente (avec traçabilité)", bootstyle="danger-outline", command=lambda: self._run_action(cancel)).pack(side="left")

    def _page_statistics(self) -> None:
        total = self.store.metrics()
        today = self.store.metrics(date_prefix=datetime.utcnow().strftime("%Y-%m-%d"))
        ttk.Label(self.content, text="Indicateurs globaux (ventes non annulées)", font=("Helvetica", 15, "bold")).pack(anchor="w", pady=8)
        general = ttk.Frame(self.content)
        general.pack(fill="x", pady=(0, 22))
        self._metric(general, "Ventes", str(total.sales_count), "primary")
        self._metric(general, "Chiffre d'affaires", money(total.revenue), "success")
        self._metric(general, "Articles vendus", str(total.items_sold), "info")
        self._metric(general, "Marge estimée", money(total.estimated_margin), "warning")
        ttk.Label(self.content, text=f"Aujourd'hui (date UTC) : {today.sales_count} ventes · {money(today.revenue)}", bootstyle="secondary").pack(anchor="w", pady=12)
        ttk.Label(self.content, text="Top 5 des articles les plus vendus", font=("Helvetica", 15, "bold")).pack(anchor="w", pady=8)
        tree = self._table(self.content, ("Référence", "Nom", "Unités", "Chiffre d'affaires"), (145, 310, 115, 170))
        for row in self.store.top_products():
            tree.insert("", "end", values=(row["sku"], row["product_name"], row["units"], money(row["revenue"])))

    def _page_settings(self) -> None:
        ttk.Label(self.content, text="Données locales", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(8, 12))
        ttk.Label(self.content, text=f"Base SQLite : {self.store.path}", wraplength=700).pack(anchor="w", pady=(0, 18))
        def backup():
            dest = filedialog.asksaveasfilename(parent=self.root, title="Sauvegarder la base SQLite", defaultextension=".sqlite3", filetypes=[("SQLite", "*.sqlite3")], initialfile="gestcom_sauvegarde.sqlite3")
            if dest:
                self.store.backup(Path(dest))
                self._notify("Sauvegarde SQLite effectuée.")
                messagebox.showinfo("Sauvegarde", "La sauvegarde est terminée.", parent=self.root)
        def export():
            dest = filedialog.asksaveasfilename(parent=self.root, title="Export CSV des ventes", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="gestcom_ventes.csv")
            if dest:
                count = self.store.export_sales_csv(Path(dest))
                self._notify(f"{count} ventes exportées.")
        ttk.Button(self.content, text="Sauvegarder la base de données", bootstyle="success", command=lambda: self._run_action(backup)).pack(anchor="w", fill="x", pady=8, ipady=7)
        ttk.Button(self.content, text="Exporter les ventes (CSV)", bootstyle="info-outline", command=lambda: self._run_action(export)).pack(anchor="w", fill="x", pady=8, ipady=7)
        ttk.Label(self.content, text="Les reçus produits sont des justificatifs internes et non des factures fiscales certifiées.", bootstyle="warning", wraplength=700).pack(anchor="w", pady=20)

    def run(self) -> None:
        self.root.mainloop()


def launch() -> None:
    GestComApp(Store()).run()
