#!/bin/sh
set -e

if [ -n "$POSTGRES_URL" ]; then
  rest=${POSTGRES_URL#*://}
  userpass=${rest%@*}
  hostdb=${rest#*@}

  if [ "$userpass" = "${userpass#*:}" ]; then
    user=$userpass
    pass=''
  else
    user=${userpass%%:*}
    pass=${userpass#*:}
  fi

  if [ -z "$user" ]; then
    user='postgres'
  fi

  db=${hostdb#*/}
  if [ -z "$db" ]; then
    db='app'
  fi

  export POSTGRES_USER=$user
  if [ -n "$pass" ]; then
    export POSTGRES_PASSWORD=$pass
  fi
  export POSTGRES_DB=$db
fi

exec /usr/local/bin/docker-entrypoint.sh postgres
