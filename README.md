# Zy Prototype

## New Server

1. before anything please do this first: <https://viertelwissen.de/debian-server-vserver-installieren-absichern/>
2. execute `secure.sh` to copy the necessary files
3. edit `nginx/conf.d/default` and `nginx/nginx.conf` comment this line and the https part

```nginx
upstream dashboard {
        server dashboard:3000;
}
```

4. add subdomain to DNS
5. in docker-compose.yml just start nginx and certbot
6. `docker exec -it certbot /bin/sh`
7. in the container execute: `certbot certonly --webroot --webroot-path /usr/share/nginx/html/ -d XXX.zy.space` optional with `--dry-run`
8. `sudo chown -R bb:bb webroot/`
9. upload ui
10. uncomment everything and restart the containers

## Setup

`brew install portaudio weasyprint`
`pip install -r requirements.txt`

```env

OPENAI_API_KEY=sk-abc...
BB_AUDIO_PATH=./data/audio
BB_PORT=8001
REDIS_HOST=redis-1 #depending on docker vs local
REDIS_PORT=6379
SESSION_SECRET_KEY=<openssl rand -hex 32 >
```

## Start Server

0. `docker compose -f docker-compose.local.yml up -d --force-recreate`
1. `python3 -m src.server.server`
2. `rq worker --with-scheduler`

## Setup Linux

```bash
apt install portaudio19-dev
apt install python3-pyaudio
```

### docker

ensure to set the right permissions for the `./data/logs` folder:
`chown -R 999:999 ./data/logs/redis`

## IMPORTANT ON MAC

`export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` before starting the rq worker

## How to deploy

1. update the version you want to deploy in `docker-version.txt`
2. execute `bash docker_build.sh <version>`
3. update app and worker in the `docker-compose.yml` with the new version
4. update the `.env.production` if new variables are added
5. Update domains in `.env.production`
5.1 **Also update the DIFY api Keys for the specific customer**
6. execute `bash update.sh` or execute `bash update.sh IP-ADDRESS`
7. connect to server `ssh bb@IP-ADDRESS`
8. login in harbor `docker login https://XXX`
9. go to the right directory `cd zy`
10. Update the nginx files
11. `docker network create zy_default`
12. (stop containers `docker compose down`)
13. start containers with new images `docker compose up -d`
14. in the certbot container execute `certbot certonly -d xxx.zy.space --webroot --webroot-path /usr/share/nginx/html`
15. Update nginx files
16. Setup Auth0 redirect URLs
17. copy ui to server from the ui folder: `./deploy.sh ip_address xxx`
18. 🤞 `docker compose up -d`
