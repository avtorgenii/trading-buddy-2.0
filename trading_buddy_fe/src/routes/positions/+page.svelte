<script>
	import { onDestroy, onMount } from 'svelte';
	import PositionCard from '$lib/components/PositionCard.svelte';
	import PendingCard from '$lib/components/PendingCard.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast } from '$lib/toasts.js';
	import { goto } from '$app/navigation';

	let intervalId;
	let positions = [];
	let pendingPositions = [];
	let isCurrentSelected = true;
	let container;

	let isLoading = true;

	let screenWidth = 0;
	$: isMobile = screenWidth < 768;

	onMount(() => {
		async function loadInitialData() {
			isLoading = true;
			[positions, pendingPositions] = await Promise.all([
				getCurrentPositions(),
				getPendingPositions()
			]);
			isLoading = false;
		}

		loadInitialData();

		screenWidth = window.innerWidth;
		window.addEventListener('resize', () => {
			screenWidth = window.innerWidth;
		});

		intervalId = setInterval(async () => {
			positions = await getCurrentPositions();
		}, 5000);
	}

	)
	onDestroy(() => {
		clearInterval(intervalId);
	});



	async function getCurrentPositions() {
		const url = `${API_BASE_URL}/trading/positions/current/`;
		console.log(`Fetching current positions from: ${url}`);

		try {
			const response = await fetch(url, { credentials: 'include' });

			if (!response.ok) {
				throw new Error('Failed to fetch current positions');
			}

			const apiPositions = await response.json();

			return apiPositions.map(pos => ({
				positionId: pos.tool + pos.pos_side,
				ticker: pos.tool,
				side: pos.pos_side.toLowerCase(),
				entryPrice: parseFloat(pos.avg_open),
				quantity: parseFloat(pos.volume),
				margin: parseFloat(pos.margin),
				leverage: pos.leverage,
				currentPnl: parseFloat(pos.pnl),
				value: parseFloat(pos.volume) * parseFloat(pos.avg_open),
				openDate: new Date(pos.open_date),
				realizedPnl: pos.realized_pnl,
				currentPnlPercent: pos.current_pnl_risk_reward_ratio,
				stopLoss: null,
				takeProfit: null
			}));

		} catch (error) {
			showErrorToast(error.message);
			console.error(error);
			return [];
		}
	}

	async function getPendingPositions() {
		const url = `${API_BASE_URL}/trading/positions/pending/`;

		try {
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) {
				throw new Error('Failed to fetch pending positions');
			}
			const apiPositions = await response.json();

			return apiPositions.map(pos => ({
				positionId: pos.tool + pos.pos_side + pos.entry_price,
				ticker: pos.tool,
				side: pos.pos_side.toLowerCase(),
				leverage: parseInt(pos.leverage, 10),
				quantity: parseFloat(pos.volume),
				margin: parseFloat(pos.margin),
				orderType: pos.trigger_price ? 'Stop' : 'Limit',
				// API nie zwraca `status` i `takeProfit`, ustawiamy domyślne wartości
				takeProfit: null,
				cancelLevel: pos.cancel_levels && pos.cancel_levels.length > 0 ? parseFloat(pos.cancel_levels[0]) : null
			}));

		} catch (error) {
			showErrorToast(error.message);
			console.error(error);
			return [];
		}
	}


	function handleWheel(e) {
		if (isMobile) return;
		if (container && container.scrollWidth > container.clientWidth) {
			e.preventDefault();
			container.scrollLeft += e.deltaY;
		}
	}

</script>


<div class="flex items-center flex-col">
	<div
		class="w-auto md:min-w-4/5 bg-zinc-900 md:px-10 pt-4 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[60vh] max-w-full md:max-w-lg shadow-xl shadow-white/10">
		<div class="w-full flex justify-center">
			<div class="flex w-100 max-w-md rounded-full border-2 border-zinc-700 bg-zinc-900 mx-5 md:mx-1">
				<button class="flex-1 flex items-center justify-center py-2 text-white cursor-pointer rounded-l-full"
								class:bg-zinc-800={isCurrentSelected}
								on:click={() => isCurrentSelected = true}
								tabindex="0"
								type="button">
					Current
				</button>
				<button class="flex-1 flex items-center justify-center py-2 text-white cursor-pointer rounded-r-full"
								class:bg-zinc-800={!isCurrentSelected}
								on:click={() => isCurrentSelected = false}
								tabindex="0"
								type="button">
					Pending
				</button>

			</div>
		</div>
		{#if isCurrentSelected}
			<div
				bind:this={container}
				class="mt-4 flex {isMobile ? 'grid gap-24 grid-col-1' : 'flex-nowrap overflow-x-auto md:mx-2 scrollbar-win11'}"
				on:wheel={handleWheel}
			>
				{#if isLoading}
					<div class="w-full flex items-center justify-center p-10">
						<div class="w-8 h-8 border-4 border-zinc-600 border-t-blue-500 rounded-full animate-spin"></div>
					</div>
				{:else if positions.length > 0}
					{#each positions as position (position.positionId)}
						<PositionCard {position} />
					{/each}
				{:else}
					<div class="w-full px-2">
						<p class="text-center text-zinc-400">No current positions.</p>
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex flex-col mt-2 px-2 md:px-4 w-full md:w-full mx-auto">
				{#if isLoading}
					<div class="w-full flex items-center justify-center p-10">
						<div class="w-8 h-8 border-4 border-zinc-600 border-t-blue-500 rounded-full animate-spin"></div>
					</div>
				{:else if pendingPositions.length === 0}
					<p class="text-center text-zinc-400 py-4">No pending orders.</p>
				{:else}
					<div class="flex-none max-h-full md:max-h-[500px] md:overflow-y-auto scrollbar-win11">
						{#each pendingPositions as order (order.positionId)}
							<PendingCard {order} on:cancel={1+1} />
						{/each}
					</div>
				{/if}
			</div>
		{/if}
		<button
			class=" mt-5 bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full text-lg transition-colors duration-200 max-w-xs mx-auto"
			on:click={() => goto('/trade')}
		>
			Open a Trade
		</button>

	</div>
</div>

<style>

    .scrollbar-win11::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    .scrollbar-win11::-webkit-scrollbar-track {
        background: transparent;
    }

    .scrollbar-win11::-webkit-scrollbar-thumb {
        background-color: rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        border: 2px solid transparent;
    }

    .scrollbar-win11::-webkit-scrollbar-thumb:hover {
        background-color: rgba(255, 255, 255, 0.4);
    }

    .scrollbar-win11 {
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
    }

    .scrollbar-win11:active {
        scrollbar-color: rgba(255, 255, 255, 0.4) transparent;
    }

</style>