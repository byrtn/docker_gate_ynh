# Docker Gate — documentation d'administration

## Ce que fait Docker Gate

Docker Gate installe Docker CE sur le serveur YunoHost (si besoin) et permet d'exposer n'importe quel conteneur Docker derrière l'authentification unique (SSO) de YunoHost, en une seule saisie — sans jamais avoir à écrire de conf nginx ou de fichier systemd à la main.

Trois façons de décrire l'app à installer, détectées automatiquement :
- un simple nom d'image Docker (ex: `vaultwarden/server:latest`) — l'image est inspectée pour deviner port et volume par défaut ;
- une commande `docker run ...` complète (collée telle quelle depuis la documentation d'un projet) ;
- un fichier `docker-compose.yml` (collé, importé par fichier, ou récupéré depuis une URL `https://`).

Deux modes d'exposition :
- **Dans un répertoire** (`domaine.tld/chemin`) — cas le plus courant, partage un domaine existant.
- **Sur un sous-domaine dédié** (`sous-domaine.domaine.tld`) — nécessaire pour les interfaces qui ne fonctionnent pas sous un sous-chemin (SPA type Portainer).

Chaque app peut avoir des données persistantes (volume Docker nommé, créé automatiquement si un chemin de données est renseigné) et être publique ou restreinte aux admins.

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
- **État** : chaque app créée est enregistrée dans `data/apps.json` (slug, image, ports, domaine/chemin, volume éventuel). C'est la seule source de vérité de Docker Gate sur ce qu'il gère — un conteneur Docker qui existe mais n'apparaît pas dans ce fichier est traité comme un résidu (voir page Audit).
- **Exposition** : chaque app Docker est exposée via l'app YunoHost officielle "redirect" en mode reverse-proxy vers `127.0.0.1:<port>` — c'est donc SSOwat et nginx (le mécanisme standard YunoHost) qui gèrent l'authentification et le TLS, pas Docker Gate lui-même.
- **Suppression** : se fait en 3 couches vérifiées séparément (permission SSO + conf nginx, conteneur Docker, entrée d'état) — chaque étape est tentée indépendamment ; un échec sur une étape n'empêche jamais les suivantes, et l'entrée est toujours retirée de l'état à la fin (un résidu réel reste détectable via la page Audit plutôt que de bloquer indéfiniment).
- **Audit & nettoyage** : détecte les conteneurs/volumes/images/domaines laissés par un essai interrompu. Les volumes ne sont jamais supprimés en masse (peuvent contenir de vraies données) — un par un, sur confirmation explicite.
- **Sécurité applicative** : jeton CSRF (session signée Flask) sur toutes les actions qui modifient un état réel ; clé de session générée aléatoirement à l'installation (jamais codée en dur dans le code source).

</details>

<details>
<summary><strong>Limitations connues (backlog, pas des bugs)</strong></summary>

- Le mode "chemin" et le mode "sous-domaine dédié" ont chacun un contrôle préventif de collision d'adresse avant la création (parité assurée depuis le 15/07/2026).
- Les images Docker sur un registre privé avec port explicite dans le nom (ex: `registre.exemple.com:5000/image:tag`) ne sont pas reconnues par l'analyseur automatique — à saisir en mode avancé le cas échéant.
- Un seul serveur YunoHost à la fois : `multi_instance = false` dans le manifeste — une seule installation de Docker Gate par serveur (les apps Docker qu'il gère, elles, n'ont pas cette limite).

</details>
