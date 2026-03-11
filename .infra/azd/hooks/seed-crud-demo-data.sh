#!/usr/bin/env sh
set -eu

NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
ENVIRONMENT_NAME="${AZURE_ENV_NAME:-dev}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-600}"
SEED_ENABLED="${DEMO_SEED_ENABLED:-true}"
FAIL_ON_ERROR="${FAIL_ON_ERROR:-false}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --namespace)
      shift
      NAMESPACE="$1"
      ;;
    --environment)
      shift
      ENVIRONMENT_NAME="$1"
      ;;
    --timeout-seconds)
      shift
      WAIT_TIMEOUT_SECONDS="$1"
      ;;
    --disable)
      SEED_ENABLED="false"
      ;;
    --fail-on-error)
      FAIL_ON_ERROR="true"
      ;;
    --non-blocking)
      FAIL_ON_ERROR="false"
      ;;
    *)
      ;;
  esac
  shift
done

if [ "$SEED_ENABLED" != "true" ]; then
  echo "CRUD demo seed is disabled (DEMO_SEED_ENABLED=false). Skipping."
  exit 0
fi

if [ "$ENVIRONMENT_NAME" = "prod" ] || [ "$ENVIRONMENT_NAME" = "production" ]; then
  echo "CRUD demo seed skipped for environment '$ENVIRONMENT_NAME'."
  exit 0
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required for CRUD demo seeding."
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

DEPLOYMENT_NAME="$(kubectl get deployment -n "$NAMESPACE" -l app=crud-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
if [ -z "$DEPLOYMENT_NAME" ]; then
  echo "Could not resolve crud-service deployment in namespace '$NAMESPACE'."
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

CRUD_IMAGE="$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)"
if [ -z "$CRUD_IMAGE" ]; then
  echo "Could not resolve CRUD image from deployment '$DEPLOYMENT_NAME'."
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

get_env_from_deployment() {
  DEPLOYMENT="$1"
  NAME="$2"
  kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name=='$NAME')].value}" 2>/dev/null || true
}

POSTGRES_HOST="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_HOST")"
POSTGRES_USER="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_USER")"
POSTGRES_PASSWORD="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_PASSWORD")"
POSTGRES_AUTH_MODE="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_AUTH_MODE")"
POSTGRES_ENTRA_SCOPE="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_ENTRA_SCOPE")"
POSTGRES_DATABASE="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_DATABASE")"
POSTGRES_PORT="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_PORT")"
POSTGRES_SSL="$(get_env_from_deployment "$DEPLOYMENT_NAME" "POSTGRES_SSL")"

[ -z "$POSTGRES_AUTH_MODE" ] && POSTGRES_AUTH_MODE="password"
[ -z "$POSTGRES_DATABASE" ] && POSTGRES_DATABASE="holiday_peak_crud"
[ -z "$POSTGRES_PORT" ] && POSTGRES_PORT="5432"
[ -z "$POSTGRES_SSL" ] && POSTGRES_SSL="true"
[ -z "$POSTGRES_ENTRA_SCOPE" ] && POSTGRES_ENTRA_SCOPE="https://ossrdbms-aad.database.windows.net/.default"

if [ "$POSTGRES_AUTH_MODE" = "entra" ]; then
  if [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_USER" ]; then
    echo "Missing PostgreSQL environment values from CRUD deployment (POSTGRES_HOST/POSTGRES_USER)."
    if [ "$FAIL_ON_ERROR" = "true" ]; then
      exit 1
    fi
    exit 0
  fi
elif [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ]; then
  echo "Missing PostgreSQL environment values from CRUD deployment (POSTGRES_HOST/POSTGRES_USER/POSTGRES_PASSWORD)."
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

CRUD_POD="$(kubectl get pod -n "$NAMESPACE" -l app=crud-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
if [ -z "$CRUD_POD" ]; then
  echo "Could not resolve crud-service pod in namespace '$NAMESPACE' for PostgreSQL connectivity check."
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

if ! kubectl exec -n "$NAMESPACE" "$CRUD_POD" -- sh -lc 'python - <<"PY"
import os, socket, sys
host = os.getenv("POSTGRES_HOST")
port = int(os.getenv("POSTGRES_PORT", "5432"))
s = socket.socket()
s.settimeout(5)
try:
    s.connect((host, port))
except Exception:
    sys.exit(1)
finally:
    s.close()
sys.exit(0)
PY' >/dev/null 2>&1; then
  echo "Skipping CRUD demo seed because PostgreSQL is not reachable from pod '$CRUD_POD' (host=$POSTGRES_HOST port=$POSTGRES_PORT)."
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

JOB_NAME="crud-demo-seed-$(date +%Y%m%d%H%M%S)"
JOB_FILE="$(mktemp)"

cat > "$JOB_FILE" <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB_NAME
  namespace: $NAMESPACE
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      tolerations:
        - key: workload
          operator: Equal
          value: crud
          effect: NoSchedule
        - key: workload
          operator: Equal
          value: agents
          effect: NoSchedule
      containers:
        - name: seed
          image: $CRUD_IMAGE
          imagePullPolicy: Always
          command: ["python", "-m", "crud_service.scripts.seed_demo_data"]
          env:
            - name: DEMO_ENVIRONMENT
              value: "$ENVIRONMENT_NAME"
            - name: POSTGRES_AUTH_MODE
              value: "$POSTGRES_AUTH_MODE"
            - name: POSTGRES_ENTRA_SCOPE
              value: "$POSTGRES_ENTRA_SCOPE"
            - name: POSTGRES_HOST
              value: "$POSTGRES_HOST"
            - name: POSTGRES_USER
              value: "$POSTGRES_USER"
            - name: POSTGRES_PASSWORD
              value: "$POSTGRES_PASSWORD"
            - name: POSTGRES_DATABASE
              value: "$POSTGRES_DATABASE"
            - name: POSTGRES_PORT
              value: "$POSTGRES_PORT"
            - name: POSTGRES_SSL
              value: "$POSTGRES_SSL"
EOF

kubectl apply -f "$JOB_FILE" >/dev/null
if ! kubectl wait --for=condition=complete "job/$JOB_NAME" -n "$NAMESPACE" --timeout="${WAIT_TIMEOUT_SECONDS}s" >/dev/null; then
  kubectl get job "$JOB_NAME" -n "$NAMESPACE" -o wide || true
  kubectl logs "job/$JOB_NAME" -n "$NAMESPACE" || true
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

if ! kubectl logs "job/$JOB_NAME" -n "$NAMESPACE"; then
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  exit 0
fi

rm -f "$JOB_FILE"

echo "CRUD demo data seeding completed with job '$JOB_NAME'."