#!/usr/bin/env bash

# This script run under sudo by default so no need to
# put sudo statements here.
export DEBIAN_FRONTEND=noninteractive

apt-get update

# Avoid annoying Grub prompt
# See https://askubuntu.com/questions/146921/how-do-i-apt-get-y-dist-upgrade-without-a-grub-config-prompt
apt-get -y -o DPkg::options::="--force-confdef" -o DPkg::options::="--force-confold" upgrade

apt-get -y install libpq-dev libxml2-dev libxslt-dev
apt-get -y install libffi-dev libssl-dev
apt-get -y install libjpeg-dev
apt-get -y install gettext
apt-get -y install memcached
apt-get -y install python3
apt-get -y install libmysqlclient-dev
apt-get -y install python3-pip

# Postgresql 10
echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
apt-get update
apt-get -y install postgresql-10

echo "local all postgres peer" > /etc/postgresql/10/main/pg_hba.conf
echo "local met met md5" >> /etc/postgresql/10/main/pg_hba.conf
echo "local test_met met md5" >> /etc/postgresql/10/main/pg_hba.conf
echo "local all all peer" >> /etc/postgresql/10/main/pg_hba.conf
echo "host all all 127.0.0.1/32 md5" >> /etc/postgresql/10/main/pg_hba.conf
echo "host all all ::1/128 md5" >> /etc/postgresql/10/main/pg_hba.conf

service postgresql restart

sudo -u postgres bash -c "psql -c \"CREATE USER met WITH SUPERUSER PASSWORD 'met';\""
sudo -u postgres createdb --owner=met --encoding=UTF8 met

su vagrant << EOF
cd /vagrant
EOF

echo "cd /vagrant/" >> /home/vagrant/.profile
echo "export LC_ALL='en_US.UTF-8'" >> /home/vagrant/.profile
echo "export LC_CTYPE='en_US.UTF-8'" >> /home/vagrant/.profile
