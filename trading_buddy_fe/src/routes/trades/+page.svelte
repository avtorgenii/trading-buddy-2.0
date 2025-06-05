<script>
	import NavMenu from '$lib/components/NavMenu.svelte';
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';
	import { onMount } from 'svelte';
	import PositionCard from '$lib/components/PositionCard.svelte';


	let positions = [];
	let isCurrentSelected = true;
	let container;

	let screenWidth = 0;
	$: isMobile = screenWidth < 768;

	onMount(() => {

		screenWidth = window.innerWidth;

		window.addEventListener('resize', () => {
			screenWidth = window.innerWidth;
		});
		positions = getCurrentPositions();setInterval(() => {
				positions = getCurrentPositions();
			}, 5000);
		}
	)

	function getCurrentPositions() {
		const generateRandomPnl = () => {
			return parseFloat((Math.random() * 1000 - 700).toFixed(2));
		};

		return [
			{
				positionId: '12345',
				margin: 123.45,
				value: 123.45,
				openDate: new Date('2024-05-01T10:00:00Z'),
				realizedPnl: generateRandomPnl(),
				currentPnl: generateRandomPnl(),
				currentPnlPercent: 78.5,
				ticker: 'BYBIT:BTCUSDT.P',
				entryPrice: 170.25,
				quantity: 10,
				side: 'long',
				stopLoss: 165.00,
				takeProfit: 180.00

			},
			{
				positionId: '67890',
				margin: 456.78,
				value: 456.78,
				openDate: new Date('2024-05-10T14:30:00Z'),
				realizedPnl: generateRandomPnl(),
				currentPnl: generateRandomPnl(),
				currentPnlPercent: 30.2,
				ticker: 'BYBIT:ETHUSDT.P',
				entryPrice: 180.50,
				quantity: 5,
				side: 'short',
				stopLoss: 185.00,
				takeProfit: 170.00
			},
			{
				positionId: '11223',
				margin: 789.01,
				value: 789.01,
				openDate: new Date('2024-04-20T09:15:00Z'),
				realizedPnl: generateRandomPnl(),
				currentPnl: generateRandomPnl(),
				currentPnlPercent: 45.0,
				ticker: 'BYBIT:SOLUSDT.P',
				entryPrice: 400.00,
				quantity: 7,
				side: 'long',
				stopLoss: 390.00,
				takeProfit: 420.00
			}
		];
	}

	function handleWheel(e) {
		if (isMobile) return;
		if (container.scrollWidth > container.clientWidth) {
			e.preventDefault();
			container.scrollLeft += e.deltaY;
		}
	}

</script>


<NavMenu />
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
				{#each positions as position (position.positionId)}
					<PositionCard {position} />

				{:else}
					<div class="w-full px-2">
						<p class="text-center text-zinc-400">No current positions.</p>
					</div>
				{/each}
			</div>
		{/if}
		<button class=" mt-5 bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full text-lg transition-colors duration-200 max-w-xs mx-auto">Open a Trade</button>

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
        background-color: rgba(255,255,255,0.2);
        border-radius: 4px;
        border: 2px solid transparent;
    }

    .scrollbar-win11::-webkit-scrollbar-thumb:hover {
        background-color: rgba(255,255,255,0.4);
    }

    .scrollbar-win11 {
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.2) transparent;
    }

    .scrollbar-win11:active {
        scrollbar-color: rgba(255,255,255,0.4) transparent;
    }

</style>