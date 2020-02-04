# Server for Linux User Group

This readme describes how to setup a server that runs wordpress with backups on a root-access server. It is designed for minimal maintainability costs.

## setup

```sh
# at least you need to have ports 443 and 80 open, 80 is for the letsencrypt authentication challenge
# for a google server:
#   make a new firewall rule at global settings → "VPC network" → "Firewall rules" to allow all (eases development on this server)
docker || apt update && apt install docker.io
sudo systemctl disable --now apache2
git clone https://github.com/adabru/lug-server

less /etc/passwd
# if not existing, add user www-data 33:33

# create www folder for bind mounts; this folder will contain the wordpress installation
sudo mkdir /home/www-data
sudo chown 33:33 /home/www-data
sudo usermod -a -G 33 $(whoami)
# logout + login to have group

# create folder for database
sudo mkdir /home/www-mysql

# create folder for backups
sudo mkdir /home/www-backup
```

automatically:

```sh
docker swarm init
export DOMAIN=YOUR_DOMAIN
export EMAIL=YOUR_DOMAIN_CERTIFICATE_EMAIL
docker stack deploy -c lug-server/stack.yml lug
```

manually:

```sh
# pull all images
docker pull linuxserver/letsencrypt wordpress mysql:5.7 aveltens/wordpress-backup

# For the tls proxy to work a custom docker network is needen, see https://github.com/linuxserver/reverse-proxy-confs#ensure-you-have-a-custom-docker-network
docker network create lug

# start nginx reverse proxy with letsencrypt tls certificate
DOMAIN=mitfr.us.to
EMAIL=
docker create \
  --name=letsencrypt \
  --network lug \
  --cap-add=NET_ADMIN \
  -e PUID=$(id -u www-data) \
  -e PGID=$(id -u www-data) \
  -e TZ=Europe/Berlin \
  -e URL=$DOMAIN \
  -e SUBDOMAINS=www, \
  -e VALIDATION=http \
  -e EMAIL=$EMAIL \
  -e STAGING=true \
  -p 443:443 \
  -p 80:80 \
  -v /home/www-data:/config \
  --restart unless-stopped \
  linuxserver/letsencrypt
docker start letsencrypt

# start wordpress
docker run -d --network lug --name wordpress \
  -v /home/www-data/www:/var/www/html \
  -e WORDPRESS_DB_HOST=wordpress-mysql:3306 \
  -e WORDPRESS_DB_USER=wordpress \
  -e WORDPRESS_DB_PASSWORD=wordpress \
  -e WORDPRESS_DB_NAME=wordpress \
  wordpress
# open https://host/index.php to see files were successfully copied
# at the moment the letsencrypt container runs the webpage,but it must be rerouted to the wordpress container's php installation
# https://github.com/linuxserver/docker-letsencrypt/blob/master/README.md#site-config-and-reverse-proxy
cp lug-server/letsencrypt_nginx.conf /home/www-data/nginx/site-confs/default
# make wordpress aware of https → http proxying ; only needed for fresh wordpress installation
sudo sh -c "cat lug-server/snippet.php >> /home/www-data/www/wp-settings.php"
sudo sh -c "cat snippet.php >> /home/www-data/www/wp-settings.php"
docker restart letsencrypt

# start database
MYSQL_ROOT_PASSWORD=abc123
docker run -d --name wordpress-mysql --network lug \
  -v /home/www-mysql:/var/lib/mysql
  -e MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD \
  -e MYSQL_DATABASE=wordpress \
  -e MYSQL_USER=wordpress \
  -e MYSQL_PASSWORD=wordpress \
  mysql:5.7

# start backup process
docker run -d --name wordpress-backup --network lug \
  --volumes-from=wordpress \
  --link=wordpress-mysql:mysql \
  -v /home/www-backup:/backups \
  aveltens/wordpress-backup
```

## domain change

For changing the domain, point both the old and the new domain to your wordpress site. Temporarily you can also change your /etc/hosts file to apply the new domain. Then go to "Settings", "General" and change the two url fields.

## setup email

Google servers blocks port 25 without a possibility to open it. All other providers I've seen allow it with a authentication process. Personally I'd recommend not using a google server because of that. So if you're on a google server you still can simply put up an email address like you would for your personal email address. Than you can configure it via the "WP Mail SMTP" wordpress-plugin like in your normal email client. After that everything should be working.

## migrate

See <https://hub.docker.com/r/aveltens/wordpress-backup> for how to:

- Manually back up your database and files
- Create WordPress and MySQL containers
- Restore your backups to those containers with the help of wordpress-backup

## migrate from restricted hosting with wordpress plugin "Duplicator"

```sh
# restore
# https://snapcreek.com/duplicator/docs/quick-start/
# https://snapcreek.com/duplicator/docs/faqs-tech/#faq-installer-015-q

# place "installer.php" & "{archive}.zip" files in an empty directory where you wish to install your site
unzip ./*.zip
docker pull wordpress mysql:5.7

# https://hub.docker.com/_/mysql
MYSQL_ROOT_PASSWORD=abc123
docker run -e MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD -e MYSQL_DATABASE=wordpress -e MYSQL_USER=wordpress -e MYSQL_PASSWORD=wordpress_pass \
  --name wordpress-mysql -d mysql:5.7
docker inspect wordpress-mysql | grep IP
# check with
mysql --host 172.17.0.2 --user=root --password=$MYSQL_ROOT_PASSWORD wordpress

# add yourself to group 33
sudo usermod -a -G 33 $(whoami)
# logout + login
sudo chown -R 33:33 .
sudo chmod -R 774 .
docker run -d -p 8080:80 --name wordpress -v "$PWD":/var/www/html wordpress

# add '127.0.0.1  ipv4.localhost.com' to /etc/hosts
# open in browser: localhost:8080/installer.php
# enable "Manual Archive Extraction"
```

using section "Migrate your blog to Docker" from https://hub.docker.com/r/aveltens/wordpress-backup:
  - unzip 20191224_werkelenzde_d58df85306f74ce44926_20191224204610_archive.zip

## login to google server

```sh
# install gcloud (required by google, see https://cloud.google.com/compute/docs/instances/managing-instance-access#add_oslogin_keys)
gcloud auth login
gcloud config set project lug-erkelenz
gcloud compute os-login ssh-keys add \
  --key-file ~/.ssh/id_rsa.pub \
  --ttl 720d
# find out your username with looking at property posixAccounts → username
gcloud compute os-login describe-profile
# connect, e.g.
ssh john_doe_gmail_com@35.1.2.3
# if you want to connect to an already running instance, stop and start may be necessary, see https://stackoverflow.com/a/47335883/6040478
```

## manual backup and restore

A backup is automatically scheduled every day. For a manual backup run

```sh
# if you used the stack.yml you have to use
# docker exec [STACKNAME]_backup.[tabcomplete] backup
docker exec wordpress-backup backup
```

To restore a backup run

```sh
# if you used the stack.yml you have to use
# docker exec [STACKNAME]_backup.[tabcomplete] restore yyyyMMdd
docker exec wordpress-backup restore yyyyMMdd
```

