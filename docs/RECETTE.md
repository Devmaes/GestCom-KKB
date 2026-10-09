# Plan de recette fonctionnelle (sur ordinateur)

Ce plan doit être exécuté sur Windows/Linux/macOS avec affichage et Tkinter installés. Les tests automatiques ne valident pas l'apparence graphique.

1. Démarrer sans fichier SQLite : le tableau de bord s'ouvre sans erreur et les indicateurs affichent zéro.
2. Créer un article `TEST01` avec prix 2 500, coût 1 400, stock 10 et seuil 3. Vérifier sa présence dans **Articles**.
3. Créer un article avec la même référence en minuscules : afficher un message d'erreur sans dupliquer.
4. Effectuer une vente de 2 unités, remise 500 : le total doit être 4 500 FCFA, stock résiduel 8.
5. Vérifier l'historique, le reçu et les statistiques. La marge estimée de cette vente doit être 1 700 FCFA.
6. Tenter de vendre 9 unités alors que 8 restent : la transaction doit échouer sans altérer ni le stock ni l'historique.
7. Annuler la vente puis vérifier le retour du stock à 10 et la disparition de la vente du CA.
8. Vérifier qu'une deuxième annulation de la même vente est refusée.
9. Sortir 8 unités avec motif `inventaire` : stock 2 et alerte affichée au tableau de bord.
10. Exporter un CSV, effectuer une sauvegarde SQLite, vérifier son ouverture et les données depuis un autre dossier.
11. Vérifier que la fermeture puis le redémarrage conservent les données.

**Précaution :** réaliser ce protocole avec `GESTCOM_DB_PATH` pointant vers un fichier de test. Ne jamais le lancer dans la base d'une entreprise en production.
