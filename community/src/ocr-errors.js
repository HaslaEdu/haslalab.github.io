// OCR diagnostics contain fixed codes and numeric HTTP status only. Neither
// provider bodies nor model/student text belongs in a public error field.
const CODES=new Set([
  'provider_required','provider_unavailable','provider_configuration','provider_locked',
  'vision_provider_auth','vision_provider_credits','vision_provider_rate_limited',
  'vision_model_unavailable','vision_provider_failed','vision_provider_timeout',
  'vision_request_rejected','vision_invalid_response','vision_response_empty',
  'vision_response_truncated','vision_response_blocked','vision_response_schema',
  'vision_images_too_large','vision_bad_image','ocr_failed','ocr_bad_response',
  'ocr_storage_limit','ocr_too_big','ocr_empty','capture_read_failed','photo_unavailable',
  'bad_image','image_too_big','rate_limited','missing_image','job_failed',
]);
export const safeOcrFailureCode=(value,fallback='ocr_failed')=>CODES.has(value)?value:fallback;
export function safeOcrFailureDetails(error,fallback='ocr_failed'){
  const value={error:safeOcrFailureCode(error?.code||error?.error,fallback)};
  if(Number.isInteger(error?.provider_status)&&error.provider_status>=100&&error.provider_status<=599)value.provider_status=error.provider_status;
  if(['deepseek','gemini'].includes(error?.provider))value.provider=error.provider;
  return value;
}
