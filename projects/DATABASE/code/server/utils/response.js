/**
 * Helpers to send a consistent response shape to the frontend.
 * - sendList: list + pagination (data, total, page, limit, totalPages)
 * - sendOne / sendData / sendCreated: single item
 * - sendOk: simple result (e.g. after delete)
 * - sendError: error message + code (NOT_FOUND, BAD_REQUEST, ...)
 */
function success(res, data, status = 200, extra = {}) {
  res.status(status).json({
    success: true,
    data,
    error: null,
    ...extra,
  });
}

function fail(res, message, status = 500, code = "INTERNAL_ERROR", details = null) {
  const error = { code, message: message || "Internal server error" };
  if (details != null) error.details = details;
  res.status(status).json({
    success: false,
    data: null,
    error,
  });
}

export function sendList(res, payload, status = 200) {
  const { data, total, page, limit, totalPages } = payload;
  success(res, data, status, { meta: { total, page, limit, totalPages } });
}

export function sendData(res, data, status = 200, message = null) {
  success(res, data, status, message ? { message } : {});
}

export function sendOne(res, data, status = 200) {
  success(res, data, status);
}

export function sendCreated(res, data, status = 201) {
  success(res, data, status);
}

export function sendOk(res, payload = { ok: true }, status = 200) {
  success(res, payload, status);
}

export function sendError(res, message, status = 500, code = null, details = null) {
  if (!code) {
    if (status === 404) code = "NOT_FOUND";
    else if (status === 400) code = "BAD_REQUEST";
    else if (status === 422) code = "VALIDATION_ERROR";
    else code = "INTERNAL_ERROR";
  }
  fail(res, message, status, code, details);
}
