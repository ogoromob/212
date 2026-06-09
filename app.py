"""
Application Flask - Planification d'Examens par Coloration de Graphes
Point d'entree principal
"""
import os
import json
import csv
import io
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

from graphe import GrapheConflit
from coloration import SolveurColoration
from affectation import GenerateurPlanning, creneau_to_horaire

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Donnees globales (simule une base de donnees en memoire)
donnees_session = {
    'graphe': None,
    'salles': [],
    'solveur': None,
    'planning': None,
    'resultats': {},
    'interdictions': []
}

# ============================================================
# ROUTES PRINCIPALES
# ============================================================

@app.route('/')
def index():
    """Page d'accueil avec l'interface principale"""
    return render_template('index.html')

@app.route('/api/etat')
def etat():
    """Retourne l'etat actuel de la session"""
    return jsonify({
        'donnees_chargees': donnees_session['graphe'] is not None,
        'nb_ues': len(donnees_session['graphe'].sommets) if donnees_session['graphe'] else 0,
        'nb_salles': len(donnees_session['salles']),
        'planning_genere': donnees_session['planning'] is not None
    })

# ============================================================
# API - Gestion des donnees (Upload CSV)
# ============================================================

@app.route('/api/charger-donnees', methods=['POST'])
def charger_donnees():
    """Charge les donnees depuis des fichiers CSV uploades ou utilise les donnees par defaut"""
    try:
        graphe = GrapheConflit()
        
        # Verifier si des fichiers sont uploades
        if 'fichier_ue' in request.files and request.files['fichier_ue'].filename:
            # Mode upload
            f_ue = request.files['fichier_ue']
            f_insc = request.files.get('fichier_inscriptions')
            f_salles = request.files.get('fichier_salles')
            
            chemin_ue = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f_ue.filename))
            f_ue.save(chemin_ue)
            
            chemin_insc = 'data/inscriptions.csv'
            if f_insc and f_insc.filename:
                chemin_insc = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f_insc.filename))
                f_insc.save(chemin_insc)
            
            chemin_salles = 'data/salles.csv'
            if f_salles and f_salles.filename:
                chemin_salles = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f_salles.filename))
                f_salles.save(chemin_salles)
            
            salles = graphe.charger_donnees(chemin_ue, chemin_insc, chemin_salles)
        else:
            # Mode donnees par defaut
            salles = graphe.charger_donnees('data/ues.csv', 'data/inscriptions.csv', 'data/salles.csv')
        
        # Construire le graphe avec les interdictions explicites
        interdictions = donnees_session.get('interdictions', [])
        stats = graphe.construire_graphe(interdictions=interdictions)
        
        # Stocker en session
        donnees_session['graphe'] = graphe
        donnees_session['salles'] = salles
        donnees_session['planning'] = None
        donnees_session['solveur'] = None
        
        return jsonify({
            'success': True,
            'message': 'Donnees chargees avec succes',
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/donnees-par-defaut', methods=['POST'])
def charger_donnees_par_defaut():
    """Charge les donnees de demonstration"""
    return charger_donnees()

# ============================================================
# API - Interdictions explicites
# ============================================================

@app.route('/api/interdictions', methods=['GET', 'POST'])
def gerer_interdictions():
    """GET: liste les interdictions, POST: ajoute/supprime des interdictions"""
    if request.method == 'GET':
        return jsonify({
            'interdictions': donnees_session.get('interdictions', [])
        })
    
    if request.method == 'POST':
        data = request.get_json() or {}
        action = data.get('action', 'add')
        
        if action == 'add':
            paire = data.get('paire')
            if paire and len(paire) == 2:
                donnees_session['interdictions'].append(paire)
                # Reconstruire le graphe si les donnees sont chargees
                if donnees_session['graphe']:
                    donnees_session['graphe'].construire_graphe(interdictions=donnees_session['interdictions'])
                return jsonify({'success': True, 'interdictions': donnees_session['interdictions']})
        
        elif action == 'remove':
            paire = data.get('paire')
            if paire and len(paire) == 2:
                donnees_session['interdictions'] = [
                    i for i in donnees_session['interdictions']
                    if not (i[0] == paire[0] and i[1] == paire[1])
                ]
                if donnees_session['graphe']:
                    donnees_session['graphe'].construire_graphe(interdictions=donnees_session['interdictions'])
                return jsonify({'success': True, 'interdictions': donnees_session['interdictions']})
        
        elif action == 'clear':
            donnees_session['interdictions'] = []
            if donnees_session['graphe']:
                donnees_session['graphe'].construire_graphe(interdictions=[])
            return jsonify({'success': True, 'interdictions': []})
        
        return jsonify({'success': False, 'error': 'Action invalide'}), 400

# ============================================================
# API - Visualisation du graphe
# ============================================================

@app.route('/api/graphe/stats')
def graphe_stats():
    """Retourne les statistiques du graphe"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    return jsonify(donnees_session['graphe'].get_stats())

@app.route('/api/graphe/visualiser')
def graphe_visualiser():
    """Genere et retourne l'image du graphe"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    hd = request.args.get('hd', 'false').lower() == 'true'
    chemin = donnees_session['graphe'].visualiser(
        donnees_session['solveur'].couleurs if donnees_session['solveur'] else None,
        hd=hd
    )
    
    return send_file(chemin, mimetype='image/png')

@app.route('/api/graphe/matrice')
def graphe_matrice():
    """Retourne la matrice d'adjacence"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    graphe = donnees_session['graphe']
    codes = list(graphe.sommets.keys())
    
    return jsonify({
        'codes': codes,
        'matrice': graphe.matrice_adj
    })

@app.route('/api/graphe/liste-adjacence')
def graphe_liste_adj():
    """Retourne la liste d'adjacence"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    return jsonify(dict(donnees_session['graphe'].liste_adj))

# ============================================================
# API - Algorithmes de coloration
# ============================================================

@app.route('/api/coloration/welsh-powell', methods=['POST'])
def coloration_welsh_powell():
    """Execute l'algorithme Welsh-Powell"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    data = request.get_json() or {}
    respecter_filiere = data.get('respecter_filiere', True)
    
    solveur = SolveurColoration(donnees_session['graphe'])
    resultat = solveur.welsh_powell(respecter_filiere)
    
    donnees_session['solveur'] = solveur
    donnees_session['planning'] = None
    donnees_session['resultats']['welsh_powell'] = resultat
    
    return jsonify(resultat)

@app.route('/api/coloration/dsatur', methods=['POST'])
def coloration_dsatur():
    """Execute l'algorithme DSATUR"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    data = request.get_json() or {}
    respecter_filiere = data.get('respecter_filiere', True)
    
    solveur = SolveurColoration(donnees_session['graphe'])
    resultat = solveur.dsatur(respecter_filiere)
    
    donnees_session['solveur'] = solveur
    donnees_session['planning'] = None
    donnees_session['resultats']['dsatur'] = resultat
    
    return jsonify(resultat)

@app.route('/api/coloration/comparer', methods=['POST'])
def comparer_algorithmes():
    """Compare Welsh-Powell et DSATUR"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    # Executer les deux algorithmes
    solveur_wp = SolveurColoration(donnees_session['graphe'])
    result_wp = solveur_wp.welsh_powell()
    
    solveur_ds = SolveurColoration(donnees_session['graphe'])
    result_ds = solveur_ds.dsatur()
    
    return jsonify({
        'welsh_powell': result_wp,
        'dsatur': result_ds,
        'comparaison': {
            'nb_creneaux_wp': result_wp['nb_creneaux'],
            'nb_creneaux_ds': result_ds['nb_creneaux'],
            'temps_wp': result_wp['temps_execution'],
            'temps_ds': result_ds['temps_execution'],
            'gagnant_creneaux': 'DSATUR' if result_ds['nb_creneaux'] <= result_wp['nb_creneaux'] else 'Welsh-Powell',
            'gagnant_temps': 'DSATUR' if result_ds['temps_execution'] <= result_wp['temps_execution'] else 'Welsh-Powell'
        }
    })

# ============================================================
# API - Affectation des salles
# ============================================================

@app.route('/api/planning/generer', methods=['POST'])
def generer_planning():
    """Genere le planning final avec affectation des salles"""
    if not donnees_session['graphe'] or not donnees_session['solveur']:
        return jsonify({'error': 'Graphe ou coloration manquante'}), 400
    
    generateur = GenerateurPlanning(
        donnees_session['graphe'],
        donnees_session['salles'],
        donnees_session['solveur']
    )
    
    planning = generateur.affecter_salles()
    rapport = generateur.verifier_contraintes()
    
    donnees_session['planning'] = generateur
    
    return jsonify({
        'success': True,
        'planning': generateur.get_planning_table(),
        'rapport': rapport,
        'nb_creneaux': len(planning)
    })

@app.route('/api/planning/tableau')
def planning_tableau():
    """Retourne le planning sous forme de tableau"""
    if not donnees_session['planning']:
        return jsonify({'error': 'Planning non genere'}), 400
    
    return jsonify(donnees_session['planning'].get_planning_table())

@app.route('/api/planning/rapport')
def planning_rapport():
    """Retourne le rapport d'audit"""
    if not donnees_session['planning']:
        return jsonify({'error': 'Planning non genere'}), 400
    
    return jsonify(donnees_session['planning'].verifier_contraintes())

@app.route('/api/planning/export-csv')
def export_csv():
    """Exporte le planning au format CSV"""
    if not donnees_session['planning']:
        return jsonify({'error': 'Planning non genere'}), 400
    
    chemin = donnees_session['planning'].exporter_csv()
    
    return send_file(
        chemin,
        mimetype='text/csv',
        as_attachment=True,
        download_name='planning_examens.csv'
    )

# ============================================================
# API - Export PNG HD
# ============================================================

@app.route('/api/export/png-hd')
def export_png_hd():
    """Exporte le graphe en PNG haute definition"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    chemin = donnees_session['graphe'].visualiser(
        donnees_session['solveur'].couleurs if donnees_session['solveur'] else None,
        chemin_sortie='static/graphe_hd.png',
        hd=True
    )
    
    return send_file(
        chemin,
        mimetype='image/png',
        as_attachment=True,
        download_name='graphe_conflits_hd.png'
    )

# ============================================================
# API - Informations UEs et Salles
# ============================================================

@app.route('/api/ues')
def liste_ues():
    """Liste toutes les UEs"""
    if not donnees_session['graphe']:
        return jsonify({'error': 'Aucune donnee chargee'}), 400
    
    ues = []
    for code, ue in donnees_session['graphe'].sommets.items():
        ues.append({
            'code': code,
            'nom': ue.nom,
            'nb_inscrits': ue.nb_inscrits,
            'surveillant': ue.surveillant,
            'filiere': ue.filiere,
            'besoin_labo': ue.besoin_labo
        })
    
    return jsonify(ues)

@app.route('/api/salles')
def liste_salles():
    """Liste toutes les salles"""
    salles = []
    for s in donnees_session['salles']:
        salles.append({
            'nom': s.nom,
            'capacite': s.capacite,
            'est_labo': s.est_labo
        })
    return jsonify(salles)

# ============================================================
# API - Conversion creneau -> horaire
# ============================================================

@app.route('/api/horaires')
def liste_horaires():
    """Retourne la liste des creneaux avec leurs horaires"""
    if not donnees_session['solveur']:
        return jsonify({'error': 'Coloration non effectuee'}), 400
    
    creneaux = sorted(set(donnees_session['solveur'].couleurs.values()))
    horaires = {}
    for c in creneaux:
        horaires[c] = creneau_to_horaire(c)
    
    return jsonify(horaires)

# ============================================================
# Démarrage
# ============================================================

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
