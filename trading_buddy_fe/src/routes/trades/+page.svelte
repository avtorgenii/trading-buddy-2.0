<script>
	import NavMenu from '$lib/components/NavMenu.svelte';
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';

	let isCurrentSelected = true;
	let container;

	function getCurrentPositions() {
		const generateRandomPnl = () => {
			return parseFloat((Math.random() * 1000 - 700).toFixed(2));
		};

		return [
			{
				positionId: '12345',
				openDate: new Date('2024-05-01T10:00:00Z'),
				currentPnl: generateRandomPnl(),
				currentPnlPercent: '50%',
				ticker: 'BYBIT:BTCUSDT',
				entryPrice: 170.25,
				quantity: 10,
				side: 'long',
				stopLoss: 165.00,
				takeProfit: 180.00

			},
			{
				positionId: '67890',
				openDate: new Date('2024-05-10T14:30:00Z'),
				currentPnl: generateRandomPnl(),
				ticker: 'BYBIT:ETHUSDT',
				entryPrice: 180.50,
				quantity: 5,
				side: 'short',
				stopLoss: 185.00,
				takeProfit: 170.00
			},
			{
				positionId: '11223',
				openDate: new Date('2024-04-20T09:15:00Z'),
				currentPnl: generateRandomPnl(),
				ticker: 'BYBIT:SOLUSDT',
				entryPrice: 400.00,
				quantity: 7,
				side: 'long',
				stopLoss: 390.00,
				takeProfit: 420.00
			}
		];
	}

	function handleWheel(e) {
		if (container.scrollWidth > container.clientWidth) {
			e.preventDefault();
			container.scrollLeft += e.deltaY;
		}
	}
	function getStringAfterColon(inputString) {
	  const parts = inputString.split(':');
	  if (parts.length > 1) {
	    return parts.slice(1).join(':');
	  }
	  return inputString;
	}
</script>


<NavMenu />
<div class="flex items-center flex-col">
	<div
		class="w-auto md:min-w-4/5 bg-zinc-900 px-2 md:px-10 pt-4 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[520px] max-w-xs md:max-w-lg shadow-xl shadow-white/10">
		<div class="w-full flex justify-center">
			<div class="flex w-100 max-w-md rounded-full border-2 border-zinc-700 bg-zinc-900">
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
				class="mt-4 flex flex-nowrap overflow-x-auto -mx-2"
				on:wheel={handleWheel}
				>
				{#each getCurrentPositions() as position (position.positionId)}

					<div class="flex-none w-1/2 px-2">
						<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 h-full flex flex-col">
							<!-- Chart -->
							<div class="h-full bg-zinc-800 rounded-t-2xl flex items-center justify-center p-1">
								<div class="h-[500px] w-[500px] block">
								<TradingViewWidget symbol={position.ticker}/>
								</div>
							</div>
							<!-- Data -->
							<div class="p-4 flex-grow flex flex-col justify-between">
								<div class="text-center">
									<p class=" font-medium">{getStringAfterColon(position.ticker)}</p>
									<p class="text-sm text-zinc-400">
										Open Date: {position.openDate.toLocaleDateString()}
									</p>
								</div>
								<div class="mt-4 text-center">
									<p
										class="text-lg font-semibold"
										class:!text-red-400={position.currentPnl < 0}
										class:!text-green-400={position.currentPnl >= 0}
									>
										PnL: {position.currentPnl.toFixed(2)}
									</p>
								</div>
							</div>
						</div>
					</div>
				{:else}
					<div class="w-full px-2">
						<p class="text-center text-zinc-400">No current positions.</p>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
