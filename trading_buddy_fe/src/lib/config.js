// Full path with port because used to fetch data on server
export const NON_PROXY_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
// Used by all browser fetches, automatically resolves by browser to backend
export const API_BASE_URL = import.meta.env.PROD.VITE_API_SUFFIX || '/api/v1';
// Used by SSO auth because is is not behind api/v1
export const API_BE_BASE_URL = import.meta.env.VITE_API_BE_BASE_URL || 'http://localhost:8000';
