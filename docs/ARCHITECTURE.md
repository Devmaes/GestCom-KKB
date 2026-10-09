# Architecture de la version 2

Architecture légère de bureau en **3 couches** :

- **Présentation** — `gestcom/ui.py` : widgets ttkbootstrap/Tkinter, formulaires et actions utilisateur, sans requêtes SQL.
- **Métier / persistance** — `gestcom/database.py` : validation, transactions SQLite, CRUD articles, stock, ventes, annulations, rapports, sauvegardes.
- **Modèles** — `gestcom/models.py` : `Product`, `CartLine`, `SaleResult`, `Metrics` en dataclasses immuables.

## Choix techniques

SQLite fonctionne sans serveur, adapté à un seul poste. `BEGIN IMMEDIATE` sérialise les écritures concurrentes, les contraintes SQL interdisent les stocks et coûts négatifs, et `PRAGMA foreign_keys=ON` évite les lignes orphelines.

Les annulations marquent une vente `cancelled` sans supprimer les lignes. Le journal de mouvements conserve la justification des modifications de quantité.

Les opérations de sauvegarde utilisent l'API SQLite `backup()` plutôt qu'une copie brute d'un fichier susceptible d'être ouvert en mode WAL.

## Points à reprendre pour un déploiement multi-poste

Utiliser une véritable API et une base serveur, ajouter authentification et permissions, journaliser l'identité de l'opérateur, prévoir des migrations versionnées, un système de sauvegardes automatisées chiffrées et une conformité fiscale adaptée à la juridiction.
