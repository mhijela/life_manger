#!/bin/sh
# Used by Docker HEALTHCHECK — keep vars out of Dockerfile to avoid Coolify ARG injection issues
port="${PORT:-8000}"
exec curl -fsS "http://127.0.0.1:${port}/healthz/"
