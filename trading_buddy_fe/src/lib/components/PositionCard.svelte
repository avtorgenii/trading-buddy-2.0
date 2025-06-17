<script>
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';
	import { tweened } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';
	import { createEventDispatcher } from 'svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { showSuccessToast, showErrorToast } from '$lib/toasts.js';
	import { csrfToken } from '$lib/stores.js';


	export let position;
	const dispatch = createEventDispatcher();

	const animatedPnl = tweened(0, { duration: 300, easing: cubicOut });
	$: animatedPnl.set(position.currentPnl);

	console.log(position);

	const animatedPnlPercent = tweened(0, { duration: 300, easing: cubicOut });
	$: animatedPnlPercent.set(position.currentPnlPercent);

	function getStringAfterColon(inputString) {
		const parts = inputString.split(':');
		return parts.length > 1 ? parts.slice(1).join(':') : inputString;
	}

	async function handleClose() {
		try {
			const res = await fetch(
				`${API_BASE_URL}/trading/positions/close-by-market/`,

				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': $csrfToken
					},
					credentials: 'include',
					body: JSON.stringify({ tool: position.ticker })
				}
			);
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || 'Failed to close position.');
			}
			showSuccessToast('Position closed.');
			dispatch('close', { positionId: position.positionId });
		} catch (err) {
			showErrorToast(err.message);
		}
	}
</script>

<div class="flex-none w-full md:w-1/2 md:px-2 bg-zinc-800 rounded-2xl p-0.5 md:bg-transparent md:rounded-none md:p-0">
	<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 h-full flex flex-col">
		<!-- Chart -->
		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-1">
			<div class="w-full h-64 md:h-90 lg:h-96 xl:h-106">
				<TradingViewWidget class="w-full h-full" symbol={position.tradingViewFormat} />
			</div>
		</div>

		<!-- Data -->
		<div class="p-4 flex-grow flex flex-row">
			<div class="w-1/5 text-start">
				<p
					class="uppercase border-l-4 px-2.5 mb-1"
					class:border-l-green-600={position.side === 'long'}
					class:border-l-red-600={position.side === 'short'}>
					{position.side}
				</p>
				<p class="text-sm text-zinc-400">Leverage: 50.0x</p>
			</div>

			<div class="w-3/5 flex flex-col justify-between">
				<div class="text-center">
					<p class="font-medium">{getStringAfterColon(position.ticker)}</p>
					<p class="text-sm text-zinc-400">
						Open Date: {position.openDate.toLocaleDateString()}
					</p>
				</div>
				<div class="mt-3 text-center">
					<p class="text-sm flex flex-col space-y-1 md:inline">
						<span>Value: {position.value.toFixed(2)}$</span>
						<span class="mx-1 text-zinc-500 hidden md:inline">|</span>
						<span>Margin: {Math.abs(position.margin.toFixed(2))}$</span>
					</p>
					<p
						class="text-lg font-semibold"
						class:!text-green-600={position.currentPnl >= 0}
						class:!text-red-500={position.currentPnl < 0}>
						P&L: {position.currentPnl.toFixed(4)}$
					</p>
					<p
						class="text-sm"
						class:!text-green-600={position.realizedPnl >= 0}
						class:!text-red-500={position.realizedPnl < 0}>
						Realized P&L: {position.realizedPnl}$
					</p>
				</div>
			</div>

			<div class="w-1/5 flex flex-col items-end">
				<button
					class="py-1 px-3 cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600"
					on:click={handleClose}
					type="button">
					Close
				</button>
				<div class="mt-5"></div>
			</div>
		</div>
	</div>
</div>
