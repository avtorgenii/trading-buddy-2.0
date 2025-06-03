<script>
	import NavMenu   from '$lib/components/NavMenu.svelte';

	let email = '';
	let password = '';

	function handleLogin(event) {
		event.preventDefault();

		alert(`Login: ${email} / ${password}`);
	}
	function handleGoogleLogin(event) {
		event.preventDefault();
		alert("Google registartion")
	}

</script>


<NavMenu />

<div class="page-wrapper flex items-center flex-col ">
	<div class="form-wrapper bg-zinc-900 px-2 md:px-12 pt-8 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[520px] max-w-xs md:max-w-lg shadow-xl shadow-white/10">
		<h2 class="text-3xl font-bold mb-10">Sign In</h2>
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
				<button
					class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full transition-colors duration-200"
					type="submit"
				>
					Login
				</button>
			</form>
			<button class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full mt-4 transition-colors duration-200" on:click={handleGoogleLogin}>Continue with Google</button>
			<p class="text-zinc-500 text-base italic mt-3 block w-full">Do not have an account?  <a class="underline" href="register/"> Sign up</a></p>
		</div>
	</div>
</div>