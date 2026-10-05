FROM mysql:8.0

# MySQL los ejecuta automáticamente la primera vez que el directorio de
# datos está vacío (igual que el bind mount ./db/init que sustituye).
COPY init/ /docker-entrypoint-initdb.d/


COPY entrypoint-mapenv.sh /usr/local/bin/entrypoint-mapenv.sh
RUN chmod +x /usr/local/bin/entrypoint-mapenv.sh
ENTRYPOINT ["/usr/local/bin/entrypoint-mapenv.sh"]
CMD ["mysqld"]
