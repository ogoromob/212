"""
Module Affectation - Affectation des salles et generation du planning final
Partie 3 du cahier des charges
"""
import csv
import os
from collections import defaultdict

# Conversion creneau -> jour/heure (UY1 style)
JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
HEURES = ['07h30-09h30', '10h00-12h00', '14h00-16h00', '16h30-18h30']

def creneau_to_horaire(creneau):
    """Convertit un numero de creneau en jour/heure"""
    if creneau < 0:
        return "Invalide"
    jour_index = creneau // len(HEURES)
    heure_index = creneau % len(HEURES)
    if jour_index >= len(JOURS):
        # Au-dela de la semaine, on continue
        jour_index = jour_index % len(JOURS)
        semaine = 1 + (creneau // (len(JOURS) * len(HEURES)))
        return f"Sem{semaine} {JOURS[jour_index]} {HEURES[heure_index]}"
    return f"{JOURS[jour_index]} {HEURES[heure_index]}"


class GenerateurPlanning:
    """Gere l'affectation des salles et la generation du planning final"""
    
    def __init__(self, graphe, salles, solveur):
        self.graphe = graphe
        self.salles = salles
        self.solveur = solveur
        self.planning = {}  # creneau -> {salle: code_ue}
        self.affectations = {}  # code_ue -> {'creneau': int, 'salle': str}
    
    def affecter_salles(self, equilibrer=True):
        """
        Algorithme First Fit Decreasing pour l'affectation des salles:
        1. Trier les salles par capacite decroissante
        2. Pour chaque creneau, trier les UEs par effectif decroissant
        3. Affecter chaque UE a la premiere salle disponible qui convient
        """
        # Trier les salles par capacite decroissante
        salles_triees = sorted(self.salles, key=lambda s: -s.capacite)
        
        # Grouper les UEs par creneau
        creneaux_ues = defaultdict(list)
        for code, couleur in self.solveur.couleurs.items():
            creneaux_ues[couleur].append(code)
        
        # Pour chaque creneau
        for creneau, codes_ue in sorted(creneaux_ues.items()):
            # Trier les UEs par effectif decroissant (priorite aux grands effectifs)
            codes_ue.sort(key=lambda c: -self.graphe.sommets[c].nb_inscrits)
            
            # Salles disponibles pour ce creneau
            salles_disponibles = list(salles_triees)
            self.planning[creneau] = {}
            
            for code in codes_ue:
                ue = self.graphe.sommets[code]
                salle_attribuee = None
                
                # Chercher la premiere salle qui convient
                for salle in salles_disponibles:
                    # Verifier la capacite
                    if salle.capacite < ue.nb_inscrits:
                        continue
                    
                    # Verifier le type de salle (labo)
                    if ue.besoin_labo and not salle.est_labo:
                        continue
                    
                    # Salle trouvee
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
                    # Aucune salle disponible - marquer comme non affecte
                    self.affectations[code] = {
                        'creneau': creneau,
                        'salle': 'NON_AFFECTE'
                    }
        
        return self.planning
    
    def verifier_contraintes(self):
        """
        Verifie automatiquement le respect de toutes les contraintes
        Retourne un rapport d'audit detaille avec statut OK/KO par contrainte
        """
        rapport = {
            'contraintes_respectees': True,
            'details': {},
            'erreurs': [],
            'avertissements': [],
            'stats': {}
        }
        
        # --- CONTRAINTES OBLIGATOIRES (2.1) ---
        
        # 1. Conflits d'etudiants (meme creneau)
        conflits_etudiants = []
        for creneau, salles_ue in self.planning.items():
            ues_creneau = list(salles_ue.values())
            for i, code1 in enumerate(ues_creneau):
                for code2 in ues_creneau[i+1:]:
                    ue1 = self.graphe.sommets[code1]
                    ue2 = self.graphe.sommets[code2]
                    if ue1.etudiants & ue2.etudiants:
                        conflits_etudiants.append(f"{code1} et {code2} au creneau {creneau}")
        
        rapport['details']['conflits_etudiants'] = {
            'status': 'OK' if len(conflits_etudiants) == 0 else 'KO',
            'label': 'Aucun etudiant en conflit',
            'description': 'Deux UEs partageant des etudiants ne sont pas au meme creneau',
            'count': len(conflits_etudiants),
            'items': conflits_etudiants[:10]  # Limiter l'affichage
        }
        if conflits_etudiants:
            rapport['contraintes_respectees'] = False
            rapport['erreurs'].extend(conflits_etudiants)
        
        # 2. Conflits de surveillant
        conflits_surveillant = []
        for creneau, salles_ue in self.planning.items():
            ues_creneau = list(salles_ue.values())
            surveillants = {}
            for code in ues_creneau:
                surv = self.graphe.sommets[code].surveillant
                if surv in surveillants:
                    conflits_surveillant.append(
                        f"{surveillants[surv]} et {code} partagent {surv} au creneau {creneau}"
                    )
                else:
                    surveillants[surv] = code
        
        rapport['details']['conflits_surveillant'] = {
            'status': 'OK' if len(conflits_surveillant) == 0 else 'KO',
            'label': 'Aucun surveillant en conflit',
            'description': 'Un surveillant ne supervise pas deux UEs simultanement',
            'count': len(conflits_surveillant),
            'items': conflits_surveillant[:10]
        }
        if conflits_surveillant:
            rapport['contraintes_respectees'] = False
            rapport['erreurs'].extend(conflits_surveillant)
        
        # 3. Capacite des salles
        capacites_ok = True
        capacites_ko = []
        for code, affectation in self.affectations.items():
            if affectation['salle'] == 'NON_AFFECTE':
                continue
            ue = self.graphe.sommets[code]
            salle = next((s for s in self.salles if s.nom == affectation['salle']), None)
            if salle and ue.nb_inscrits > salle.capacite:
                capacites_ok = False
                capacites_ko.append(
                    f"{code} ({ue.nb_inscrits} inscrits) dans {salle.nom} ({salle.capacite} places)"
                )
        
        rapport['details']['capacite_salles'] = {
            'status': 'OK' if capacites_ok else 'KO',
            'label': 'Capacite des salles respectee',
            'description': 'Chaque salle accueille au plus son nombre de places',
            'count': len(capacites_ko),
            'items': capacites_ko[:10]
        }
        if not capacites_ok:
            rapport['contraintes_respectees'] = False
            rapport['erreurs'].extend(capacites_ko)
        
        # 4. Type de salle (labo)
        labo_ok = True
        labo_ko = []
        for code, affectation in self.affectations.items():
            if affectation['salle'] == 'NON_AFFECTE':
                continue
            ue = self.graphe.sommets[code]
            salle = next((s for s in self.salles if s.nom == affectation['salle']), None)
            if salle and ue.besoin_labo and not salle.est_labo:
                labo_ok = False
                labo_ko.append(f"{code} necessite un labo mais est en salle standard {salle.nom}")
        
        rapport['details']['type_salle'] = {
            'status': 'OK' if labo_ok else 'KO',
            'label': 'Type de salle correct',
            'description': 'Les UEs necessitant un labo sont affectees a une salle labo',
            'count': len(labo_ko),
            'items': labo_ko[:10]
        }
        if not labo_ok:
            rapport['contraintes_respectees'] = False
            rapport['erreurs'].extend(labo_ko)
        
        # 5. Une salle par examen (pas de double occupation)
        double_salle = []
        for creneau, salles_ue in self.planning.items():
            salles_vues = {}
            for salle, code in salles_ue.items():
                if salle in salles_vues:
                    double_salle.append(f"Salle {salle} occupee par {salles_vues[salle]} et {code} au creneau {creneau}")
                else:
                    salles_vues[salle] = code
        
        rapport['details']['unicite_salle'] = {
            'status': 'OK' if len(double_salle) == 0 else 'KO',
            'label': 'Une salle par examen',
            'description': 'Chaque salle accueille au plus un examen par creneau',
            'count': len(double_salle),
            'items': double_salle[:10]
        }
        if double_salle:
            rapport['contraintes_respectees'] = False
            rapport['erreurs'].extend(double_salle)
        
        # --- CONTRAINTES SOUHAITEES (2.2) ---
        
        # 6. Espacement des filieres
        espacement_ok = True
        espacement_ko = []
        for code1, aff1 in self.affectations.items():
            for code2, aff2 in self.affectations.items():
                if code1 >= code2:
                    continue
                ue1 = self.graphe.sommets[code1]
                ue2 = self.graphe.sommets[code2]
                if ue1.filiere == ue2.filiere:
                    if abs(aff1['creneau'] - aff2['creneau']) == 1:
                        espacement_ok = False
                        espacement_ko.append(
                            f"{code1} et {code2} ({ue1.filiere}) creneaux consecutifs "
                            f"({aff1['creneau']} et {aff2['creneau']})"
                        )
        
        rapport['details']['espacement_filiere'] = {
            'status': 'OK' if espacement_ok else 'AVERTISSEMENT',
            'label': 'Espacement des filieres',
            'description': 'Deux UEs de la meme filiere ne sont pas en creneaux consecutifs',
            'count': len(espacement_ko),
            'items': espacement_ko[:10]
        }
        rapport['avertissements'].extend(espacement_ko)
        
        # 7. Equilibre de la charge
        creneaux_count = defaultdict(int)
        for aff in self.affectations.values():
            creneaux_count[aff['creneau']] += 1
        
        max_count = max(creneaux_count.values()) if creneaux_count else 0
        min_count = min(creneaux_count.values()) if creneaux_count else 0
        ecart = max_count - min_count
        equilibre_ok = ecart <= 2
        
        rapport['details']['equilibre_charge'] = {
            'status': 'OK' if equilibre_ok else 'AVERTISSEMENT',
            'label': 'Equilibre de la charge',
            'description': f'Repartition des examens: min={min_count}, max={max_count}, ecart={ecart}',
            'count': ecart,
            'items': [f"Creneaubusy: {dict(creneaux_count)}"]
        }
        if not equilibre_ok:
            rapport['avertissements'].append(
                f"Ecart de charge important: {max_count} vs {min_count} examens par creneau"
            )
        
        # 8. UEs non affectees
        non_affectes = [code for code, aff in self.affectations.items() if aff['salle'] == 'NON_AFFECTE']
        
        rapport['details']['affectation_complete'] = {
            'status': 'OK' if len(non_affectes) == 0 else 'KO',
            'label': 'Affectation complete',
            'description': 'Toutes les UEs sont affectees a une salle',
            'count': len(non_affectes),
            'items': non_affectes[:10]
        }
        if non_affectes:
            rapport['contraintes_respectees'] = False
            rapport['erreurs'].extend([f"{code} non affecte" for code in non_affectes])
        
        # Statistiques
        nb_affectes = sum(1 for a in self.affectations.values() if a['salle'] != 'NON_AFFECTE')
        rapport['stats'] = {
            'total_ues': len(self.graphe.sommets),
            'ues_affectees': nb_affectes,
            'ues_non_affectees': len(self.graphe.sommets) - nb_affectes,
            'nb_creneaux': len(self.planning),
            'nb_erreurs': len(rapport['erreurs']),
            'nb_avertissements': len(rapport['avertissements']),
            'equilibre': dict(creneaux_count)
        }
        
        return rapport
    
    def exporter_csv(self, chemin='data/planning_final.csv'):
        """Exporte le planning final au format CSV (creneau x salle)"""
        if not self.planning:
            return None
        
        # Creer le tableau creneau x salle
        tous_creneaux = sorted(self.planning.keys())
        toutes_salles = sorted(set(s.nom for s in self.salles))
        
        with open(chemin, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # En-tete
            header = ['Creneau', 'Horaire'] + toutes_salles
            writer.writerow(header)
            
            # Donnees
            for creneau in tous_creneaux:
                horaire = creneau_to_horaire(creneau)
                row = [f"Creneau_{creneau}", horaire]
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
                    'horaire': creneau_to_horaire(creneau),
                    'salle': salle,
                    'code_ue': code,
                    'nom_ue': ue.nom,
                    'filiere': ue.filiere,
                    'effectif': ue.nb_inscrits,
                    'surveillant': ue.surveillant,
                    'besoin_labo': ue.besoin_labo
                })
        return table
