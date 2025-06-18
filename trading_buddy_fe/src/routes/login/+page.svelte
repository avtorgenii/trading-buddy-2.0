<script>
	import { API_BASE_URL, API_BE_BASE_URL } from '$lib/config.js';
	import { showSuccessToast, showErrorToast } from '$lib/toasts.js';
	import { goto } from '$app/navigation';
	import { csrfToken } from '$lib/stores.js';
	import  { getCookie } from '$lib/utils.js';

	let isSubmitting = false;
	let email = '';
	let password = '';

	async function handleLogin(event) {
		event.preventDefault();
		isSubmitting = true;

		const url = `${API_BASE_URL}/auth/login/`;
		const payload = { email, password };

		try {
			const response = await fetch(url, {
				method: 'POST',
				credentials: 'same-origin',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password })
			});

			if (!response.ok) {
				const errorData = await response.json();
				const errorMessage = errorData[0] || 'An unknown error occurred.';
				throw new Error(errorMessage);
			}

			const data = await response.json();
			email = '';
			password = '';
			csrfToken.set(getCookie('csrftoken'));
			showSuccessToast('Successfully logged in!');
			setTimeout(() => {
				goto('/trade');
			}, 100);
		} catch (error) {
			showErrorToast(error.message);
		} finally {
			isSubmitting = false;
		}
	}

	function handleGoogleLogin(event) {
		event.preventDefault();

		window.location.href = `${API_BE_BASE_URL}/accounts/google/login/`;
	}
</script>


<div class="page-wrapper flex items-center flex-col ">
	<div
		class="form-wrapper bg-zinc-900 px-2 md:px-12 pt-8 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[520px] max-w-xs md:max-w-lg shadow-xl shadow-white/10">
		<h2 class="text-3xl font-bold mb-10">Sign In</h2>
		<div>
			<form class="space-y-5 w-auto md:w-96" on:submit={handleLogin}>
				<input
					bind:value={email}
					class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
					placeholder="Email"
					required
					type="email"
				/>
				<input
					bind:value={password}
					class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
					placeholder="Password"
					required
					type="password"
				/>
				<button
					class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full transition-colors duration-200"
					disabled={isSubmitting}
					type="submit"
				>
					Login
				</button>
			</form>
			<button
				class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full mt-4 transition-colors duration-200"
				disabled={isSubmitting}
				on:click={handleGoogleLogin}
			>
				Continue with Google
			</button>
			<p class="text-zinc-500 text-base italic mt-3 block w-full">
				Do not have an account? <a class="underline" href="register/">Sign up</a>
			</p>
		</div>
	</div>
</div>
