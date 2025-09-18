<script>
	import { onDestroy, onMount } from 'svelte';
	import PositionCard from '$lib/components/PositionCard.svelte';
	import PendingCard from '$lib/components/PendingCard.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { csrfToken } from '$lib/stores.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { goto } from '$app/navigation';

	let intervalId = $state();
	let positions = $state([]);
	let pendingPositions = $state([]);
	let isCurrentSelected = $state(true);
	let container = $state();

	let isLoading = $state(true);

	let screenWidth = $state(0);
	let isMobile = $derived(screenWidth < 768);

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
	});

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
				positionId: pos.trade_id,
				ticker: pos.tool,
				tradingViewFormat: pos.trading_view_format,
				side: pos.pos_side.toLowerCase(),
				entryPrice: parseFloat(pos.avg_open),
				volume: parseFloat(pos.volume),
				margin: parseFloat(pos.margin),
				leverage: pos.leverage,
				currentPnl: parseFloat(pos.current_pnl),
				value: parseFloat(pos.volume) * parseFloat(pos.avg_open),
				openDate: pos.open_date,
				realizedPnl: pos.realized_pnl,
				currentPnlPercent: pos.current_pnl_risk_reward_ratio,
				stopLoss: null,
				takeProfit: null,
				description: pos.description
			}));

		} catch (error) {
			showErrorToast(error.message);
			console.error(error);
			return [];
		}
	}

	async function handlePendingCancel() {
		pendingPositions = await getPendingPositions();
	}

	async function handleSaveLevels({ toolName, levels }) {
		const url = `${API_BASE_URL}/trading/positions/pending/cancel-levels/${toolName}/`;

		try {
			const response = await fetch(url,
				{
					method: 'PUT',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': $csrfToken
					},
					credentials: 'include',
					body: JSON.stringify({ 'cancel_levels': levels })
				});
			if (!response.ok) {
				throw new Error('Failed to update cancel levels');
			}

			const data = await response.json();
			console.log(data.message);
			showSuccessToast(data.message);
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
				positionId: pos.trade_id,
				ticker: pos.tool,
				side: pos.pos_side.toLowerCase(),
				orderType: 'Limit',

				leverage: parseInt(pos.leverage, 10),
				volume: parseFloat(pos.volume),
				margin: parseFloat(pos.margin),

				entryPrice: parseFloat(pos.entry_price),
				triggerPrice: parseFloat(pos.trigger_price),
				stopPrice: parseFloat(pos.stop_price),
				takeProfits: pos.take_profit_prices,

				cancelLevels: pos.cancel_levels && pos.cancel_levels.length >= 2
					? {
						overLowBuyLevel: parseFloat(pos.cancel_levels[0]),
						takeProfitLevel: parseFloat(pos.cancel_levels[1])
					}
					: null,

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
		class="w-auto md:min-w-4/5 bg-zinc-900 md:px-10 pt-4 pb-12 rounded-2xl text-center flex flex-col min-h-[60vh] max-w-full shadow-xl shadow-white/10">
		<div class="w-full flex justify-center">
			<div class="flex w-100 max-w-md rounded-full border-2 border-zinc-700 bg-zinc-900 mx-5 md:mx-1">
				<button class="flex-1 flex items-center justify-center py-2 text-white cursor-pointer rounded-l-full"
								class:bg-zinc-800={isCurrentSelected}
								onclick={() => isCurrentSelected = true}
								tabindex="0"
								type="button">
					Current
				</button>
				<button class="flex-1 flex items-center justify-center py-2 text-white cursor-pointer rounded-r-full"
								class:bg-zinc-800={!isCurrentSelected}
								onclick={() => isCurrentSelected = false}
								tabindex="0"
								type="button">
					Pending
				</button>
			</div>
		</div>
		{#if isCurrentSelected}
			<div
				bind:this={container}
				class="mt-4 grid gap-6 grid-cols-1 lg:grid-cols-2 flex-1 w-full"
				onwheel={handleWheel}
			>
				{#if isLoading}
					<div class="col-span-full w-full flex items-center justify-center p-10">
						<div class="w-8 h-8 border-4 border-zinc-600 border-t-blue-500 rounded-full animate-spin"></div>
					</div>
				{:else if positions.length > 0}
					{#each positions as position (position.positionId)}
						<div class="col-span-1">
							<PositionCard {position} />
						</div>
					{/each}
				{:else}
					<div class="col-span-full w-full flex justify-center">
						<p class="text-center text-zinc-400 py-4">No current positions.</p>
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex flex-col mt-2 px-2 md:px-4 w-full md:w-full mx-auto flex-1">
				{#if isLoading}
					<div class="w-full flex items-center justify-center p-10">
						<div class="w-8 h-8 border-4 border-zinc-600 border-t-blue-500 rounded-full animate-spin"></div>
					</div>
				{:else if pendingPositions.length === 0}
					<p class="text-center text-zinc-400 py-4">No pending positions.</p>
				{:else}
					<div class="flex-1 max-h-[500px] md:overflow-y-auto scrollbar-win11">
						{#each pendingPositions as order (order.positionId)}
							<PendingCard {order} onCancel={handlePendingCancel} onSaveLevels={handleSaveLevels} />
						{/each}
					</div>
				{/if}
			</div>
		{/if}
		<button
			class="mt-5 bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full text-lg transition-colors duration-200 max-w-xs mx-auto cursor-pointer"
			onclick={() => goto('/trade')}
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