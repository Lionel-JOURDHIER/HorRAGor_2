Monitoring
==========

Overview
--------

HorRAGor includes a monitoring stack designed to observe the availability,
performance, requests and logs of the application services.

The monitoring infrastructure is based on:

* **Prometheus** for collecting and storing metrics;
* **Grafana** for dashboards and visualization;
* **Loki** for centralized log storage;
* **Promtail** for collecting Docker container logs;
* **Langfuse** for tracing and LLM observability;
* **Uptime Kuma** for service availability monitoring.

The monitoring services communicate through the external Docker network
``horragor_net``.


Architecture
------------

The monitoring architecture can be summarized as follows::

    HorRAGor API (:8000) --------\
                                   \
                                    -> Prometheus (:9090)
                                   /        |
    Database API (:8000) --------/         |
                                             v
                                         Grafana (:3000)

    Docker containers
          |
          v
       Promtail (:9080)
          |
          v
       Loki (:3100)
          |
          v
       Grafana


Prometheus
----------

Prometheus periodically scrapes the ``/metrics`` endpoint of the HorRAGor
services.

The global scrape interval is 15 seconds::

    global:
      scrape_interval: 15s

Two application targets are configured.

HorRAGor API::

    - job_name: "horragor-api"
      metrics_path: /metrics
      static_configs:
        - targets: ["horragor_api:8000"]

Database API::

    - job_name: "horragor-database-api"
      metrics_path: /metrics
      static_configs:
        - targets: ["database_api:8000"]

The Docker Compose service names are used as hostnames inside the Docker
network.

The ``job`` label distinguishes metrics coming from the two APIs:

* ``job="horragor-api"``
* ``job="horragor-database-api"``


Application Metrics
-------------------

The FastAPI services expose Prometheus-compatible HTTP metrics.

The monitoring system can track:

* total HTTP requests;
* request rate;
* HTTP status codes;
* requests by endpoint;
* request duration when histogram metrics are available.


Request Rate
~~~~~~~~~~~~

HorRAGor API::

    sum(
      rate(
        http_requests_total{
          job="horragor-api"
        }[5m]
      )
    )

Database API::

    sum(
      rate(
        http_requests_total{
          job="horragor-database-api"
        }[5m]
      )
    )

The ``/metrics`` endpoint is called automatically by Prometheus every
15 seconds and should normally be excluded from business request panels.

Example::

    sum by (handler) (
      rate(
        http_requests_total{
          job="horragor-api",
          handler!="/metrics",
          handler!="/health"
        }[5m]
      )
    )


Requests by Endpoint
~~~~~~~~~~~~~~~~~~~~

Requests can be grouped by the HTTP handler.

HorRAGor API::

    sum by (handler) (
      rate(
        http_requests_total{
          job="horragor-api"
        }[5m]
      )
    )

Database API::

    sum by (handler) (
      rate(
        http_requests_total{
          job="horragor-database-api"
        }[5m]
      )
    )


HTTP Errors
~~~~~~~~~~~

The dashboard tracks HTTP 4xx and 5xx responses.

HorRAGor API::

    sum(
      rate(
        http_requests_total{
          job="horragor-api",
          status=~"4xx|5xx"
        }[5m]
      )
    )

Database API::

    sum(
      rate(
        http_requests_total{
          job="horragor-database-api",
          status=~"4xx|5xx"
        }[5m]
      )
    )


Latency
~~~~~~~

The dashboard can calculate the 95th percentile latency when histogram
buckets are available.

Example::

    histogram_quantile(
      0.95,
      sum(
        rate(
          http_request_duration_seconds_bucket{
            job="horragor-api"
          }[5m]
        )
      ) by (le)
    )

For the Database API::

    histogram_quantile(
      0.95,
      sum(
        rate(
          http_request_duration_seconds_bucket{
            job="horragor-database-api"
          }[5m]
        )
      ) by (le)
    )

If ``http_request_duration_seconds_bucket`` is not available, the P95
latency cannot be calculated with this query.

If ``_sum`` and ``_count`` metrics are available, average request duration
can be calculated instead::

    sum(
      rate(
        http_request_duration_seconds_sum{
          job="horragor-api"
        }[5m]
      )
    )
    /
    sum(
      rate(
        http_request_duration_seconds_count{
          job="horragor-api"
        }[5m]
      )
    )

The exact metric names should be verified using the ``/metrics`` endpoint.


Grafana
-------

Grafana is used as the main monitoring dashboard.

The dashboard combines data from:

* Prometheus for metrics;
* Loki for logs.

The dashboard contains panels for both application APIs.


HorRAGor API Panels
~~~~~~~~~~~~~~~~~~~

The HorRAGor API dashboard contains:

* Request Rate;
* Latency;
* Requests by Endpoint;
* HTTP Errors;
* application logs.


Database API Panels
~~~~~~~~~~~~~~~~~~~

The Database API dashboard contains:

* Request Rate;
* Latency;
* Requests by Endpoint;
* HTTP Errors;
* application logs.

The default dashboard time range is the last six hours.


Loki
----

Loki provides centralized storage for application logs.

Grafana uses Loki as a log datasource.

Promtail sends logs to Loki using::

    http://loki:3100/loki/api/v1/push

Loki is available inside the Docker network on port ``3100``.


Promtail
--------

Promtail uses Docker service discovery to find application containers.

Docker discovery is configured with::

    unix:///var/run/docker.sock

Two application containers are monitored.


HorRAGor API
~~~~~~~~~~~~

The container is identified with::

    regex: '/horragor_api'

The following label is assigned::

    service: horragor_api


Database API
~~~~~~~~~~~~

The container is identified with::

    regex: '/horragor_database_api'

The following label is assigned::

    service: horragor_database_api


Log Queries
-----------

HorRAGor API logs can be queried in Grafana using::

    {service="horragor_api"}

Database API logs::

    {service="horragor_database_api"}

Using an exact non-empty label matcher avoids Loki parser errors caused by
selectors such as ``{app=~".*"}``.


Langfuse
--------

Langfuse is used for tracing and observability of LLM-related operations.

The Langfuse stack includes:

* Langfuse Web;
* Langfuse Worker;
* PostgreSQL;
* ClickHouse;
* Redis;
* MinIO.

The Langfuse Web interface is available locally on port ``3000``.

The HorRAGor API must use the credentials generated by the active Langfuse
project.

If the API logs contain::

    Failed to export span batch code: 401, reason: Unauthorized

the Langfuse credentials configured for the API are invalid, outdated or
do not correspond to the current Langfuse project.

After changing the Langfuse credentials, the HorRAGor API container must be
recreated so that the new environment variables are loaded.

Credentials must not be committed to Git.


Uptime Kuma
-----------

Uptime Kuma provides availability monitoring for application services.

It can be used to monitor:

* HorRAGor API health endpoint;
* Database API health endpoint;
* other HTTP services.

The Uptime Kuma interface is available locally on port ``3002``.


Monitoring URLs
---------------

The monitoring interfaces are available locally at:

* Prometheus: ``http://localhost:9092``
* Grafana: ``http://localhost:3001``
* Uptime Kuma: ``http://localhost:3002``
* Loki: ``http://localhost:3100``
* Langfuse: ``http://localhost:3000``


Starting the Monitoring Stack
-----------------------------

From the ``monitoring`` directory::

    docker compose up -d

Check the status of all services::

    docker compose ps

View Prometheus logs::

    docker compose logs -f prometheus

View Grafana logs::

    docker compose logs -f grafana

View Loki logs::

    docker compose logs -f loki

Stop the monitoring stack::

    docker compose down


Troubleshooting
---------------

Prometheus Target is DOWN
~~~~~~~~~~~~~~~~~~~~~~~~~

Check the targets in Prometheus under:

``Status -> Targets``

The expected targets are::

    horragor_api:8000
    database_api:8000

The Database API target must use the Docker Compose service name
``database_api:8000``.


No Data in Grafana
~~~~~~~~~~~~~~~~~~

Verify that Prometheus is receiving metrics.

HorRAGor API::

    up{job="horragor-api"}

Database API::

    up{job="horragor-database-api"}

A value of ``1`` means that Prometheus successfully scraped the target.


No Latency Histogram
~~~~~~~~~~~~~~~~~~~~

If Grafana reports that no histogram was found, verify whether the following
metric exists::

    http_request_duration_seconds_bucket

If it does not exist, the P95 latency query cannot be used.

The available ``_sum`` and ``_count`` metrics should be checked instead.


No Logs in Loki
~~~~~~~~~~~~~~~

Check that Promtail is running::

    docker compose ps promtail

Check Promtail logs::

    docker compose logs promtail

Then test the Loki queries in Grafana::

    {service="horragor_api"}

and::

    {service="horragor_database_api"}


Langfuse 401 Error
~~~~~~~~~~~~~~~~~~

A ``401 Unauthorized`` error when exporting traces means that the API
cannot authenticate with the current Langfuse project.

Check:

* Langfuse public key;
* Langfuse secret key;
* Langfuse host;
* Langfuse project.

Credentials should be stored in environment variables and never committed
to the repository.


Dashboard Versioning
--------------------

The Grafana dashboard can be exported as JSON and stored in the project::

    monitoring/
    └── grafana/
        └── dashboards/
            └── horragor-monitoring.json

Keeping the dashboard JSON in Git makes the monitoring configuration
reproducible and allows the dashboard to be restored after redeploying
Grafana.