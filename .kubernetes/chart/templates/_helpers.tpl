{{- define "holiday-peak-service.fullname" -}}
{{- printf "%s-%s" .Release.Name .Values.serviceName | trunc 63 | trimSuffix "-" -}}
{{- end -}}
