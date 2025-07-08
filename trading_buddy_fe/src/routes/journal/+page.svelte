<script>
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast } from '$lib/toasts.js';
	import JournalCard from '$lib/components/JournalCard.svelte';
	import { untrack } from 'svelte';

	let trades = $state([]);
	let allAccounts = $state(true);

	let isLoading = $state(true);
	let loadedPages = $state(1);

	$effect(async () => {
		loadedPages;
		isLoading = true;
		const newTrades = await getJournalTrades();
		untrack(() => {
			trades = [...trades, ...newTrades];
		});
		isLoading = false;
	});


	async function getJournalTrades() {
		const url = `${API_BASE_URL}/journal/trades/` + (allAccounts ? 'all/' : '') + `?page=${loadedPages}`;
		console.log(`Fetching journal trades from: ${url}`);

		try {
			const response = await fetch(url, { credentials: 'include' });

			if (!response.ok) {
				throw new Error('Failed to fetch journal trades');
			}

			const apiTrades = await response.json();

			return apiTrades.results;

		} catch (error) {
			showErrorToast(error.message);
			console.error(error);
			return [];
		}
	}
</script>

<div class="page-wrapper flex flex-col items-center px-4 py-8">
	<div class="grid w-full max-w-7xl grid-cols-1 md:grid-cols-2 gap-6">
		{#each trades as trade}
			<JournalCard {trade} />
		{/each}
	</div>
</div>

<div class="flex justify-center mt-8">
	<button
		onclick={() => loadedPages++}
		class="px-6 py-3 rounded-xl bg-blue-700 text-white font-semibold shadow-lg hover:bg-blue-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 cursor-pointer"
	>
		Load More
	</button>
</div>
