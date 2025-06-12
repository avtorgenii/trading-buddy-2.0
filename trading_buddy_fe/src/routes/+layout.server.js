import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').LayoutServerLoad} */
export const load = async ({ locals, url }) => {
	const user = locals.user;

	const publicRoutes = ['/login', '/register'];


	if (!user && !publicRoutes.includes(url.pathname)) {
		throw redirect(303, '/login');
	}

	return {
		user: user
	};
};