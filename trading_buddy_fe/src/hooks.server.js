import { NON_PROXY_API_BASE_URL } from '$lib/config.js';

// DANGER: Only use this in development!
// Mitigates issue with Node yelling at self-signed certificate
// [cause]: Error: self-signed certificate
if (import.meta.env.DEV) {
	process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
}

/** @type {import('@sveltejs/kit').Handle} */
export const handle = async ({ event, resolve }) => {
	event.locals.user = null;

	const sessionId = event.cookies.get('sessionid');
	// get all cookies
	console.log("All cookies:", event.cookies.getAll());
	console.log("Session ID from cookie:", sessionId);

	if (sessionId) {
		try {
			const response = await event.fetch(`${NON_PROXY_API_BASE_URL}/auth/status`, {
				headers: {
					Cookie: `sessionid=${sessionId}`
				}
			});

			console.log("API response status:", response.status);

			if (response.ok) {
				event.locals.user = await response.json();
				console.log("User set in locals:", event.locals.user);
			} else {
				console.log("API returned non-ok status, clearing user.");
				event.locals.user = null;
			}
		} catch (error) {
			console.error('API error in hooks.server.js:', error);
			event.locals.user = null;
		}
	}

	return resolve(event);
};
