{{- define "aiops-iforest.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "aiops-iforest.fullname" -}}
{{- printf "%s" (include "aiops-iforest.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end }}
