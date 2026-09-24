# GestCom KKB — snapshot de travail privé

Ce dépôt contient une interface de bureau Python/Tkinter pour un projet de gestion commerciale. Il est privé car il se rapporte à un travail réalisé pour une entreprise.

## Contenu vérifiable dans ce dépôt

- `main.py` crée la fenêtre principale et affiche un menu de vente, d'articles, de transactions et de statistiques.
- `src/images/` contient des ressources graphiques.
- Les boutons de ce snapshot ne sont pas reliés aux traitements métier ; aucune couche de persistance ou mesure de performance n'est présente dans cette version du dépôt.

## État et exécution

Il s'agit d'un snapshot d'interface, pas d'une distribution installable de l'application complète. Le lancement requiert Python, Tkinter et `ttkbootstrap`. Avant exécution sur une autre machine, remplacer le chemin absolu Windows de l'icône dans `main.py` par un chemin relatif valide.

```sh
python -m pip install ttkbootstrap
python main.py
```

La commande de lancement n'a pas été validée dans cet environnement. Les résultats métier ou chiffres cités ailleurs doivent être accompagnés de preuves distinctes, avec l'accord de l'entreprise.

## Documentation à ajouter

Décrire le périmètre de la version complète, le modèle de données, les flux de vente et de stock, les tests et une démonstration anonymisée autorisée. Ne pas ajouter de données client ou de secrets au dépôt.