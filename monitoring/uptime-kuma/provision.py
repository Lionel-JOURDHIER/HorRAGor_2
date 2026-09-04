""" 
Provisionne automatiquement la configuration d'Uptime Kuma.
Ce script permet de synchroniser la configuration déclarative définie dans les fichiers YAML avec une instance Uptime Kuma.

Fonctionnalités : 
    - connexion à Uptime Kuma avec les identifiants fournis par les variables d'environnement ;
    - création de la notification Discord si elle n'existe pas ;
    - création ou mise à jour des monitors définis dans ``monitors.yml`` ;
    - association des monitors à la notification Discord ;
    - fonctionnement idempotent : le script peut être exécuté plusieurs fois sans créer de doublons.
    
Les paramètres sensibles (identifiants Uptime Kuma et webhook Discord) sont fournis par les variables d'environnement et ne sont pas stockés dans Git.
    
Le script est utilisé :
        - localement avec ``uv run python provision.py`` ;
        - dans Docker Compose via le service ``uptime-kuma-provision``.
    
Variables d'environnement :

        KUMA_URL: URL de l'instance Uptime Kuma.
        KUMA_USERNAME: nom d'utilisateur Uptime Kuma.
        KUMA_PASSWORD: mot de passe Uptime Kuma.
        DISCORD_WEBHOOK_URL: URL du webhook Discord.
        
Configuration : 
        monitors.yml: définition des monitors à surveiller. 
        notifications.yml: définition des notifications. 
        
    Returns: None 
"""

import os

import yaml
from dotenv import load_dotenv
from uptime_kuma_api import UptimeKumaApi
import time


load_dotenv()

KUMA_URL = os.getenv("KUMA_URL")
KUMA_USERNAME = os.getenv("KUMA_USERNAME")
KUMA_PASSWORD = os.getenv("KUMA_PASSWORD")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def main():
    api = UptimeKumaApi(KUMA_URL)

    for attempt in range(10):
        try:
            api = UptimeKumaApi(KUMA_URL)
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            break
        except Exception:
            if attempt == 9:
                raise
            print(f"Waiting for Uptime Kuma... ({attempt + 1}/10)")
            time.sleep(5)

    with open("notifications.yml", encoding="utf-8") as file:
        notification_config = yaml.safe_load(file)

    existing_notifications = {
        notification["name"]: notification
        for notification in api.get_notifications()
    }

    for notification in notification_config["notifications"]:
        name = notification["name"]

        if name in existing_notifications:
            print(f"OK: notification {name}")
        else:
            api.add_notification(
                name=name,
                type=notification["type"],
                webhookURL=DISCORD_WEBHOOK_URL,
                webhookContentType=notification["content_type"],
            )
            print(f"CREATED: notification {name}")

    existing_notifications = {
        notification["name"]: notification
        for notification in api.get_notifications()
    }

    existing_monitors = {
        monitor["name"]: monitor
        for monitor in api.get_monitors()
    }

    with open("monitors.yml", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    for monitor in config["monitors"]:
        name = monitor["name"]

        if name in existing_monitors:
            existing = existing_monitors[name]

            notification_ids = [
                existing_notifications[name]["id"]
                for name in monitor.get("notifications", [])
            ]

            if (
                existing["url"] != monitor["url"]
                or existing["interval"] != monitor["interval"]
                or existing["notificationIDList"] != notification_ids
            ):
                api.edit_monitor(
                    existing["id"],
                    url=monitor["url"],
                    interval=monitor["interval"],
                    notificationIDList=notification_ids
                )
                print(f"UPDATED: {name}")
            else:
                print(f"OK: {name}")

        else:
            api.add_monitor(
                type=monitor["type"],
                name=name,
                url=monitor["url"],
                interval=monitor["interval"],
                notificationIDList=notification_ids,
            )
            print(f"CREATED: {name}")

    api.disconnect()


if __name__ == "__main__":
    main()