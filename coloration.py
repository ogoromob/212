"""
Module Coloration - Algorithmes Welsh-Powell et DSATUR
Partie 2 du cahier des charges
"""
import time
from collections import defaultdict

class SolveurColoration:
    """Implémente les algorithmes de coloration de graphe"""
    
    def __init__(self, graphe):
        self.graphe = graphe
        self.couleurs = {}  # code_ue -> num_creneau
    
    def welsh_powell(self, respecter_filiere=True):
        """
        Algorithme Welsh-Powell:
        1. Trier les sommets par degré décroissant, puis par nb_inscrits décroissant
        2. Attribuer la plus petite couleur disponible à chaque sommet
        """
        start_time = time.time()
        
        codes = list(self.graphe.sommets.keys())
        degres = self.graphe.get_stats()['degres_detail']
        
        # Trier par degré décroissant, puis par nb_inscrits décroissant (Contrainte 2.2)
        codes_tries = sorted(
            codes,
            key=lambda c: (-degres.get(c, 0), -self.graphe.sommets[c].nb_inscrits)
        )
        
        self.couleurs = {}
        
        for code in codes_tries:
            # Couleurs interdites (voisins déjà colorés)
            couleurs_interdites = set()
            for voisin in self.graphe.liste_adj[code]:
                if voisin in self.couleurs:
                    couleurs_interdites.add(self.couleurs[voisin])
            
            # Trouver la plus petite couleur disponible
            couleur = 0
            while couleur in couleurs_interdites:
                couleur += 1
            
            # Vérifier la contrainte de filière (pas de couleurs consécutives)
            if respecter_filiere:
                while self._conflit_filiere(code, couleur):
                    couleur += 1
                    while couleur in couleurs_interdites:
                        couleur += 1
            
            self.couleurs[code] = couleur
        
        # Post-optimisation pour équilibrer la charge
        if respecter_filiere:
            self.couleurs = self._optimiser_equilibre(codes_tries)
        
        end_time = time.time()
        nb_creneaux = max(self.couleurs.values()) + 1 if self.couleurs else 0
        
        return {
            'algorithme': 'Welsh-Powell',
            'nb_creneaux': nb_creneaux,
            'temps_execution': round(end_time - start_time, 4),
            'couleurs': self.couleurs.copy()
        }
    
    def dsatur(self, respecter_filiere=True):
        """
        Algorithme DSATUR (Degree of SATURation):
        1. Colorer d'abord le sommet de plus haut degré
        2. À chaque étape, choisir le sommet avec le plus haut degré de saturation
           (nombre de couleurs différentes chez les voisins)
        3. Attribuer la plus petite couleur possible
        """
        start_time = time.time()
        
        codes = list(self.graphe.sommets.keys())
        degres = self.graphe.get_stats()['degres_detail']
        
        self.couleurs = {}
        codes_non_colorés = set(codes)
        
        # Étape 1 : Colorer le sommet de plus haut degré (puis plus grand effectif si égalité)
        premier = max(codes, key=lambda c: (degres.get(c, 0), self.graphe.sommets[c].nb_inscrits))
        self.couleurs[premier] = 0
        codes_non_colorés.remove(premier)
        
        while codes_non_colorés:
            # Calculer le degré de saturation pour chaque sommet non coloré
            saturation = {}
            for code in codes_non_colorés:
                couleurs_voisins = set()
                for voisin in self.graphe.liste_adj[code]:
                    if voisin in self.couleurs:
                        couleurs_voisins.add(self.couleurs[voisin])
                saturation[code] = len(couleurs_voisins)
            
            # Choisir le sommet avec la saturation la plus élevée
            # En cas d'égalité, prendre celui de plus haut degré, puis plus grand effectif
            suivant = max(
                codes_non_colorés,
                key=lambda c: (saturation.get(c, 0), degres.get(c, 0), self.graphe.sommets[c].nb_inscrits)
            )
            
            # Couleurs interdites
            couleurs_interdites = set()
            for voisin in self.graphe.liste_adj[suivant]:
                if voisin in self.couleurs:
                    couleurs_interdites.add(self.couleurs[voisin])
            
            # Trouver la plus petite couleur disponible
            couleur = 0
            while couleur in couleurs_interdites:
                couleur += 1
            
            # Vérifier la contrainte de filière
            if respecter_filiere:
                while self._conflit_filiere(suivant, couleur):
                    couleur += 1
                    while couleur in couleurs_interdites:
                        couleur += 1
            
            self.couleurs[suivant] = couleur
            codes_non_colorés.remove(suivant)
        
        # Post-optimisation pour équilibrer la charge
        if respecter_filiere:
            self.couleurs = self._optimiser_equilibre(codes)
        
        end_time = time.time()
        nb_creneaux = max(self.couleurs.values()) + 1 if self.couleurs else 0
        
        return {
            'algorithme': 'DSATUR',
            'nb_creneaux': nb_creneaux,
            'temps_execution': round(end_time - start_time, 4),
            'couleurs': self.couleurs.copy()
        }
    
    def _conflit_filiere(self, code, couleur):
        """Vérifie si attribuer cette couleur crée un conflit de filière (créneaux consécutifs)"""
        filiere = self.graphe.sommets[code].filiere
        for autre_code, autre_couleur in self.couleurs.items():
            if autre_code != code and self.graphe.sommets[autre_code].filiere == filiere:
                if abs(couleur - autre_couleur) == 1:
                    return True
        return False
    
    def _optimiser_equilibre(self, codes):
        """
        Post-optimisation pour équilibrer la charge entre créneaux (Contrainte 2.2).
        Essaye de réduire l'écart entre le créneau le plus chargé et le moins chargé.
        """
        if not self.couleurs:
            return self.couleurs
        
        # Compter les examens par créneau
        def count_par_creneau(couleurs):
            creneaux_count = defaultdict(int)
            for couleur in couleurs.values():
                creneaux_count[couleur] += 1
            return creneaux_count
        
        creneaux_count = count_par_creneau(self.couleurs)
        if not creneaux_count:
            return self.couleurs
        
        max_creneau = max(self.couleurs.values())
        
        # Objectif : lisser la répartition
        # Pour chaque UE, essayer de la déplacer vers un créneau moins chargé
        # tout en respectant les contraintes
        amelioration = True
        iterations = 0
        max_iterations = 100
        
        while amelioration and iterations < max_iterations:
            amelioration = False
            iterations += 1
            
            creneaux_count = count_par_creneau(self.couleurs)
            max_count = max(creneaux_count.values()) if creneaux_count else 0
            min_count = min(creneaux_count.values()) if creneaux_count else 0
            
            # Si l'écart est faible, on arrête
            if max_count - min_count <= 1:
                break
            
            # Trier les créneaux par nombre d'UEs décroissant
            creneaux_tries = sorted(creneaux_count.items(), key=lambda x: -x[1])
            
            for creneau_source, count_source in creneaux_tries:
                if count_source <= min_count + 1:
                    continue
                
                # Chercher une UE dans ce créneau qui pourrait bouger
                ues_source = [c for c, col in self.couleurs.items() if col == creneau_source]
                
                for ue_code in ues_source:
                    ue = self.graphe.sommets[ue_code]
                    
                    # Chercher un créneau cible moins chargé
                    for creneau_cible in range(max_creneau + 2):
                        if creneau_cible == creneau_source:
                            continue
                        if creneaux_count.get(creneau_cible, 0) >= count_source - 1:
                            continue
                        
                        # Vérifier que le déplacement est valide
                        # 1. Pas de conflit avec les voisins
                        conflit_voisin = False
                        for voisin in self.graphe.liste_adj[ue_code]:
                            if self.couleurs.get(voisin) == creneau_cible:
                                conflit_voisin = True
                                break
                        if conflit_voisin:
                            continue
                        
                        # 2. Pas de conflit de filière
                        conflit_filiere = False
                        for autre_code, autre_couleur in self.couleurs.items():
                            if autre_code != ue_code and self.graphe.sommets[autre_code].filiere == ue.filiere:
                                if abs(creneau_cible - autre_couleur) == 1:
                                    conflit_filiere = True
                                    break
                        if conflit_filiere:
                            continue
                        
                        # Déplacer l'UE
                        self.couleurs[ue_code] = creneau_cible
                        amelioration = True
                        break
                    
                    if amelioration:
                        break
                
                if amelioration:
                    break
        
        # Re-numéroter les créneaux pour éliminer les gaps
        couleurs_uniques = sorted(set(self.couleurs.values()))
        mapping = {old: new for new, old in enumerate(couleurs_uniques)}
        self.couleurs = {code: mapping[col] for code, col in self.couleurs.items()}
        
        return self.couleurs
    
    def get_creneaux_details(self):
        """Retourne les détails des créneaux"""
        creneaux = defaultdict(list)
        for code, couleur in self.couleurs.items():
            creneaux[couleur].append(code)
        
        result = {}
        for creneau, codes in sorted(creneaux.items()):
            result[creneau] = {
                'ues': codes,
                'nb_examens': len(codes),
                'filieres': list(set(self.graphe.sommets[c].filiere for c in codes))
            }
        return result
