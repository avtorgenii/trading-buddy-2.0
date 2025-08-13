<script>
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import JournalCard from '$lib/components/JournalCard.svelte';
	import { untrack } from 'svelte';
	import { csrfToken } from '$lib/stores.js';

	let tradesAmount = $state(0);
	let trades = $state([]);

	let isLoading = $state(true);
	let loadedPages = $state(1);
	let pageSize = 10;

	$effect(async () => {
		loadedPages;
		isLoading = true;
		const newTrades = await getJournalTrades();
		untrack(() => {
			trades = [...trades, ...newTrades];
		});
		isLoading = false;
	});


	$effect(() => {
		tradesAmount; // Only track tradesAmount
		untrack(() => {
			for (let i = 0; i < trades.length; i++) {
				trades[i].tradeNumber = tradesAmount - ((loadedPages - 1) * pageSize) - i;
			}
		});
	});


	async function getJournalTrades() {
		const url = `${API_BASE_URL}/journal/trades/` + `?page=${loadedPages}&page_size=${pageSize}`;
		console.log(`Fetching journal trades from: ${url}`);

		try {
			const response = await fetch(url, { credentials: 'include' });

			if (!response.ok) {
				throw new Error('Failed to fetch journal trades.');
			}

			const apiTrades = await response.json();
			tradesAmount = apiTrades.count;

			for (let i = 0; i < apiTrades.results.length; i++) {
				apiTrades.results[i]['tradeNumber'] = tradesAmount - ((loadedPages - 1) * pageSize) - i;
			}

			return apiTrades.results;

		} catch (error) {
			showErrorToast(error.message);
			console.error(error);
			return [];
		}
	}


	async function deleteTrade(trade_id) {
		try {
			const url = `${API_BASE_URL}/journal/trades/${trade_id}/`;
			const resp = await fetch(url, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include'
			});

			if (resp.ok) {
				showSuccessToast(`Trade deleted.`);
				tradesAmount--;
				return true;
			} else {
				const error = await resp.json();
				showErrorToast(error.error);
				return false;
			}
		} catch (err) {
			showErrorToast(err.message);
			return false;
		}
	}


	async function handleDelete(tradeId) {
		let success = await deleteTrade(tradeId);
		if (success) {
			let tradeIdxToDeleted;
			for (let i = 0; i < trades.length; i++) {
				if (trades[i].id === tradeId) {
					tradeIdxToDeleted = i;
					break;
				}
			}
			trades.splice(tradeIdxToDeleted, 1);
		}
	}

</script>

<div class="page-wrapper flex flex-col items-center px-4 py-8">
	<div class="grid w-full max-w-7xl grid-cols-1 md:grid-cols-2 gap-6">
		{#each trades as trade}
			<JournalCard {trade} on:deleted={() => handleDelete(trade.id)} />
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
