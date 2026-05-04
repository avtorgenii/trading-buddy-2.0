<script>
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import JournalCard from '$lib/components/JournalCard.svelte';
	import { onMount, untrack } from 'svelte';
	import { csrfToken } from '$lib/stores.js';
	import AddInvestmentModal from '$lib/components/modals/AddInvestmentModal.svelte';

	let addModalOpen = $state(false);
	let investingAccounts = $state([]);


	let mode = $state('trading'); // 'trading' | 'investing'
	let tradesAmount = $state(0);
	let trades = $state([]);
	let isLoading = $state(true);
	let loadedPages = $state(1);
	let pageSize = 10;

	let allLoaded = $derived(trades.length >= tradesAmount);

	let isFiltered = $state(false);
	let filters = $state({
		date_from: '',
		date_to: '',
		trade_setup: [],
		profitable: '',
		side: '',
		tool_name: '',
		timeframe: ''
	});

	let filtersOpen = $state(false);

	const TRADE_SETUPS = [
		{ value: 'ACC_BORDER_BREAKTHROUGH', label: '(Ре)накопление - Пробой верхней границы' },
		{ value: 'ACC_BORDER_RETEST', label: '(Ре)накопление - Ретест верхней границы' },
		{ value: 'ACC_CREEK_BREAKTHROUGH', label: '(Ре)накопление - Пробой крика' },
		{ value: 'ACC_CREEK_RETEST', label: '(Ре)накопление - Ретест крика' },
		{ value: 'ACC_SPRING', label: '(Ре)накопление - Спринг' },
		{ value: 'DISTR_BORDER_RETEST', label: '(Ре)дистрибьюция - Ретест нижней границы' },
		{ value: 'DISTR_ICE_RETEST', label: '(Ре)дистрибьюция - Ретест льда' },
		{ value: 'DISTR_UPTHRUST', label: '(Ре)дистрибьюция - Аптраст' },
		{ value: 'BEAR_WOLFE', label: 'Медвежий Вульф' },
		{ value: 'BULL_WOLFE', label: 'Бычий Вульф' },
		{ value: 'DOWN_WEDGE_BREAKTHROUGH', label: 'Нисходящий клин - пробой верхней границы' },
		{ value: 'DOWN_WEDGE_RETEST', label: 'Нисходящий клин - ретест верхней границы' },
		{ value: 'UP_WEDGE_BREAKTHROUGH', label: 'Восходящий клин - пробой нижней границы' },
		{ value: 'UP_WEDGE_RETEST', label: 'Восходящий клин - ретест нижней границы' },
		{ value: 'DOWN_CHANNEL_REBOUND', label: 'Нисходящий канал - отбой вниз от верхней границы' },
		{ value: 'DOWN_CHANNEL_BREAKTHROUGH', label: 'Нисходящий канал - пробой верхней границы' },
		{ value: 'DOWN_CHANNEL_RETEST', label: 'Нисходящий канал - ретест верхней границы' },
		{ value: 'UP_CHANNEL_REBOUND', label: 'Восходящий канал - пробой нижней границы' },
		{ value: 'UP_CHANNEL_BREAKTHROUGH', label: 'Восходящий канал - ретест нижней границы' },
		{ value: 'UP_CHANNEL_RETEST', label: 'Восходящий канал - отбой вверх от нижней границы' },
		{ value: 'SECANT_RETEST', label: 'Ретест секущей в шорт' },
		{ value: 'DOWN_TRENDLINE_REBOUND', label: 'Отбой вниз от нисходящей трендовой' },
		{ value: 'UP_TRENDLINE_REBOUND', label: 'Отбой вверх от восходящей трендовой' }
	];

	const TIMEFRAMES = ['M15', 'H1', 'H4'];

	async function getJournalTrades(page) {
		const endpoint = mode === 'investing' ? 'investments' : 'trades';
		const url = `${API_BASE_URL}/journal/${endpoint}/?page=${page}&page_size=${pageSize}`;
		try {
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) throw new Error('Failed to fetch journal trades.');
			const apiTrades = await response.json();
			tradesAmount = apiTrades.count;
			return apiTrades.results;
		} catch (error) {
			showErrorToast(error.message);
			return [];
		}
	}

	async function applyFilters() {
		isLoading = true;
		isFiltered = true;

		const endpoint = mode === 'investing' ? 'investments' : 'trades';
		const params = new URLSearchParams();
		if (filters.date_from) params.set('date_from', filters.date_from);
		if (filters.date_to) params.set('date_to', filters.date_to);
		if (filters.profitable !== '') params.set('profitable', filters.profitable);
		if (filters.side) params.set('side', filters.side);
		if (filters.tool_name) params.set('tool_name', filters.tool_name);
		if (filters.timeframe) params.set('timeframe', filters.timeframe);
		filters.trade_setup.forEach(s => params.append('trade_setup', s));

		try {
			const response = await fetch(`${API_BASE_URL}/journal/${endpoint}/filtered/?${params}`, { credentials: 'include' });
			if (!response.ok) throw new Error('Failed to fetch filtered trades.');
			const result = await response.json();
			trades = result;
			tradesAmount = result.length;
		} catch (error) {
			showErrorToast(error.message);
		}

		isLoading = false;
	}


	function switchMode(newMode) {
		if (mode === newMode) return;
		mode = newMode;
		isFiltered = false;
		loadPage(1);
	}

	async function deleteTrade(trade_id) {
		try {
			const url = `${API_BASE_URL}/journal/trades/${trade_id}/`;
			const resp = await fetch(url, {
				method: 'DELETE',
				headers: { 'X-CSRFToken': $csrfToken },
				credentials: 'include'
			});
			if (resp.ok) {
				showSuccessToast('Trade deleted.');
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
		const success = await deleteTrade(tradeId);
		if (success) {
			trades = trades.filter(t => t.id !== tradeId);
		}
	}

	async function loadInvestingAccounts() {
		const resp = await fetch(`${API_BASE_URL}/accounts/`, { credentials: 'include' });
		if (resp.ok) {
			const all = await resp.json();
			investingAccounts = all.filter(a => a.exchange === 'Investing');
		}
	}

	async function loadPage(page) {
		loadedPages = page;
		isLoading = true;
		const newTrades = await getJournalTrades(page);
		if (page === 1) {
			trades = newTrades;
		} else {
			trades = [...trades, ...newTrades];
		}
		isLoading = false;
	}

	onMount(() => {
		loadInvestingAccounts();
		loadPage(1);
	});


	function resetFilters() {
		filters = {
			date_from: '', date_to: '',
			trade_setup: [], profitable: '',
			side: '', tool_name: '', timeframe: ''
		};
		isFiltered = false;
		loadPage(1);
	}

	function handleInvestmentCreated() {
		loadPage(1);
	}

</script>

<!-- Mode Toggle -->
<div class="w-full max-w-7xl mx-auto px-4 pt-4 flex justify-center items-center gap-3">
	<div class="flex bg-zinc-900 border border-zinc-800 rounded-xl p-1 w-fit">
		<button onclick={() => switchMode('trading')}
						class="cursor-pointer px-5 py-2 rounded-lg text-sm font-semibold transition-all {mode === 'trading' ? 'bg-blue-700 text-white' : 'text-zinc-400 hover:text-white'}">
			Trading
		</button>
		<button onclick={() => switchMode('investing')}
						class="cursor-pointer px-5 py-2 rounded-lg text-sm font-semibold transition-all {mode === 'investing' ? 'bg-blue-700 text-white' : 'text-zinc-400 hover:text-white'}">
			Investing
		</button>
	</div>
	{#if mode === 'investing'}
		<button onclick={() => addModalOpen = true}
						class="px-4 py-2 rounded-xl bg-blue-700 hover:bg-blue-600 text-white text-sm font-semibold transition-all cursor-pointer">
			+ Add
		</button>
	{/if}
</div>

<AddInvestmentModal bind:open={addModalOpen} accounts={investingAccounts} on:created={handleInvestmentCreated} />

<!-- Filter Panel -->
<div class="w-full max-w-7xl mx-auto px-4 py-4">
	<div class="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">

		<button
			onclick={() => filtersOpen = !filtersOpen}
			class="cursor-pointer w-full flex items-center justify-between px-5 py-3 text-sm font-semibold text-zinc-300 hover:text-white hover:bg-zinc-800 transition-all"
		>
			<span>Filters {isFiltered ? '· active' : ''}</span>
			<span class="transition-transform duration-200 {filtersOpen ? 'rotate-180' : ''}">▼</span>
		</button>

		{#if filtersOpen}
			<div class="p-5 flex flex-col gap-4 border-t border-zinc-800">
				<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">

					<div class="flex flex-col gap-1">
						<label for="filter-date-from" class="text-xs text-zinc-400">С</label>
						<input id="filter-date-from" type="date" bind:value={filters.date_from}
									 class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-500" />
					</div>

					<div class="flex flex-col gap-1">
						<label for="filter-date-to" class="text-xs text-zinc-400">По</label>
						<input id="filter-date-to" type="date" bind:value={filters.date_to}
									 class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-500" />
					</div>

					<div class="flex flex-col gap-1">
						<label for="filter-side" class="text-xs text-zinc-400">Сторона</label>
						<select id="filter-side" bind:value={filters.side}
										class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-500">
							<option value="">Все</option>
							<option value="LONG">Long</option>
							<option value="SHORT">Short</option>
						</select>
					</div>

					<div class="flex flex-col gap-1">
						<label for="filter-profitable" class="text-xs text-zinc-400">Результат</label>
						<select id="filter-profitable" bind:value={filters.profitable}
										class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-500">
							<option value="">Все</option>
							<option value="true">Прибыльные</option>
							<option value="false">Убыточные</option>
						</select>
					</div>

					<div class="flex flex-col gap-1">
						<label for="filter-timeframe" class="text-xs text-zinc-400">Таймфрейм</label>
						<select id="filter-timeframe" bind:value={filters.timeframe}
										class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-500">
							<option value="">Все</option>
							{#each TIMEFRAMES as tf}
								<option value={tf}>{tf}</option>
							{/each}
						</select>
					</div>

					<div class="flex flex-col gap-1">
						<label for="filter-tool" class="text-xs text-zinc-400">Инструмент</label>
						<input id="filter-tool" type="text" bind:value={filters.tool_name} placeholder="BTC-USDT"
									 class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm placeholder-zinc-500 focus:outline-none focus:border-zinc-500" />
					</div>
				</div>

				<div class="flex flex-col gap-1">
					<label for="filter-setup" class="text-xs text-zinc-400">Сетап (можно несколько, Ctrl+Click)</label>
					<select id="filter-setup" multiple bind:value={filters.trade_setup}
									class="bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm h-32 focus:outline-none focus:border-zinc-500">
						{#each TRADE_SETUPS as setup}
							<option value={setup.value}>{setup.label}</option>
						{/each}
					</select>
				</div>

				<div class="flex gap-3 justify-center">
					<button onclick={applyFilters}
									class="cursor-pointer px-5 py-2 rounded-lg bg-blue-700 hover:bg-blue-600 text-white text-sm font-semibold transition-all">
						Apply
					</button>
					<button onclick={resetFilters}
									class="cursor-pointer px-5 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-semibold transition-all">
						Clear
					</button>
				</div>
			</div>
		{/if}

	</div>
</div>

<!-- Trades grid -->
<div class="page-wrapper flex flex-col items-center px-4 py-8">
	<div class="grid w-full max-w-7xl grid-cols-1 md:grid-cols-2 gap-6">
		{#each trades as trade}
			<JournalCard {trade} isInvesting={mode === 'investing'} on:deleted={() => handleDelete(trade.id)} />
		{:else}
			<p class="text-zinc-500 col-span-2 text-center py-12">No trades yet</p>
		{/each}
	</div>
</div>

{#if !isFiltered && trades.length > 0 && !allLoaded}
	<div class="flex justify-center mt-8">
		<button onclick={() => loadPage(loadedPages + 1)}
						class="px-6 py-3 rounded-xl bg-blue-700 text-white font-semibold shadow-lg hover:bg-blue-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 cursor-pointer">
			Load More
		</button>
	</div>
{/if}