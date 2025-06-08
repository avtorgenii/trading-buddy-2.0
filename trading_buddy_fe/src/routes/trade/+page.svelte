<script>
	import NavMenu from '$lib/components/NavMenu.svelte';
	import { onMount } from 'svelte';
	import Select from 'svelte-select';
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';

	let items = [];

	let selectedTicker = { value: 'BYBIT:BTCUSDT', label: 'BTCUSD' };
	let screenWidth = 0;
	$: isMobile = screenWidth < 768;

	let accountBalance = 1000;
	let riskPercent = 1;
	let leverage = 1;
	let entryPrice = null;
	let cancelLevel = null;
	let stopLoss = null;

	let takeProfits = [
		{ price: null, percent: null }
	];
	let moveSLToBEAfterTP = false;

	let positionSize = null;
	let requiredMargin = null;
	let potentialLoss = null;
	let potentialProfit = null;
	let riskRewardRatio = null;

	function getCurrentPrice(tickerLabel) {
		return 105000;
	}

	$: isLong = entryPrice && stopLoss ? entryPrice > stopLoss : null;

	$: {
		const riskAmount = accountBalance * (riskPercent / 100);
		const currentPrice = getCurrentPrice(selectedTicker.label);


	}


	function addTakeProfit() {
		takeProfits = [...takeProfits, { price: null, percent: null }];
	}

	function removeTakeProfit(indexToRemove) {
		takeProfits = takeProfits.filter((_, index) => index !== indexToRemove);
	}

	function getPossibleTickers() {
		return [
			{ value: 'BYBIT:BTCUSDT', label: 'BTCUSD' },
			{ value: 'BYBIT:ETHUSDT', label: 'ETHUSD' },
			{ value: 'BYBIT:SOLUSDT', label: 'SOLUSD' },
			{ value: 'BYBIT:ADAUSDT', label: 'ADAUSD' },
			{ value: 'BYBIT:XRPUSDT', label: 'XRPUSD' },
			{ value: 'BYBIT:DOGEUSDT', label: 'DOGEUSD' },
			{ value: 'BYBIT:BNBUSDT', label: 'BNBUSD' }
		];
	}

	onMount(() => {
		items = getPossibleTickers();
		selectedTicker = items.at(0);
		screenWidth = window.innerWidth;
		window.addEventListener('resize', () => {
			screenWidth = window.innerWidth;
		});
	});

</script>


<NavMenu />
<div class="flex items-center flex-col">
	<div
		class="w-auto md:min-w-2/3 bg-zinc-900 md:px-10 pt-4 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[60vh] max-w-full md:max-w-lg shadow-xl shadow-white/10">
		<Select --item-hover-bg="#52525b" --list-background="#27272a" bind:value={selectedTicker} containerStyles="
        background-color: #27272a;
        border: 1px solid #374151;
        border-radius: 0.5rem;
        color: #ffffff;a
        width: 100%;
        max-width: 20rem;
        margin: 0 auto;
      "
						{items}
						placeholder="Select Ticker"
		/>


		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-1 mt-3">
			<div class="w-full h-64 md:h-90 lg:h-96 xl:h-106 ">
				{#key selectedTicker}
					<TradingViewWidget class="w-full h-full" symbol={selectedTicker.value} />
				{/key}
			</div>
		</div>

		<div class="w-full max-w-md mx-auto mt-6 px-4">

			<div class="flex justify-center space-x-6 bg-zinc-800 p-2 rounded-xl mb-6 text-sm">
				<div>
					<span class="text-zinc-400">Balance: </span>
					<span class="font-mono text-white">${accountBalance.toLocaleString('en-US')}</span>
				</div>
				<div>
					<span class="text-zinc-400">Risk per Trade: </span>
					<span class="font-mono text-white">{riskPercent}%</span>
				</div>
			</div>


			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Leverage:</span>
				<input
					bind:value={leverage}
					class="bg-zinc-800   text-center w-24 rounded-xl px-4 py-2  focus:outline-none focus:ring-2 focus:ring-blue-600"
					max="100"
					min="1"
					step="1"
					type="number"
				/>
				<span class="">x</span>

					<div class="flex-1 flex justify-end">
						<p class="uppercase border-r-4 px-2.5 mb-1 text-lg"
							 class:border-r-green-600={isLong}
							 class:border-r-red-600={!isLong}>
							{isLong ? 'Long' : 'Short'}
						</p>
					</div>
			</div>
			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Entry:</span>
				<input
					bind:value={entryPrice}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Limit Entry Price"
					type="number"
				/>
			</div>

			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Cancel:</span>
				<input
					bind:value={cancelLevel}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Cancel Level"
					type="number"
				/>
			</div>

			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Stop Loss:</span>
				<input
					bind:value={stopLoss}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Stop Loss"
					type="number"
				/>
			</div>

			{#each takeProfits as tp, index (index)}
				<div class="flex items-center gap-2 mb-4 flex-col md:flex-row align">
					<span class="text-zinc-400 w-25 text-center md:text-start text-nowrap ">{index + 1}. TP:</span>
					<div class="flex-1 flex gap-2">
						<input
							type="number"
							bind:value={tp.price}
							placeholder="Price"
							class="bg-zinc-800 flex-1 min-w-0 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm"
						/>
						<input
							type="number"
							bind:value={tp.percent}
							placeholder="%"
							class="bg-zinc-800 w-14 rounded-xl px-2 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm"
						/>

						<span class="text-zinc-400 text-sm my-auto">%</span>

					</div>
					<button
						class="py-1 px-3  cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed "
						on:click={() => removeTakeProfit(index)}
						disabled={takeProfits.length <= 1}
						tabindex="0"
						type="button">
						Remove
					</button>

				</div>
			{/each}
			<button
				class="py-1 px-3  cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600 mb-4 disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={addTakeProfit}
				disabled={takeProfits.length >= 5}
				tabindex="0"
				type="button">
				Add Take Profit
			</button>

			<div class="space-y-2 bg-zinc-800 rounded-xl p-4 mb-4">
				<div class="flex justify-between">
					<span class="text-zinc-400">Pos. size:</span>
					<span class="text-white">{positionSize ? `$${positionSize.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Required margin:</span>
					<span class="text-white">{requiredMargin ? `$${requiredMargin.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Required margin:</span>
					<span class="text-white">{requiredMargin ? `$${requiredMargin.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Potential loss:</span>
					<span class="text-red-500">{potentialLoss ? `$${potentialLoss.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Potential profit:</span>
					<span class="text-green-500">{potentialProfit ? `$${potentialProfit.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Risk reward ratio:</span>
					<span class="text-white">{riskRewardRatio ? `1 : ${riskRewardRatio.toFixed(2)}` : '-'}</span>
				</div>
			</div>

			<button
				class="mt-5 bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full text-lg
            transition-colors duration-200 max-w-xs mx-auto"
			>
				Open {isLong ? 'Long' : "Short"}
			</button>
		</div>
	</div>
</div>

<style>
    input[type="number"]::-webkit-inner-spin-button,
    input[type="number"]::-webkit-outer-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    input[type="number"] {
        -moz-appearance: textfield;
    }
</style>