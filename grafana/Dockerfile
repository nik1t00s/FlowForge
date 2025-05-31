FROM grafana/grafana:latest

RUN grafana-cli plugins install vertamedia-clickhouse-datasource

COPY ./provisioning /etc/grafana/provisioning