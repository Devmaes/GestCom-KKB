# Règles métier — GestCom KKB

1. Référence produit obligatoire, unique (insensible à la casse) ; nom non vide.
2. Les montants sont des entiers en FCFA. Prix de vente > 0 ; coût d'achat >= 0.
3. Stock et seuil d'alerte sont des entiers positifs ou nuls ; un stock ne devient jamais négatif.
4. Tout mouvement de stock manuel doit avoir un motif. Les créations avec stock initial, ventes et annulations produisent des écritures d'audit.
5. Le panier regroupe automatiquement les lignes multiples d'un même article avant la vente.
6. La remise est un montant global entre 0 et le sous-total.
7. À la validation, la transaction enregistre vente + lignes + stock + journal de mouvements de manière atomique ; si un article est indisponible, **aucune modification** n'est enregistrée.
8. Les prix, coûts et libellés des lignes de vente sont figés au moment de la vente (les modifications ultérieures du catalogue n'affectent pas l'historique).
9. Une vente peut être annulée une seule fois : l'annulation restitue les quantités et laisse sa trace dans l'historique. Les ventes annulées sont exclues des statistiques.
10. Alerte de stock si un article actif a `stock <= seuil`.
11. Chiffre d'affaires = somme des totaux des ventes valides ; marge estimée = somme (prix de vente - coût d'achat) * quantité - remise.
12. Pas de collecte de coordonnées client, ni de données bancaires. Le système n'émet pas de factures fiscales certifiées.
13. Horodatage interne stocké en UTC (ISO-8601) ; les indicateurs « aujourd'hui » utilisent la date UTC.
