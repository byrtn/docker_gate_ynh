<!--
N.B. (audit chantier 6, 17/07/2026) : sur une app YunoHost officielle, ce
fichier est normalement AUTO-GÉNÉRÉ par https://github.com/YunoHost/apps/tree/main/tools/readme_generator
à partir de manifest.toml + doc/DESCRIPTION*.md + doc/screenshots/, et ne
doit JAMAIS être édité à la main une fois généré. Celui-ci est un brouillon
manuel provisoire (le dépôt n'est pas encore public/soumis au catalogue) —
à remplacer par la vraie sortie de cet outil avant toute soumission
officielle, une fois doc/screenshots/ rempli de vraies captures.
-->

# Docker Gate pour YunoHost

[![Niveau d'intégration](https://dash.yunohost.org/integration/docker_gate.svg)](https://dash.yunohost.org/appci/app/docker_gate)
[![Installer Docker Gate avec YunoHost](https://install-app.yunohost.org/install-with-yunohost.svg)](https://install-app.yunohost.org/?app=docker_gate)

*[Read this README in English.](./README.md)*

## Vue d'ensemble

Docker Gate installe Docker CE sur le serveur YunoHost (si besoin) et permet d'exposer n'importe quel conteneur Docker derrière l'authentification unique (SSO) de YunoHost, en une seule saisie — sans jamais avoir à écrire de conf nginx ou de fichier systemd à la main.

Trois façons de décrire l'app à installer, détectées automatiquement :
- un simple nom d'image Docker (ex: `vaultwarden/server:latest`) ;
- une commande `docker run ...` complète (collée telle quelle depuis la documentation d'un projet) ;
- un fichier `docker-compose.yml` (collé, importé par fichier, ou récupéré depuis une URL `https://`).

Deux modes d'exposition (dans un répertoire, ou sur un sous-domaine dédié), volumes de données persistantes, et accès réglé sur l'un des 3 groupes natifs YunoHost (administrateurs uniquement, tous les comptes YunoHost, ou public).

**Fourni dans la version : 0.1~ynh1**

## Documentation et ressources

* Site officiel de l'app : *pas encore publié — prévu avant soumission au catalogue*
* Documentation admin (anglais) : [doc/ADMIN.md](./doc/ADMIN.md)
* Documentation admin (français) : [doc/ADMIN_fr.md](./doc/ADMIN_fr.md)
* Dépôt du code : [github.com/byrtn/docker_gate_ynh](https://github.com/byrtn/docker_gate_ynh)
* Documentation YunoHost pour cette app : *pas encore soumise au catalogue officiel*
* Signaler un bug : [github.com/byrtn/docker_gate_ynh/issues](https://github.com/byrtn/docker_gate_ynh/issues)

## Informations pour les développeurs

Merci d'envoyer vos pull requests vers la [branche main](https://github.com/byrtn/docker_gate_ynh/tree/main).

Pour tester le paquet avant qu'il ne soit fusionné :

```bash
sudo yunohost app install https://github.com/byrtn/docker_gate_ynh/tree/main --debug
```

Ou, tant que le code vit dans le monorepo `byrtn-homelab` (pas encore migré vers son propre dépôt dédié — voir la question ouverte suivie dans `docs/TODO-PROCHAINE-SESSION.md`) :

```bash
sudo yunohost app install /chemin/vers/docs/02-wappos/docker_gate_ynh --debug
```

Pour toute autre information de développement, voir la [documentation officielle de packaging](https://yunohost.org/packaging_apps).
