<script>
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';
	import { tweened } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';

	export let position;


	const animatedPnl = tweened(0, {
		duration: 300,
		easing: cubicOut
	});

	$: animatedPnl.set(position.currentPnl);

	const animatedPnlPercent = tweened(0, {
		duration: 300,
		easing: cubicOut
	});

	$: animatedPnlPercent.set(position.currentPnlPercent);


	function getStringAfterColon(inputString) {
		const parts = inputString.split(':');
		if (parts.length > 1) {
			return parts.slice(1).join(':');
		}
		return inputString;
	}
</script>


<div class="flex-none w-full md:w-1/2 md:px-2 bg-zinc-800 rounded-2xl p-0.5 md:bg-transparent md:rounded-none md:p-0">
	<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 h-full flex flex-col">
		<!-- Chart -->
		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-1">
			<div class="w-full h-64 md:h-90 lg:h-96 xl:h-106">
				<TradingViewWidget class="w-full h-full" symbol={position.ticker} />
			</div>
		</div>
		<!-- Data -->
		<div class="p-4 flex-grow flex flex-row ">

			<div class="w-1/5 text-start">
				<p class="uppercase border-l-4 px-2.5 mb-1"
				class:border-l-green-600={position.side === 'long'}
				class:border-l-red-600={position.side === 'short'}
				>{position.side}</p>
				<p class="text-sm text-zinc-400">Leverage: 50.0x</p>
<!--				<p class="text-sm text-zinc-400">Qty: {position.quantity}</p> Dont needed I guess-->
<!--				<p class="text-md text-zinc-400">TP: {position.takeProfit.toFixed(2)}</p>-->
<!--				<p class="text-md text-zinc-400">SL: {position.takeProfit.toFixed(2)}</p>-->
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
						<span>Margin: {position.margin.toFixed(2)}$</span>
					</p>
					<p
						class="text-lg font-semibold"
						class:!text-green-600={position.currentPnl >= 0}
						class:!text-red-500={position.currentPnl < 0}
					>
						P&L: {$animatedPnl.toFixed(2)}$ ({$animatedPnlPercent.toFixed(1)}%)
					</p>

					<p
						class="text-sm "
						class:!text-green-600={position.realizedPnl >= 0}
						class:!text-red-500={position.realizedPnl < 0}
					>
						Realized P&L: {position.realizedPnl}$
					</p>

				</div>
			</div>
			<div class="w-1/5 flex flex-col items-end">
				<button class="py-1 px-3  cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600"
								on:click={() => 1+1 //TODO: IMPLEMENT;
								}
								tabindex="0"
								type="button">
					Close
				</button>
				<div class="mt-5">
					<p class="text-sm text-zinc-400">TP: {position.takeProfit.toFixed(2)}$</p>
					<p class="text-sm text-zinc-400">SL: {position.takeProfit.toFixed(2)}$</p>

				</div>

			</div>
		</div>

	</div>
</div>

