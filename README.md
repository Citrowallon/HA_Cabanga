# Cabanga pour Home Assistant

Intégration custom (non officielle) pour importer dans Home Assistant les
données de l'app scolaire [Cabanga](https://www.cabanga.be) (société
Scolares) : journal de classe, devoirs à faire, et évaluations.

⚠️ Projet personnel basé sur du reverse engineering de l'app web. Aucun lien
avec Scolares/Cabanga. Peut casser si leur API change.

## Ce que ça fait

Pour chaque enfant configuré, trois capteurs sont créés :

- **Journal de classe {enfant}** — nombre de cours aujourd'hui, avec heure/matière/sujet en attribut
- **Devoirs à faire {enfant}** — nombre de devoirs non cochés comme faits, avec détail en attribut
- **Dernière évaluation {enfant}** — dernière note reçue (`score`), avec matière/titre/date et les 5 dernières évaluations en attribut

## Pourquoi il faut un refresh_token manuel

Le login Cabanga passe par Keycloak avec un captcha **Cloudflare Turnstile**.
Impossible d'automatiser un login username/password. En revanche, une fois
connecté une fois, Keycloak fournit un `refresh_token` valable **7 jours**,
qui se renouvelle automatiquement à chaque utilisation par l'intégration —
tant que Home Assistant tourne et interroge l'API au moins une fois par
semaine, la connexion reste valide indéfiniment sans repasser par le
captcha.

Il faut donc récupérer ce refresh_token **une seule fois manuellement**, à
la configuration initiale (et le refaire uniquement si l'intégration reste
éteinte plus de 7 jours d'affilée).

### Récupérer le refresh_token

1. Ouvre `https://app.cabanga.be/app` dans Chrome/Firefox
2. Ouvre les DevTools (F12) → onglet **Network** → coche "Preserve log"
3. Filtre sur **All** (pas juste Fetch/XHR) et tape `token` dans la barre de recherche
4. Connecte-toi normalement à Cabanga
5. Une requête `token` apparaît (vers `login.scolares.be`) → clique dessus → onglet **Response**
6. Copie la valeur du champ `refresh_token` (la chaîne complète commençant par `eyJ...`)

### Récupérer les IDs élèves et l'ID école

- **ID école** : visible dans n'importe quelle URL d'API, ex.
  `https://api.scolares.be/cabanga/api/schools/CSJCHENEE/...` → ici `CSJCHENEE`
- **ID élève** : clique sur "A faire" ou "Evaluations" pour un enfant donné,
  regarde l'URL de la requête réseau, ex.
  `.../students/75729028/diary?...` → ici `75729028`

## Installation

### Via HACS (dépôt personnalisé)

1. HACS → menu ⋮ → **Dépôts personnalisés**
2. Ajoute l'URL de ce repo GitHub, catégorie **Intégration**
3. Installe "Cabanga" depuis HACS
4. Redémarre Home Assistant
5. Paramètres → Appareils et services → Ajouter une intégration → cherche "Cabanga"
6. Renseigne :
   - **Refresh token** : la valeur récupérée ci-dessus
   - **Identifiant école** : ex. `CSJCHENEE`
   - **Élèves** : format `id:Nom, id:Nom` — ex. `75729028:Haley, 12345678:Aaron`

### Installation manuelle

Copie le dossier `custom_components/cabanga` dans le dossier
`custom_components` de ta config Home Assistant, redémarre, puis suis les
étapes 5-6 ci-dessus.

## Limitations connues (v0.1)

- Pas encore de capteur pour les **absences** (à venir)
- Le mapping id→nom des élèves doit être renseigné manuellement (pas
  d'auto-découverte via l'endpoint `profiles`, exploré plus tard)
- Si le refresh_token expire (HA éteint >7 jours), il faut reconfigurer
  l'intégration avec un nouveau token capturé manuellement — pas de
  notification automatique de ce cas en v0.1

## Structure technique

- `api.py` — client HTTP (Keycloak token refresh + endpoints Cabanga)
- `coordinator.py` — polling centralisé (toutes les 3h par défaut), persiste
  le refresh_token à jour dans le config entry après chaque rotation
- `config_flow.py` — formulaire de configuration + validation du token
- `sensor.py` — les 3 entités par enfant
