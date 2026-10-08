// Mirrors ALLOWED_UPLOAD_TYPES and UPLOAD_MAX_BYTES in backend/app/common/constants.py;
// the API checks again, this only saves the user a round trip.
export const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'application/pdf', 'text/plain', 'text/csv', 'application/zip'];
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
