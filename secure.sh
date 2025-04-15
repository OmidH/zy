#!/bin/bash

# Überprüfe, ob eine IP-Adresse als Argument übergeben wurde
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <IP-Adresse>"
    exit 1
fi

# IP-Adresse aus dem Argument speichern
IP=$1

# Pfad zum Zielverzeichnis auf dem Server
TARGET_DIR="~/zy"

# Überprüfen und Erstellen des Zielverzeichnisses auf dem Server
ssh bb@$IP "mkdir -p $TARGET_DIR"

# Kopiere docker-compose.yml zum angegebenen Verzeichnis
scp ./docker-compose.yml bb@$IP:$TARGET_DIR/docker-compose.yml

# Kopiere den nginx-Ordner zum angegebenen Verzeichnis
scp -r ./nginx bb@$IP:$TARGET_DIR/nginx

# Kopiere den crowdsec-Ordner zum angegebenen Verzeichnis
scp -r ./crowdsec bb@$IP:$TARGET_DIR/crowdsec

# Kopiere den start.sh zum angegebenen Verzeichnis
scp -r ./start.sh bb@$IP:$TARGET_DIR/start.sh

# Kopiere den start.sh & supervisord.conf zum angegebenen Verzeichnis
scp -r ./start.sh bb@$IP:$TARGET_DIR/start.sh
scp -r ./supervisord.conf bb@$IP:$TARGET_DIR/supervisord.conf

echo "Operationen abgeschlossen."
