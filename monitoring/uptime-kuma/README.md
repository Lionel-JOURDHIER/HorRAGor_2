# Uptime Kuma — Monitoring HorRAGor

## Description

Ce dossier permet de **configurer automatiquement Uptime Kuma** avec les monitors et les notifications Discord du projet HorRAGor.

La configuration est gérée avec Git (`monitors.yml`, `notifications.yml`) et appliquée automatiquement par `provision.py`.

### Monitors

* HorRAGor API
* Database API
* Prometheus
* Grafana
* Langfuse

Les services sont vérifiés toutes les **60 secondes** et les alertes sont envoyées sur Discord.

## Utilisation

### 1. Configurer les variables d'environnement

Créer le fichier `.env` :

```env
KUMA_URL=http://localhost:3002
KUMA_USERNAME=<username>
KUMA_PASSWORD=<password>
DISCORD_WEBHOOK_URL=<discord-webhook>
```

Ne pas ajouter `.env` à Git.

### 2. Lancer Uptime Kuma

Depuis la racine du projet :

```powershell
docker compose -f monitoring/docker-compose.yml up -d uptime-kuma
```

Uptime Kuma est accessible sur :

```text
http://localhost:3002
```

### 3. Appliquer la configuration

Depuis la racine du projet :

```powershell
docker compose -f monitoring/docker-compose.yml up --build uptime-kuma-provision
```

Le script crée ou met à jour automatiquement les monitors et leur notification Discord.

### 4. Vérifier

Un résultat similaire doit apparaître :

```text
OK: notification Discord
OK: HorRAGor API
OK: Database API
OK: Prometheus
OK: Grafana
OK: Langfuse
```

Le conteneur `uptime-kuma-provision` peut ensuite s'arrêter avec `code 0` : c'est normal, car il s'agit d'un service d'initialisation ponctuel.

## Configuration

* `monitors.yml` — liste des services à surveiller.
* `notifications.yml` — configuration des notifications.
* `provision.py` — synchronisation avec Uptime Kuma.
* `.env` — identifiants et secrets locaux.

La configuration est **idempotente** : le script peut être relancé sans créer de doublons.
