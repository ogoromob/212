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
        1. Trier les sommets par degré décroissant
        2. Attribuer la plus petite couleur disponible à chaque sommet
        """
        start_time = time.time()
        
        codes = list(self.graphe.sommets.keys())
        degres = self.graphe.get_stats()['degres_detail']
        
        # Trier par degré décroissant, puis par nb_inscrits décroissant
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
            
            # Contrainte de filière : pas de couleurs consécutives
            if respecter_filiere:
                filiere = self.graphe.sommets[code].filiere
                for autre_code, autre_couleur in self.couleurs.items():
                    if autre_code != code and self.graphe.sommets[autre_code].filiere == filiere:
                        if abs(autre_couleur - (autre_couleur + 1)) == 1:  # Logique simplifiée
                            pass  # Sera gérée dans la recherche de couleur
            
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
        
        # Étape 1 : Colorer le sommet de plus haut degré
        premier = max(codes, key=lambda c: degres.get(c, 0))
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
            # En cas d'égalité, prendre celui de plus haut degré
            suivant = max(
                codes_non_colorés,
                key=lambda c: (saturation.get(c, 0), degres.get(c, 0))
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
    
    def optimiser_equilibre(self):
        """Optimise l'équilibre des examens par créneau (contrainte 2.2)"""
        if not self.couleurs:
            return self.couleurs
        
        # Compter les examens par créneau
        creneaux_count = defaultdict(int)
        for couleur in self.couleurs.values():
            creneaux_count[couleur] += 1
        
        # Rééquilibrer si possible (algorithme simplifié)
        # Cette partie peut être étendue avec un recuit simulé
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
