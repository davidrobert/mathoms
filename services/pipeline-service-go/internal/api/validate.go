package api

import (
	"encoding/json"
	"io"
	"net/http"

	"mathoms.ai/pipeline-service/internal/contracts"
)

const locBody = "body"

var (
	requiredStageFields = []string{"run_id", "workspace_id", "workspace_root"}
	requiredRunFields   = []string{"run_id", "workspace_id", "workspace_root", "stages"}
)

// decodeBody decodifica JSON e valida campos obrigatórios; responde 422
// no shape HTTPValidationError do FastAPI. Retorna false se já respondeu.
func decodeBody(w http.ResponseWriter, r *http.Request, dst any, required []string) bool {
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		writeValidationError(w, validationItem([]string{locBody}, err.Error(), "json_invalid"))
		return false
	}
	var probe map[string]json.RawMessage
	if err := json.Unmarshal(raw, &probe); err != nil {
		writeValidationError(w, validationItem([]string{locBody}, "Input should be a valid dictionary", "model_attributes_type"))
		return false
	}
	var missing []contracts.ValidationError
	for _, field := range required {
		if _, ok := probe[field]; !ok {
			missing = append(missing, validationItem([]string{locBody, field}, "Field required", "missing"))
		}
	}
	if len(missing) > 0 {
		writeValidationError(w, missing...)
		return false
	}
	if err := json.Unmarshal(raw, dst); err != nil {
		writeValidationError(w, validationItem([]string{locBody}, err.Error(), "json_invalid"))
		return false
	}
	return true
}

func validationItem(loc []string, msg, errType string) contracts.ValidationError {
	items := make([]contracts.ValidationError_Loc_Item, 0, len(loc))
	for _, l := range loc {
		var item contracts.ValidationError_Loc_Item
		_ = item.FromValidationErrorLoc0(l)
		items = append(items, item)
	}
	return contracts.ValidationError{Loc: items, Msg: msg, Type: errType}
}

func writeValidationError(w http.ResponseWriter, items ...contracts.ValidationError) {
	writeJSON(w, http.StatusUnprocessableEntity, contracts.HTTPValidationError{Detail: &items})
}
