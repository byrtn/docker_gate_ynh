# Docker Gate — documentation d'administration

## Ce que fait Docker Gate

Docker Gate installe Docker CE sur le serveur YunoHost (si besoin) et permet d'exposer n'importe quel conteneur Docker derrière l'authentification unique (SSO) de YunoHost, en une seule saisie — sans jamais avoir à écrire de conf nginx ou de fichier systemd à la main.

Trois façons de décrire l'app à installer, détectées automatiquement :
- un simple nom d'image Docker (ex: `vaultwarden/server:latest`) — l'image est inspectée pour deviner port et volume par défaut ;
- une commande `docker run ...` complète (collée telle quelle depuis la documentation d'un projet) ;
- un fichier `docker-compose.yml` (collé, importé par fichier, ou récupéré depuis une URL `https://`).

> 💡 **Pour l'installation la plus simple, préfère l'option URL** (le lien brut vers le `docker-compose.yml` du projet, ex: sur GitHub) plutôt que de coller le texte. Quand il est récupéré par URL, Docker Gate cherche aussi le fichier d'exemple d'environnement du projet juste à côté (`.env.example`, `example.env`...) et pré-remplit automatiquement les variables requises à partir de lui — plus besoin d'aller les chercher dans la doc de l'app pour les taper à la main. Ce n'est pas une liste d'apps maintenue par Docker Gate : il ne fait que lire ce que le projet lui-même publie déjà à côté de son compose.

Si le compose déclare **plusieurs services** (ex: une app + sa propre base de données + un cache — courant pour des apps comme Immich, Paperless-ngx...), Docker Gate laisse choisir lequel est exposé via YunoHost/SSO ; les autres démarrent à ses côtés comme dépendances internes sur un réseau Docker dédié, jamais accessibles publiquement, jamais avec un port publié. Les mots de passe trouvés sur ces services internes sont générés automatiquement (valeurs aléatoires robustes, propagées de façon cohérente partout où la même valeur est référencée) plutôt que laissés à taper et à synchroniser à la main.

Deux modes d'exposition :
- **Dans un répertoire** (`domaine.tld/chemin`) — cas le plus courant, partage un domaine existant.
- **Sur un sous-domaine dédié** (`sous-domaine.domaine.tld`) — nécessaire pour les interfaces qui ne fonctionnent pas sous un sous-chemin (SPA type Portainer).

Chaque app peut avoir des données persistantes (volume Docker nommé, créé automatiquement si un chemin de données est renseigné) et son accès réglé sur l'un des 3 groupes natifs YunoHost : administrateurs uniquement, tous les comptes YunoHost, ou public.

## ⚠️ Important — que se passe-t-il si tu désinstalles/réinstalles Docker Gate alors que des apps existent encore ?

**Les apps Docker que tu as créées via Docker Gate NE SONT PAS supprimées** si tu désinstalles Docker Gate lui-même (que ce soit volontairement ou lors d'une réinstallation à froid) — leur conteneur Docker, leur exposition YunoHost (app "redirect", conf nginx, permission SSO) restent parfaitement intacts et fonctionnels, complètement indépendants de Docker Gate.

**Mais Docker Gate, lui, perd la mémoire de ces apps.** Sa page d'accueil affichera "Aucune app installée" même si des conteneurs qu'il a créés tournent toujours en arrière-plan — un vrai résidu **du point de vue de Docker Gate uniquement**, pas une panne des apps elles-mêmes.

**Comment les retrouver** : ouvre la page **Audit & nettoyage** de Docker Gate après une réinstallation — les conteneurs Docker nommés `docker-gate-<slug>` qui ne sont plus dans son fichier d'état apparaissent comme "conteneurs orphelins", détectables et supprimables (un par un) depuis cette page.

**Point de vigilance si tu supprimes un conteneur orphelin détecté ainsi** : ça arrête le conteneur, mais l'app YunoHost "redirect" correspondante (sa tuile sur le portail, sa conf nginx) reste en place, pointant alors vers un service arrêté (elle affichera une erreur au clic). Pour un nettoyage complet, retire aussi cette app depuis **Applications** dans le panneau d'administration YunoHost.

**Question posée à la désinstallation (depuis le 17/07/2026)** : si tu désinstalles Docker Gate en ligne de commande (`yunohost app remove docker_gate`) alors que des apps sont encore trackées, une question s'affiche directement dans le terminal, dans la langue courante de l'interface (anglais ou français, d'après `data/default_language.txt` — le même réglage modifiable à tout moment via le sélecteur EN/FR de l'app elle-même) :
> *"Souhaitez-vous également supprimer les applications ET leurs données gérées par Docker Gate ? Réponds explicitement 'oui' ou 'non' :"*

Une réponse **explicite** est exigée — un simple Entrée ou toute autre saisie reboucle sur la question ("Réponse non reconnue") au lieu de choisir silencieusement à ta place. Répondre **oui** supprime réellement chaque app (conteneur Docker, volume de données, exposition YunoHost, domaine dédié éventuel) avant de continuer la désinstallation de Docker Gate — un vrai nettoyage complet en une seule fois. Répondre **non** laisse les apps intactes, exactement comme décrit ci-dessus (à retrouver via `/audit` après une éventuelle réinstallation). Cette question ne s'affiche que si un vrai terminal est utilisé (jamais lors d'une suppression automatisée/API — dans ce cas, comportement par défaut le plus prudent : rien n'est touché).

**Seconde question posée à la désinstallation (depuis le 18/07/2026)** : juste après celle ci-dessus, si Docker CE est installé sur la machine, une seconde question propose de le désinstaller aussi complètement (paquets `docker-ce`/`containerd.io`/etc., `/var/lib/docker`, groupe système `docker`) — symétrique au fait que Docker Gate l'installe automatiquement à la première installation. **Avant de poser la question, tout conteneur encore présent est signalé**, réparti en deux catégories : les apps encore trackées et conservées par Docker Gate (ex : tu as répondu "non" à la première question) et les conteneurs sans rapport avec Docker Gate — purger Docker CE détruit les deux catégories sans distinction, les deux sont donc explicitement signalées (une version antérieure de cet avertissement ne couvrait que la seconde catégorie, laissant croire à tort que c'était sans risque tant qu'aucun conteneur étranger n'existait). Même mécanique que la première question : réponse explicite exigée, jamais bloquant hors terminal réel (Docker CE reste alors installé par défaut, comportement le plus prudent).

**⚠️ Ordre recommandé si tu comptes supprimer Docker Gate, ses apps enfants ET Docker CE en une seule fois** : fais-le en ligne de commande, où les deux questions interactives ci-dessus peuvent réellement être répondues. **Si tu supprimes Docker Gate depuis le panneau d'administration YunoHost (interface web)**, aucune des deux questions ne peut jamais s'afficher (aucun terminal n'est attaché à une action déclenchée depuis le web) — Docker Gate applique alors silencieusement le choix le plus prudent à chaque fois (apps enfants conservées, Docker CE laissé installé), et le journal de l'action ne le précise qu'après coup. Si tu comptes aussi désinstaller Docker CE, **fais-le d'abord depuis la page Audit de Docker Gate lui-même (bouton "Désinstaller Docker CE")**, avant de supprimer Docker Gate — une fois Docker Gate désinstallé, ce bouton (et son avertissement sur les apps qui dépendent de Docker CE) disparaît avec lui, et tu devrais alors purger Docker CE à la main, sans plus aucun avertissement intégré sur ce que ça va casser.

<details>
<summary><strong>Ce que Docker Gate NE fait PAS</strong></summary>

- **Il ne sauvegarde ni ne restaure les conteneurs/volumes/données des apps qu'il gère.** La sauvegarde YunoHost de Docker Gate (`yunohost backup create`) ne couvre que Docker Gate lui-même : ses propres fichiers, sa configuration nginx/systemd, son fichier d'état (`data/apps.json` — la liste des apps qu'il connaît). **Aucune donnée des conteneurs Docker créés via l'interface n'est incluse.** Restaurer une sauvegarde de Docker Gate remet l'outil en place, avec un fichier d'état qui référence des apps dont les conteneurs/volumes réels peuvent avoir disparu entre-temps si le disque a été perdu — pas les services eux-mêmes.

  **C'est un choix assumé, pas un oubli** : la sauvegarde des données de ce que Docker Gate héberge est un sujet à part entière (formats de données hétérogènes selon l'app, volumes potentiellement volumineux, fréquence de sauvegarde différente selon la criticité de chaque app) qui dépasse le périmètre d'un outil d'installation. **C'est la responsabilité de l'administrateur du serveur de prévoir sa propre stratégie de sauvegarde** pour les conteneurs/volumes qu'il crée via cet outil (ex: sauvegarde des volumes Docker via un outil dédié, snapshot du disque, etc.).

  *Note interne BYRTN : un outil de sauvegarde plus large est envisagé séparément (projet "Vaultn") — Docker Gate n'anticipe pas cette brique, il reste volontairement simple et se concentre sur l'installation/l'exposition, pas la protection des données.*

- **Il ne synchronise pas automatiquement un relais/reverse-proxy externe.** En mode "sous-domaine dédié", si le serveur YunoHost est lui-même derrière un relais TLS-passthrough (topologie à 2 serveurs), Docker Gate ne peut pas configurer ce relais (hors de son périmètre — il ne connaît que la machine sur laquelle il est installé). Un avertissement non-bloquant le signale en fin d'installation si le certificat Let's Encrypt n'a pas pu être obtenu.

- **Il ne gère pas de registre de ports centralisé multi-outils.** La plage `9100-9999` lui est propre ; il évite les collisions avec ses propres apps et avec les conteneurs Docker existants, mais ne connaît pas d'éventuels ports réservés par d'autres outils du serveur.

</details>

<details>
<summary><strong>Comment ça marche (architecture)</strong></summary>

- **Backend** : Flask + gunicorn (un seul worker — le suivi de progression vit en mémoire Python, voir `progress.py`), utilisateur système dédié, membre du groupe `docker`.
- **Droits élevés** : un fichier sudoers ciblé (`conf/docker_gate.sudoers`) autorise uniquement les commandes `yunohost app/domain/diagnosis` nécessaires — jamais de sudo générique. Ce fichier est posé à l'installation, la mise à jour, **et la restauration**.
- **Moteur d'exécution (réécrit le 20/07/2026)** : chaque app — un conteneur ou plusieurs — tourne via un vrai appel `docker compose`, piloté depuis un `docker-compose.yml` minimal que Docker Gate génère lui-même sous `data/compose/<slug>/`, construit uniquement à partir des champs déjà analysés (image/port/volume/env), jamais depuis le texte brut collé par l'utilisateur. Les clés à vrai risque sur un serveur partagé (`build`, `privileged`, `cap_add`, `devices`, `network_mode: host`, `secrets`, `extends`) ne sont jamais lues par l'analyseur, donc ne peuvent jamais atteindre le fichier généré non plus. Chaque app multi-conteneurs reçoit son propre réseau Docker dédié ; les conteneurs se joignent par leur nom de service compose d'origine (résolution DNS native de Compose — aucun code maison nécessaire pour ça).
- **État** : chaque app créée est enregistrée dans `data/apps.json` (slug, image, ports, domaine/chemin, volume éventuel, et — pour les apps multi-conteneurs — ses compagnons et son réseau dédié). C'est la seule source de vérité de Docker Gate sur ce qu'il gère — un conteneur/volume/réseau Docker qui existe mais n'apparaît pas dans ce fichier est traité comme un résidu (voir page Audit).
- **Exposition** : chaque app Docker est exposée via l'app YunoHost officielle "redirect" en mode reverse-proxy vers `127.0.0.1:<port>` — c'est donc SSOwat et nginx (le mécanisme standard YunoHost) qui gèrent l'authentification et le TLS, pas Docker Gate lui-même.
- **Suppression** : se fait en 3 couches vérifiées séparément (permission SSO + conf nginx, conteneur(s) Docker via `docker compose down`, entrée d'état) — chaque étape est tentée indépendamment ; un échec sur une étape n'empêche jamais les suivantes, et l'entrée est toujours retirée de l'état à la fin (un résidu réel reste détectable via la page Audit plutôt que de bloquer indéfiniment). Les apps créées avant la réécriture du 20/07/2026 sont supprimées via l'ancien chemin API Docker direct, conservé comme filet de compatibilité — aucune migration forcée.
- **Audit & nettoyage** : détecte les conteneurs/volumes/images/domaines laissés par un essai interrompu. Les volumes ne sont jamais supprimés en masse (peuvent contenir de vraies données) — un par un, sur confirmation explicite.
- **Suppression de Docker Gate lui-même** (pas d'une app enfant) : voir l'encadré "⚠️ Important" en tête de ce document — un avertissement s'affiche si des apps sont encore trackées, mais il n'empêche pas la suppression de continuer (limitation du cœur YunoHost, pas de ce paquet).
- **Sécurité applicative** : jeton CSRF (session signée Flask) sur toutes les actions qui modifient un état réel ; clé de session générée aléatoirement à l'installation (jamais codée en dur dans le code source).

</details>

<details>
<summary><strong>Limitations connues (backlog, pas des bugs)</strong></summary>

- Le mode "chemin" et le mode "sous-domaine dédié" ont chacun un contrôle préventif de collision d'adresse avant la création (parité assurée depuis le 15/07/2026).
- Les images Docker sur un registre privé avec port explicite dans le nom (ex: `registre.exemple.com:5000/image:tag`) ne sont pas reconnues par l'analyseur automatique — à saisir en mode avancé le cas échéant.
- Un seul serveur YunoHost à la fois : `multi_instance = false` dans le manifeste — une seule installation de Docker Gate par serveur (les apps Docker qu'il gère, elles, n'ont pas cette limite).

</details>
