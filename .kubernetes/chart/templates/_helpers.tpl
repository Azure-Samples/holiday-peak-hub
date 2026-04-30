{{- define "holiday-peak-service.fullname" -}}
{{- printf "%s-%s" .Release.Name .Values.serviceName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Generate a suffixed resource name that stays within the K8s 63-char limit.
Usage: {{ include "holiday-peak-service.suffixedname" (dict "root" . "suffix" "agc") }}
*/}}
{{- define "holiday-peak-service.suffixedname" -}}
{{- $suffix := printf "-%s" .suffix -}}
{{- $maxBase := sub 63 (len $suffix) | int -}}
{{- $base := printf "%s-%s" .root.Release.Name .root.Values.serviceName | trunc $maxBase | trimSuffix "-" -}}
{{- printf "%s%s" $base $suffix -}}
{{- end -}}
