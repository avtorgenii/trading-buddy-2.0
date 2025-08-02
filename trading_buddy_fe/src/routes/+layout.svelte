<script>
	import '../app.css';
	import { SvelteToast } from '@zerodevx/svelte-toast';
	import NavMenu from '$lib/components/NavMenu.svelte';
	import { onMount } from 'svelte';
	import { csrfToken } from '$lib/stores.js';

	let { data, children } = $props();

	function getCookie(name) {
		let cookieValue = null;
		if (typeof document !== 'undefined' && document.cookie) {
			const cookies = document.cookie.split(';');
			// console.log(cookies);
			for (let i = 0; i < cookies.length; i++) {
				const cookie = cookies[i].trim();
				if (cookie.substring(0, name.length + 1) === (name + '=')) {
					cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
					break;
				}
			}
		}
		// console.log(cookieValue)
		return cookieValue;
	}

	onMount(() => {
		csrfToken.set(getCookie('csrftoken'));
	});
</script>

<main class="min-h-screen bg-zinc-950 flex justify-center text-gray-100 p-3">
	<div class="w-full md:w-4/5">
		<NavMenu user={data.user} />
		{@render children()}
	</div>
</main>

<SvelteToast />