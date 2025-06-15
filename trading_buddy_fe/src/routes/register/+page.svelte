<script>
	import { API_BASE_URL, API_BE_BASE_URL } from '$lib/config.js';
	import { showSuccessToast, showErrorToast } from '$lib/toasts.js';
	import { goto } from '$app/navigation';
	import { csrfToken } from '$lib/stores.js';
	import  { getCookie } from '$lib/utils.js';

	let isSubmitting = false;
	let email = '';
	let password = '';
	let repeatedPassword = '';
	let userID;

	async function handleRegister(event) {
		event.preventDefault();
		if (password !== repeatedPassword) {
			showErrorToast('Passwords are not the same');
			return;
		}
		isSubmitting = true;

		const url = `${API_BASE_URL}/auth/register/`;
		const payload = {
			email: email,
			password: password,
			password2: repeatedPassword
		};

		try {
			const response = await fetch(url, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload),
				credentials: 'include'
			});

			if (!response.ok) {
				const errorData = await response.json();
				const errorKey = Object.keys(errorData)[0];
				const errorMessage = errorData[errorKey][0] || 'An unknown registration error occurred.';
				throw new Error(errorMessage);
			}

			const data = await response.json();
			userID = data.user_id;
			email = '';
			password = '';
			repeatedPassword = '';

			csrfToken.set(getCookie('csrftoken'));

			showSuccessToast("Successfully registered!");

			setTimeout(() => {
				goto('/settings');
			}, 1000);

		} catch (error) {
			showErrorToast(error.message);
		} finally {
			isSubmitting = false;
		}
	}

	function handleGoogleRegistration(event) {
		event.preventDefault();
		window.location.href = `${API_BE_BASE_URL}/accounts/google/login/`;
	}
</script>
<div class="page-wrapper flex items-center flex-col ">
	<div
		class="form-wrapper bg-zinc-900 px-2 md:px-12 pt-8 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[520px] max-w-xs md:max-w-lg shadow-xl shadow-white/10">
		<h2 class="text-3xl font-bold mb-10">Sign Up</h2>
		<div>
			<form class="space-y-5 w-auto md:w-96" on:submit={handleRegister}>

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
				<input
					bind:value={repeatedPassword}
					class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
					placeholder="Repeat password"
					required
					type="password"
				/>
				<button
					class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full transition-colors duration-200"
					type="submit"
					disabled={isSubmitting}
				>
					Create Account
				</button>
			</form>
			<button class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full mt-4 transition-colors duration-200"
							on:click={handleGoogleRegistration}
							disabled={isSubmitting}
			>Continue with Google
			</button>
			<p class="text-zinc-500 text-base italic mt-3 block w-full">Already have an account? <a class="underline"
																																															href="login/"> Sign in</a>
			</p>
		</div>
	</div>
</div>