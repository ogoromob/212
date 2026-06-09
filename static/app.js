/**
 * Application Frontend - Planification d'Examens
 * Gere l'interaction avec l'API Flask
 * Version complete avec interdictions, audit OK/KO, horaires
 */

// ============================================================
// VARIABLES GLOBALES
// ============================================================
let etat = {
    donneesChargees: false,
    grapheConstruit: false,
    colorationFaite: false,
    planningGenere: false,
    interdictions: []
};

let listeUEsCache = [];
let listeSallesCache = [];

// ============================================================
// NAVIGATION
// ============================================================
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
    
    document.getElementById('tab-' + tabName).classList.add('active');
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

// ============================================================
// MISE A JOUR DU STATUS
// ============================================================
function updateStatus() {
    const donnees = document.getElementById('status-donnees');
    const graphe = document.getElementById('status-graphe');
    const coloration = document.getElementById('status-coloration');
    const planning = document.getElementById('status-planning');
    
    const textDonnees = document.getElementById('text-donnees');
    const textGraphe = document.getElementById('text-graphe');
    const textColoration = document.getElementById('text-coloration');
    const textPlanning = document.getElementById('text-planning');
    
    if (etat.donneesChargees) {
        donnees.classList.add('ready');
        textDonnees.textContent = 'Chargees';
    }
    if (etat.grapheConstruit) {
        graphe.classList.add('ready');
        textGraphe.textContent = 'Construit';
    }
    if (etat.colorationFaite) {
        coloration.classList.add('ready');
        textColoration.textContent = 'Effectuee';
    }
    if (etat.planningGenere) {
        planning.classList.add('ready');
        textPlanning.textContent = 'Genere';
    }
}

// ============================================================
// CHARGEMENT DES DONNEES
// ============================================================
async function chargerDonneesParDefaut() {
    try {
        const response = await fetch('/api/charger-donnees', {
            method: 'POST',
            body: new FormData()
        });
        const data = await response.json();
        
        if (data.success) {
            etat.donneesChargees = true;
            updateStatus();
            
            document.getElementById('info-donnees').style.display = 'block';
            document.getElementById('btn-construire-graphe').disabled = false;
            
            afficherStatsDonnees(data.stats);
            await chargerListes();
            await chargerInterdictions();
            
            alert('Donnees chargees avec succes!');
        } else {
            alert('Erreur: ' + data.error);
        }
    } catch (error) {
        alert('Erreur de connexion: ' + error.message);
    }
}

async function chargerFichiersUpload() {
    const formData = new FormData();
    
    const fileUE = document.getElementById('file-ue').files[0];
    const fileInsc = document.getElementById('file-insc').files[0];
    const fileSalles = document.getElementById('file-salles').files[0];
    
    if (!fileUE) {
        alert('Veuillez selectionner au moins le fichier UEs.csv');
        return;
    }
    
    formData.append('fichier_ue', fileUE);
    if (fileInsc) formData.append('fichier_inscriptions', fileInsc);
    if (fileSalles) formData.append('fichier_salles', fileSalles);
    
    try {
        const response = await fetch('/api/charger-donnees', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            etat.donneesChargees = true;
            updateStatus();
            
            document.getElementById('info-donnees').style.display = 'block';
            document.getElementById('btn-construire-graphe').disabled = false;
            
            afficherStatsDonnees(data.stats);
            await chargerListes();
            await chargerInterdictions();
            
            alert('Fichiers importes avec succes!');
        } else {
            alert('Erreur: ' + data.error);
        }
    } catch (error) {
        alert('Erreur de connexion: ' + error.message);
    }
}

function afficherStatsDonnees(stats) {
    const container = document.getElementById('stats-donnees');
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.nb_sommets}</div>
            <div class="stat-label">UEs</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.nb_aretes}</div>
            <div class="stat-label">Conflits</div>
        </div>
    `;
}

async function chargerListes() {
    try {
        const [respUE, respSalles] = await Promise.all([
            fetch('/api/ues'),
            fetch('/api/salles')
        ]);
        
        const ues = await respUE.json();
        const salles = await respSalles.json();
        
        listeUEsCache = ues;
        listeSallesCache = salles;
        
        // Afficher les UEs
        let htmlUE = '<table><thead><tr><th>Code</th><th>Nom</th><th>Effectif</th><th>Surveillant</th><th>Filiere</th></tr></thead><tbody>';
        ues.forEach(ue => {
            htmlUE += `<tr>
                <td>${ue.code}</td>
                <td>${ue.nom}</td>
                <td>${ue.nb_inscrits}</td>
                <td>${ue.surveillant}</td>
                <td>${ue.filiere}</td>
            </tr>`;
        });
        htmlUE += '</tbody></table>';
        document.getElementById('liste-ues').innerHTML = htmlUE;
        
        // Afficher les salles
        let htmlSalles = '<table><thead><tr><th>Nom</th><th>Capacite</th><th>Labo</th></tr></thead><tbody>';
        salles.forEach(salle => {
            htmlSalles += `<tr>
                <td>${salle.nom}</td>
                <td>${salle.capacite}</td>
                <td>${salle.est_labo ? 'Oui' : 'Non'}</td>
            </tr>`;
        });
        htmlSalles += '</tbody></table>';
        document.getElementById('liste-salles').innerHTML = htmlSalles;
        
        // Mettre a jour les selects d'interdictions
        mettreAJourSelectsInterdictions(ues);
        
    } catch (error) {
        console.error('Erreur chargement listes:', error);
    }
}

// ============================================================
// INTERDICTIONS EXPLICITES
// ============================================================
function mettreAJourSelectsInterdictions(ues) {
    const sel1 = document.getElementById('interdiction-ue1');
    const sel2 = document.getElementById('interdiction-ue2');
    
    if (!sel1 || !sel2) return;
    
    const options = ues.map(ue => `<option value="${ue.code}">${ue.code} - ${ue.nom}</option>`).join('');
    
    sel1.innerHTML = '<option value="">UE 1</option>' + options;
    sel2.innerHTML = '<option value="">UE 2</option>' + options;
}

async function chargerInterdictions() {
    try {
        const resp = await fetch('/api/interdictions');
        const data = await resp.json();
        etat.interdictions = data.interdictions || [];
        afficherInterdictions();
    } catch (error) {
        console.error('Erreur chargement interdictions:', error);
    }
}

async function ajouterInterdiction() {
    const ue1 = document.getElementById('interdiction-ue1').value;
    const ue2 = document.getElementById('interdiction-ue2').value;
    
    if (!ue1 || !ue2) {
        alert('Veuillez selectionner deux UEs');
        return;
    }
    if (ue1 === ue2) {
        alert('Veuillez selectionner deux UEs differentes');
        return;
    }
    
    try {
        const response = await fetch('/api/interdictions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'add', paire: [ue1, ue2] })
        });
        
        const data = await response.json();
        if (data.success) {
            etat.interdictions = data.interdictions;
            afficherInterdictions();
            
            // Reconstruire le graphe si deja construit
            if (etat.grapheConstruit) {
                await reconstruireGraphe();
            }
        }
    } catch (error) {
        alert('Erreur: ' + error.message);
    }
}

async function clearInterdictions() {
    if (!confirm('Effacer toutes les interdictions explicites ?')) return;
    
    try {
        const response = await fetch('/api/interdictions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'clear' })
        });
        
        const data = await response.json();
        if (data.success) {
            etat.interdictions = [];
            afficherInterdictions();
            if (etat.grapheConstruit) {
                await reconstruireGraphe();
            }
        }
    } catch (error) {
        alert('Erreur: ' + error.message);
    }
}

async function supprimerInterdiction(ue1, ue2) {
    try {
        const response = await fetch('/api/interdictions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'remove', paire: [ue1, ue2] })
        });
        
        const data = await response.json();
        if (data.success) {
            etat.interdictions = data.interdictions;
            afficherInterdictions();
            if (etat.grapheConstruit) {
                await reconstruireGraphe();
            }
        }
    } catch (error) {
        alert('Erreur: ' + error.message);
    }
}

function afficherInterdictions() {
    const container = document.getElementById('liste-interdictions');
    
    if (etat.interdictions.length === 0) {
        container.innerHTML = '<p><em>Aucune interdiction explicite definie.</em></p>';
        return;
    }
    
    let html = '<p><strong>Interdictions actives:</strong></p>';
    etat.interdictions.forEach(paire => {
        html += `<span class="interdiction-item">
            ${paire[0]} <-> ${paire[1]}
            <button onclick="supprimerInterdiction('${paire[0]}', '${paire[1]}')" 
                    style="margin-left:5px;background:none;border:none;cursor:pointer;color:#721c24;font-weight:bold;">x</button>
        </span>`;
    });
    container.innerHTML = html;
}

async function reconstruireGraphe() {
    // Reconstruire le graphe avec les nouvelles interdictions
    document.getElementById('loading-graphe').classList.add('active');
    try {
        const respStats = await fetch('/api/graphe/stats');
        const stats = await respStats.json();
        afficherStatsGraphe(stats);
        
        document.getElementById('img-graphe').src = '/api/graphe/visualiser?' + new Date().getTime();
        await chargerMatriceAdj();
        await chargerListeAdj();
    } catch (error) {
        console.error('Erreur reconstruction graphe:', error);
    } finally {
        document.getElementById('loading-graphe').classList.remove('active');
    }
}

// ============================================================
// GRAPHE
// ============================================================
async function construireGraphe() {
    document.getElementById('loading-graphe').classList.add('active');
    
    try {
        const respStats = await fetch('/api/graphe/stats');
        const stats = await respStats.json();
        
        afficherStatsGraphe(stats);
        
        const imgGraphe = document.getElementById('img-graphe');
        imgGraphe.src = '/api/graphe/visualiser?' + new Date().getTime();
        
        await chargerMatriceAdj();
        await chargerListeAdj();
        
        etat.grapheConstruit = true;
        updateStatus();
        
        document.getElementById('resultat-graphe').style.display = 'block';
        
        document.getElementById('btn-welsh').disabled = false;
        document.getElementById('btn-dsatur').disabled = false;
        document.getElementById('btn-comparer').disabled = false;
        
    } catch (error) {
        alert('Erreur: ' + error.message);
    } finally {
        document.getElementById('loading-graphe').classList.remove('active');
    }
}

function afficherStatsGraphe(stats) {
    const container = document.getElementById('stats-graphe');
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.nb_sommets}</div>
            <div class="stat-label">Sommets</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.nb_aretes}</div>
            <div class="stat-label">Aretes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.degre_max}</div>
            <div class="stat-label">Degre Max</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.degre_min}</div>
            <div class="stat-label">Degre Min</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.degre_moyen}</div>
            <div class="stat-label">Degre Moyen</div>
        </div>
    `;
}

async function chargerMatriceAdj() {
    try {
        const response = await fetch('/api/graphe/matrice');
        const data = await response.json();
        
        let html = '<table><thead><tr><th></th>';
        data.codes.forEach(code => html += `<th>${code}</th>`);
        html += '</tr></thead><tbody>';
        
        data.matrice.forEach((row, i) => {
            html += `<tr><th>${data.codes[i]}</th>`;
            row.forEach(val => {
                html += `<td style="text-align:center;${val ? 'background:#ffc107;font-weight:bold;' : ''}">${val}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        
        document.getElementById('matrice-adj').innerHTML = html;
    } catch (error) {
        console.error('Erreur matrice:', error);
    }
}

async function chargerListeAdj() {
    try {
        const response = await fetch('/api/graphe/liste-adjacence');
        const data = await response.json();
        
        let html = '<table><thead><tr><th>Sommet</th><th>Voisins</th></tr></thead><tbody>';
        for (const [code, voisins] of Object.entries(data)) {
            html += `<tr><td><strong>${code}</strong></td><td>${voisins.join(', ')}</td></tr>`;
        }
        html += '</tbody></table>';
        
        document.getElementById('liste-adj').innerHTML = html;
    } catch (error) {
        console.error('Erreur liste adj:', error);
    }
}

// ============================================================
// COLORATION
// ============================================================
async function lancerWelshPowell() {
    await lancerColoration('welsh-powell');
}

async function lancerDSATUR() {
    await lancerColoration('dsatur');
}

async function lancerColoration(algorithme) {
    document.getElementById('loading-coloration').classList.add('active');
    document.getElementById('resultat-coloration').style.display = 'none';
    
    try {
        const respecterFiliere = document.getElementById('check-filiere').checked;
        
        const response = await fetch(`/api/coloration/${algorithme}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ respecter_filiere: respecterFiliere })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Erreur: ' + data.error);
            return;
        }
        
        afficherResultatColoration(data);
        
        etat.colorationFaite = true;
        updateStatus();
        
        document.getElementById('btn-generer-planning').disabled = false;
        
        // Rafraichir l'image du graphe colore
        document.getElementById('img-graphe').src = '/api/graphe/visualiser?' + new Date().getTime();
        
    } catch (error) {
        alert('Erreur: ' + error.message);
    } finally {
        document.getElementById('loading-coloration').classList.remove('active');
    }
}

function afficherResultatColoration(data) {
    document.getElementById('resultat-coloration').style.display = 'block';
    
    const container = document.getElementById('stats-coloration');
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.algorithme}</div>
            <div class="stat-label">Algorithme</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.nb_creneaux}</div>
            <div class="stat-label">Creneaux Utilises</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.temps_execution}s</div>
            <div class="stat-label">Temps d'Execution</div>
        </div>
    `;
    
    // Details des creneaux avec horaires
    let htmlDetails = '<h4>Repartition par Creneau</h4><table><thead><tr><th>Creneau</th><th>Horaire</th><th>UEs</th><th>Nombre</th></tr></thead><tbody>';
    
    const creneaux = {};
    for (const [code, creneau] of Object.entries(data.couleurs)) {
        if (!creneaux[creneau]) creneaux[creneau] = [];
        creneaux[creneau].push(code);
    }
    
    for (const [creneau, ues] of Object.entries(creneaux)) {
        const horaire = creneauToHoraire(parseInt(creneau));
        htmlDetails += `<tr>
            <td><strong>Creneau ${creneau}</strong></td>
            <td>${horaire}</td>
            <td>${ues.join(', ')}</td>
            <td>${ues.length}</td>
        </tr>`;
    }
    htmlDetails += '</tbody></table>';
    
    document.getElementById('details-coloration').innerHTML = htmlDetails;
}

function creneauToHoraire(creneau) {
    const jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi'];
    const heures = ['07h30-09h30', '10h00-12h00', '14h00-16h00', '16h30-18h30'];
    
    if (creneau < 0) return 'Invalide';
    const jourIndex = Math.floor(creneau / heures.length);
    const heureIndex = creneau % heures.length;
    
    if (jourIndex >= jours.length) {
        const semaine = 1 + Math.floor(creneau / (jours.length * heures.length));
        const ji = jourIndex % jours.length;
        return `Sem${semaine} ${jours[ji]} ${heures[heureIndex]}`;
    }
    return `${jours[jourIndex]} ${heures[heureIndex]}`;
}

async function comparerAlgorithmes() {
    document.getElementById('loading-coloration').classList.add('active');
    document.getElementById('resultat-comparaison').style.display = 'none';
    
    try {
        const response = await fetch('/api/coloration/comparer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        document.getElementById('resultat-comparaison').style.display = 'block';
        
        const comp = data.comparaison;
        const wpWinner = comp.gagnant_creneaux === 'Welsh-Powell';
        const dsWinner = comp.gagnant_creneaux === 'DSATUR';
        
        document.getElementById('comparaison-content').innerHTML = `
            <div class="algo-card ${wpWinner ? 'winner' : ''}">
                <h4>Welsh-Powell ${wpWinner ? '&#127942;' : ''}</h4>
                <p><strong>Creneaux:</strong> ${comp.nb_creneaux_wp}</p>
                <p><strong>Temps:</strong> ${comp.temps_wp}s</p>
                <p>${wpWinner ? 'Meilleur en nombre de creneaux!' : ''}</p>
            </div>
            <div class="algo-card ${dsWinner ? 'winner' : ''}">
                <h4>DSATUR ${dsWinner ? '&#127942;' : ''}</h4>
                <p><strong>Creneaux:</strong> ${comp.nb_creneaux_ds}</p>
                <p><strong>Temps:</strong> ${comp.temps_ds}s</p>
                <p>${dsWinner ? 'Meilleur en nombre de creneaux!' : ''}</p>
            </div>
        `;
        
    } catch (error) {
        alert('Erreur: ' + error.message);
    } finally {
        document.getElementById('loading-coloration').classList.remove('active');
    }
}

// ============================================================
// PLANNING
// ============================================================
async function genererPlanning() {
    document.getElementById('loading-planning').classList.add('active');
    document.getElementById('resultat-planning').style.display = 'none';
    
    try {
        const response = await fetch('/api/planning/generer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            etat.planningGenere = true;
            updateStatus();
            
            afficherRapportAudit(data.rapport);
            afficherTableauPlanning(data.planning);
            
            document.getElementById('resultat-planning').style.display = 'block';
        } else {
            alert('Erreur: ' + data.error);
        }
        
    } catch (error) {
        alert('Erreur: ' + error.message);
    } finally {
        document.getElementById('loading-planning').classList.remove('active');
    }
}

function afficherRapportAudit(rapport) {
    const container = document.getElementById('rapport-audit');
    
    let html = '';
    
    // Message global
    if (rapport.contraintes_respectees) {
        html += '<div class="alert alert-success"><strong>&#10004; Toutes les contraintes obligatoires sont respectees!</strong></div>';
    } else {
        html += '<div class="alert alert-danger"><strong>&#10008; Certaines contraintes ne sont pas respectees!</strong></div>';
    }
    
    // Details par contrainte avec badges OK/KO
    if (rapport.details) {
        html += '<h4>Verification detaillee des contraintes</h4>';
        html += '<div style="margin: 15px 0;">';
        
        for (const [key, detail] of Object.entries(rapport.details)) {
            const statusClass = detail.status === 'OK' ? 'audit-ok' : 
                               (detail.status === 'KO' ? 'audit-ko' : 'audit-warning');
            const badgeClass = detail.status === 'OK' ? 'badge-ok' : 
                               (detail.status === 'KO' ? 'badge-ko' : 'badge-warning');
            
            html += `<div class="audit-item ${statusClass}">
                <span class="audit-badge ${badgeClass}">${detail.status}</span>
                <div>
                    <strong>${detail.label}</strong><br>
                    <small style="opacity:0.8">${detail.description}</small>
                    ${detail.count > 0 && detail.status !== 'OK' ? `<br><small style="color:#721c24">Problemes: ${detail.count}</small>` : ''}
                </div>
            </div>`;
        }
        html += '</div>';
    }
    
    // Erreurs et avertissements legacy
    if (rapport.erreurs && rapport.erreurs.length > 0) {
        html += '<h4>Erreurs detaillees (' + rapport.erreurs.length + ')</h4><ul>';
        rapport.erreurs.forEach(err => html += `<li style="color: #721c24;">${err}</li>`);
        html += '</ul>';
    }
    
    if (rapport.avertissements && rapport.avertissements.length > 0) {
        html += '<h4>Avertissements (' + rapport.avertissements.length + ')</h4><ul>';
        rapport.avertissements.forEach(warn => html += `<li style="color: #856404;">${warn}</li>`);
        html += '</ul>';
    }
    
    // Statistiques
    if (rapport.stats) {
        html += '<div class="stats-grid">';
        html += `<div class="stat-card"><div class="stat-value">${rapport.stats.total_ues}</div><div class="stat-label">Total UEs</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${rapport.stats.ues_affectees}</div><div class="stat-label">UEs Affectees</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${rapport.stats.nb_creneaux}</div><div class="stat-label">Creneaux</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${rapport.stats.nb_erreurs || 0}</div><div class="stat-label">Erreurs</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${rapport.stats.nb_avertissements || 0}</div><div class="stat-label">Avertissements</div></div>`;
        html += '</div>';
        
        // Equilibre de charge
        if (rapport.stats.equilibre) {
            html += '<h4>Repartition par creneau</h4><table><thead><tr><th>Creneau</th><th>Horaire</th><th>NB Examens</th></tr></thead><tbody>';
            for (const [creneau, count] of Object.entries(rapport.stats.equilibre)) {
                const horaire = creneauToHoraire(parseInt(creneau));
                html += `<tr><td>Creneau ${creneau}</td><td>${horaire}</td><td>${count}</td></tr>`;
            }
            html += '</tbody></table>';
        }
    }
    
    container.innerHTML = html;
}

function afficherTableauPlanning(planning) {
    const thead = document.querySelector('#table-planning thead');
    const tbody = document.querySelector('#table-planning tbody');
    
    // Regrouper par creneau
    const parCreneau = {};
    planning.forEach(item => {
        if (!parCreneau[item.creneau]) parCreneau[item.creneau] = [];
        parCreneau[item.creneau].push(item);
    });
    
    // En-tete avec horaire
    thead.innerHTML = '<tr><th>Creneau</th><th>Horaire</th><th>Salle</th><th>Code UE</th><th>Nom UE</th><th>Filiere</th><th>Effectif</th><th>Surveillant</th></tr>';
    
    // Corps
    let html = '';
    for (const [creneau, items] of Object.entries(parCreneau)) {
        items.forEach((item, index) => {
            html += `<tr>
                ${index === 0 ? `<td rowspan="${items.length}"><strong>Creneau ${creneau}</strong></td>` : ''}
                ${index === 0 ? `<td rowspan="${items.length}">${item.horaire || creneauToHoraire(parseInt(creneau))}</td>` : ''}
                <td>${item.salle}</td>
                <td>${item.code_ue}</td>
                <td>${item.nom_ue}</td>
                <td>${item.filiere}</td>
                <td>${item.effectif}</td>
                <td>${item.surveillant}</td>
            </tr>`;
        });
    }
    tbody.innerHTML = html;
}

// ============================================================
// INITIALISATION
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/etat')
        .then(r => r.json())
        .then(data => {
            if (data.donnees_chargees) {
                etat.donneesChargees = true;
                document.getElementById('btn-construire-graphe').disabled = false;
                chargerListes();
                chargerInterdictions();
            }
            updateStatus();
        });
});
