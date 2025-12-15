{{- define "devplatform.name" -}}
devplatform
{{- end -}}

{{- define "devplatform.fullname" -}}
{{ include "devplatform.name" . }}-{{ .Release.Name }}
{{- end -}}

