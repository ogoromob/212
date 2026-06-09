"""
Module Graphe - Construction du graphe de conflits
Partie 1 du cahier des charges
"""
import csv
import os
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

class UE:
    """Classe representant une Unite d'Enseignement"""
    def __init__(self, code, nom, nb_inscrits, surveillant, filiere, besoin_labo):
        self.code = code
        self.nom = nom
        self.nb_inscrits = int(nb_inscrits)
        self.surveillant = surveillant
        self.filiere = filiere
        self.besoin_labo = besoin_labo.lower() == 'true' if isinstance(besoin_labo, str) else bool(besoin_labo)
        self.etudiants = set()
    
    def __repr__(self):
        return f"UE({self.code}, {self.filiere}, {self.nb_inscrits})"

class Salle:
    """Classe representant une Salle d'examen"""
    def __init__(self, nom, capacite, est_labo):
        self.nom = nom
        self.capacite = int(capacite)
        self.est_labo = est_labo.lower() == 'true' if isinstance(est_labo, str) else bool(est_labo)
    
    def __repr__(self):
        return f"Salle({self.nom}, cap={self.capacite}, labo={self.est_labo})"

class GrapheConflit:
    """Graphe de conflits entre UEs"""
    def __init__(self):
        self.sommets = {}  # code_ue -> UE
        self.matrice_adj = []  # Matrice d'adjacence
        self.liste_adj = defaultdict(list)  # Liste d'adjacence
        self.aretes = []  # Liste des aretes (code1, code2)
    
    def charger_donnees(self, chemin_ue, chemin_inscriptions, chemin_salles):
        """Charge les donnees depuis les fichiers CSV"""
        # Charger les UEs
        with open(chemin_ue, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ue = UE(
                    row['code_ue'], row['nom'], row['nb_inscrits'],
                    row['surveillant'], row['filiere'], row['besoin_labo']
                )
                self.sommets[ue.code] = ue
        
        # Charger les inscriptions etudiants
        with open(chemin_inscriptions, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code_ue = row['code_ue']
                id_etudiant = row['id_etudiant']
                if code_ue in self.sommets:
                    self.sommets[code_ue].etudiants.add(id_etudiant)
        
        # Charger les salles
        salles = []
        with open(chemin_salles, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                salle = Salle(row['nom_salle'], row['capacite'], row['est_labo'])
                salles.append(salle)
        
        return salles
    
    def construire_graphe(self, interdictions=None):
        """Construit le graphe de conflits avec matrice et liste d'adjacence"""
        codes = list(self.sommets.keys())
        n = len(codes)
        
        # Initialiser la matrice d'adjacence (n x n)
        self.matrice_adj = [[0] * n for _ in range(n)]
        self.liste_adj = defaultdict(list)
        self.aretes = []
        
        # Index des codes pour la matrice
        index = {code: i for i, code in enumerate(codes)}
        
        # Parcourir toutes les paires d'UEs
        for i, code1 in enumerate(codes):
            for j, code2 in enumerate(codes):
                if i >= j:
                    continue
                
                ue1 = self.sommets[code1]
                ue2 = self.sommets[code2]
                
                # Conflit d'etudiants (intersection non vide)
                conflit_etudiants = len(ue1.etudiants & ue2.etudiants) > 0
                
                # Conflit de surveillant
                conflit_surveillant = ue1.surveillant == ue2.surveillant and ue1.surveillant != ''
                
                # Interdiction explicite
                conflit_interdiction = False
                if interdictions:
                    for interdit in interdictions:
                        if (code1 == interdit[0] and code2 == interdit[1]) or \
                           (code1 == interdit[1] and code2 == interdit[0]):
                            conflit_interdiction = True
                            break
                
                # Creer l'arete si au moins un conflit
                if conflit_etudiants or conflit_surveillant or conflit_interdiction:
                    self.matrice_adj[i][j] = 1
                    self.matrice_adj[j][i] = 1
                    self.liste_adj[code1].append(code2)
                    self.liste_adj[code2].append(code1)
                    self.aretes.append((code1, code2))
        
        return {
            'nb_sommets': n,
            'nb_aretes': len(self.aretes),
            'degres': {code: len(self.liste_adj[code]) for code in codes}
        }
    
    def visualiser(self, couleurs=None, chemin_sortie='static/graphe.png'):
        """Visualise le graphe avec networkx et matplotlib"""
        G = nx.Graph()
        
        # Ajouter les noeuds
        for code in self.sommets:
            G.add_node(code)
        
        # Ajouter les aretes
        for code1, code2 in self.aretes:
            G.add_edge(code1, code2)
        
        # Couleurs des noeuds
        if couleurs:
            node_colors = []
            for code in G.nodes():
                if code in couleurs and couleurs[code] is not None:
                    # Utiliser une palette de couleurs distinctes
                    couleur = couleurs[code] % 12  # 12 couleurs max pour visibilite
                    node_colors.append(plt.cm.Set3(couleur / 12))
                else:
                    node_colors.append('lightgray')
        else:
            node_colors = ['skyblue'] * len(G.nodes())
        
        # Dessiner le graphe
        plt.figure(figsize=(14, 10))
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        nx.draw(G, pos, 
                node_color=node_colors,
                node_size=800,
                with_labels=True,
                font_size=8,
                font_weight='bold',
                edge_color='gray',
                width=1.0,
                alpha=0.9)
        
        plt.title("Graphe de Conflits des UEs\n(Deux UEs reliees ne peuvent pas etre au meme creneau)", 
                  fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        os.makedirs(os.path.dirname(chemin_sortie) if os.path.dirname(chemin_sortie) else '.', exist_ok=True)
        plt.savefig(chemin_sortie, dpi=150, bbox_inches='tight')
        plt.close()
        
        return chemin_sortie
    
    def get_stats(self):
        """Retourne les statistiques du graphe"""
        codes = list(self.sommets.keys())
        degres = {code: len(self.liste_adj[code]) for code in codes}
        degre_max = max(degres.values()) if degres else 0
        degre_min = min(degres.values()) if degres else 0
        degre_moy = sum(degres.values()) / len(degres) if degres else 0
        
        return {
            'nb_sommets': len(codes),
            'nb_aretes': len(self.aretes),
            'degre_max': degre_max,
            'degre_min': degre_min,
            'degre_moyen': round(degre_moy, 2),
            'degres_detail': degres
        }
