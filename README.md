# GestCom KKB — gestion commerciale locale

**Application de bureau Python pour les ventes, les articles, les stocks et les statistiques d'une petite entreprise.**

> **Developed by Devmaes** · Modernisation du prototype avec assistance IA.

![Version](https://img.shields.io/badge/version-2.0.0-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-yellow) ![Stockage](https://img.shields.io/badge/SQLite-local-success) ![Statut](https://img.shields.io/badge/statut-MVP%20fonctionnel-orange)

## Contexte

Le dépôt d'origine contenait une interface de navigation basée sur `ttkbootstrap` et `Tkinter`, avec plusieurs boutons non reliés à la gestion commerciale. Cette évolution conserve **Python et ttkbootstrap** et ajoute un véritable moteur transactionnel **SQLite**, des écrans opérationnels et des tests automatisés. Elle ne prétend pas reconstituer une version métier complète absente du dépôt initial.

## Fonctionnalités

- Tableau de bord : nombre de ventes, chiffre d'affaires, marge **estimée**, alertes de stock.
- Catalogue : création d'article avec référence unique, modification des prix, seuil d'alerte, activation/désactivation.
- Stock : mouvements justifiés d'entrée/sortie, historique audit des mouvements.
- Vente : panier, quantités, remise en FCFA, vérification atomique des stocks, reçu interne exportable.
- Transactions : liste des ventes, consultation des reçus, annulation unique qui restitue les stocks.
- Statistiques : unités vendues, ventes valides, top cinq des articles, total et indicateurs du jour **en UTC**.
- Données locales : base SQLite dans le dossier de données de l'utilisateur, sauvegarde cohérente et export CSV.
- Sécurité métier : champs vérifiés, transactions atomiques, historique conservé et aucune donnée client obligatoire.

## Aperçu de l'application

Le projet comprend une interface Tkinter/ttkbootstrap en thème sombre. Captures réelles après exécution locale :

- `docs/screenshots/tableau-de-bord.png` *(à ajouter après essai sur ordinateur)*
- `docs/screenshots/articles.png` *(à ajouter après essai sur ordinateur)*
- `docs/screenshots/vente.png` *(à ajouter après essai sur ordinateur)*

Aucune capture non vérifiée n'est présentée comme un écran réel.

## Architecture

```text
main.py                 # Point d'entrée bureau
gestcom/
  database.py           # Accès SQLite, transactions et règles métier
  models.py             # Modèles typés
  ui.py                 # Interface desktop, événements et formulaires
  __main__.py           # python -m gestcom
tests/test_store.py      # Tests unitaires du moteur, sans interface graphique
docs/                  # Règles, architecture, limitations
.github/workflows/      # Validation automatique
```

## Installation

Python **3.10+** avec Tkinter est requis. Sous Linux, installer `python3-tk` via le gestionnaire de paquets de la distribution si nécessaire.

```bash
git clone https://github.com/Devmaes/GestCom-KKB.git
cd GestCom-KKB
python -m venv .venv
# Windows PowerShell : .venv\Scripts\Activate.ps1
# Linux / macOS : source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Sous Windows, tu peux aussi démarrer via `python -m gestcom`.

### Tester la logique métier sans GUI

```bash
python -m unittest discover -s tests -v
python -m compileall -q gestcom main.py tests
```

## Emplacement de la base SQLite

- Windows : `%LOCALAPPDATA%/gestcom-kkb/gestcom.sqlite3`
- Linux : `$XDG_DATA_HOME/gestcom-kkb/gestcom.sqlite3` (par défaut `~/.local/share/`)
- macOS : `~/.local/share/gestcom-kkb/gestcom.sqlite3`
- Personnalisation : variable d'environnement `GESTCOM_DB_PATH`.

Les données et sauvegardes ne doivent **pas** être versionnées sur GitHub.

## Ce que cette version ne fait pas

Il s'agit d'un **MVP local mono-poste**, pas d'un ERP certifié. Pas d'authentification multiutilisateur, d'intégration fiscale, de paiement électronique, de comptabilité complète, d'imprimante fiscale ni de synchronisation cloud. Les reçus sont des **justificatifs internes non fiscaux**. La marge calculée correspond à prix de vente moins coût d'achat moins remise ; elle n'inclut ni taxes, ni salaires, ni charges indirectes.

Avant toute utilisation réelle : valider les contraintes métiers avec l'entreprise, prévoir les sauvegardes quotidiennes, tester la restauration, vérifier l'interface sur les postes de travail et prévoir les obligations fiscales applicables.

## Documentation

- [Règles métier](docs/REGLES_METIER.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Guide de recette](docs/RECETTE.md)
- [Évolutions proposées](docs/ROADMAP.md)

**Developed by Devmaes**
