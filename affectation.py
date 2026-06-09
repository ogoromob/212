"""
Module Affectation - Affectation des salles et génération du planning final
Partie 3 du cahier des charges
"""
import csv
import os
from collections import defaultdict

class GenerateurPlanning:
    """Gère l'affectation des salles et la génération du planning final"""
    
    def __init__(self, graphe, salles, solveur):
        self.graphe = graphe
        self.salles = salles
        self.solveur = solveur
        self.planning = {}  # creneau -> {salle: code_ue}
        self.affectations = {}  # code_ue -> {'creneau': int, 'salle': str}
    
    def affecter_salles(self, equilibrer=True):
        """
        Algorithme First Fit Decreasing pour l'affectation des salles:
        1. Trier les salles par capacité décroissante
        2. Pour chaque créneau, trier les UEs par effectif décroissant
        3. Affecter chaque UE à la première salle disponible qui convient
        """
        # Trier les salles par capacité décroissante
        salles_triees = sorted(self.salles, key=lambda s: -s.capacite)
        
        # Grouper les UEs par créneau
        creneaux_ues = defaultdict(list)
        for code, couleur in self.solveur.couleurs.items():
            creneaux_ues[couleur].append(code)
        
        # Pour chaque créneau
        for creneau, codes_ue in sorted(creneaux_ues.items()):
            # Trier les UEs par effectif décroissant (priorité aux grands effectifs)
            codes_ue.sort(key=lambda c: -self.graphe.sommets[c].nb_inscrits)
            
            # Salles disponibles pour ce créneau
            salles_disponibles = list(salles_triees)
            self.planning[creneau] = {}
            
            for code in codes_ue:
                ue = self.graphe.sommets[code]
                salle_attribuee = None
                
                # Chercher la première salle qui convient
                for salle in salles_disponibles:
                    # Vérifier la capacité
                    if salle.capacite < ue.nb_inscrits:
                        continue
                    
                    # Vérifier le type de salle (labo)
                    if ue.besoin_labo and not salle.est_labo:
                        continue
                    
                    # Salle trouvée
                    salle_attribuee = salle
                    break
                
                if salle_attribuee:
                    self.planning[creneau][salle_attribuee.nom] = code
                    self.affectations[code] = {
                        'creneau': creneau,
                        'salle': salle_attribuee.nom
                    }
                    salles_disponibles.remove(salle_attribuee)
                else:
                    # Aucune salle disponible - marquer comme non affecté
                    self.affectations[code] = {
                        'creneau': creneau,
                        'salle': 'NON_AFFECTE'
                    }
        
        return self.planning
    
    def verifier_contraintes(self):
        """
        Vérifie automatiquement le respect de toutes les contraintes
        Retourne un rapport d'audit détaillé
        """
        rapport = {
            'contraintes_respectees': True,
            'erreurs': [],
            'avertissements': [],
            'stats': {}
        }
        
        # 1. Vérifier les conflits d'étudiants (même créneau)
        for creneau, salles_ue in self.planning.items():
            ues_creneau = list(salles_ue.values())
            for i, code1 in enumerate(ues_creneau):
                for code2 in ues_creneau[i+1:]:
                    ue1 = self.graphe.sommets[code1]
                    ue2 = self.graphe.sommets[code2]
                    if ue1.etudiants & ue2.etudiants:
                        rapport['erreurs'].append(
                            f"CONFLIT ETUDIANT: {code1} et {code2} au creneau {creneau}"
                        )
                        rapport['contraintes_respectees'] = False
        
        # 2. Vérifier les conflits de surveillant
        for creneau, salles_ue in self.planning.items():
            ues_creneau = list(salles_ue.values())
            surveillants = {}
            for code in ues_creneau:
                surv = self.graphe.sommets[code].surveillant
                if surv in surveillants:
                    rapport['erreurs'].append(
                        f"CONFLIT SURVEILLANT: {surveillants[surv]} et {code} "
                        f"partagent {surv} au creneau {creneau}"
                    )
                    rapport['contraintes_respectees'] = False
                else:
                    surveillants[surv] = code
        
        # 3. Vérifier les capacités des salles
        for code, affectation in self.affectations.items():
            if affectation['salle'] == 'NON_AFFECTE':
                rapport['avertissements'].append(
                    f"{code} non affecte a une salle (creneau {affectation['creneau']})"
                )
                continue
            
            ue = self.graphe.sommets[code]
            salle = next((s for s in self.salles if s.nom == affectation['salle']), None)
            if salle and ue.nb_inscrits > salle.capacite:
                rapport['erreurs'].append(
                    f"CAPACITE INSUFFISANTE: {code} ({ue.nb_inscrits} etudiants) "
                    f"dans {salle.nom} ({salle.capacite} places)"
                )
                rapport['contraintes_respectees'] = False
        
        # 4. Vérifier les types de salles (labo)
        for code, affectation in self.affectations.items():
            if affectation['salle'] == 'NON_AFFECTE':
                continue
            ue = self.graphe.sommets[code]
            salle = next((s for s in self.salles if s.nom == affectation['salle']), None)
            if salle and ue.besoin_labo and not salle.est_labo:
                rapport['erreurs'].append(
                    f"TYPE SALLE INCORRECT: {code} necessite un labo mais "
                    f"est dans {salle.nom} (standard)"
                )
                rapport['contraintes_respectees'] = False
        
        # 5. Vérifier l'espacement des filières (contrainte 2.2)
        for code1, aff1 in self.affectations.items():
            for code2, aff2 in self.affectations.items():
                if code1 >= code2:
                    continue
                ue1 = self.graphe.sommets[code1]
                ue2 = self.graphe.sommets[code2]
                if ue1.filiere == ue2.filiere:
                    if abs(aff1['creneau'] - aff2['creneau']) == 1:
                        rapport['avertissements'].append(
                            f"ESPACEMENT FILIERE: {code1} et {code2} ({ue1.filiere}) "
                            f"sont en creneaux consecutifs ({aff1['creneau']} et {aff2['creneau']})"
                        )
        
        # Statistiques
        nb_affectes = sum(1 for a in self.affectations.values() if a['salle'] != 'NON_AFFECTE')
        rapport['stats'] = {
            'total_ues': len(self.graphe.sommets),
            'ues_affectees': nb_affectes,
            'ues_non_affectees': len(self.graphe.sommets) - nb_affectes,
            'nb_creneaux': len(self.planning),
            'nb_erreurs': len(rapport['erreurs']),
            'nb_avertissements': len(rapport['avertissements'])
        }
        
        return rapport
    
    def exporter_csv(self, chemin='data/planning_final.csv'):
        """Exporte le planning final au format CSV (creneau x salle)"""
        if not self.planning:
            return None
        
        # Créer le tableau creneau x salle
        tous_creneaux = sorted(self.planning.keys())
        toutes_salles = sorted(set(s.nom for s in self.salles))
        
        with open(chemin, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # En-tête
            header = ['Creneau'] + toutes_salles
            writer.writerow(header)
            
            # Données
            for creneau in tous_creneaux:
                row = [f"Creneau_{creneau}"]
                for salle in toutes_salles:
                    if salle in self.planning.get(creneau, {}):
                        code = self.planning[creneau][salle]
                        ue = self.graphe.sommets[code]
                        row.append(f"{code} ({ue.nb_inscrits})")
                    else:
                        row.append('')
                writer.writerow(row)
        
        return chemin
    
    def get_planning_table(self):
        """Retourne le planning sous forme de tableau pour l'affichage web"""
        table = []
        for creneau in sorted(self.planning.keys()):
            for salle, code in sorted(self.planning[creneau].items()):
                ue = self.graphe.sommets[code]
                table.append({
                    'creneau': creneau,
                    'salle': salle,
                    'code_ue': code,
                    'nom_ue': ue.nom,
                    'filiere': ue.filiere,
                    'effectif': ue.nb_inscrits,
                    'surveillant': ue.surveillant,
                    'besoin_labo': ue.besoin_labo
                })
        return table
