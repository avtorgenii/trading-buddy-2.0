<script>
	import NavMenu from '$lib/components/NavMenu.svelte';
	import { onMount } from 'svelte';
	import Select from 'svelte-select';
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';

	let items = []; // Do not rename it, select library is dumb

	let selectedTicker = { value: 'BYBIT:BTCUSDT', label: 'BTCUSD' }
	let screenWidth = 0;
	$: isMobile = screenWidth < 768;



	 function getPossibleTickers() {
		  return [
		    { value: 'BYBIT:BTCUSDT', label: 'BTCUSD' },
		    { value: 'BYBIT:ETHUSDT', label: 'ETHUSD' },
		    { value: 'BYBIT:SOLUSDT', label: 'SOLUSD' },
		    { value: 'BYBIT:ADAUSDT', label: 'ADAUSD' },
		    { value: 'BYBIT:XRPUSDT', label: 'XRPUSD' },
		    { value: 'BYBIT:DOGEUSDT', label: 'DOGEUSD' },
		    { value: 'BYBIT:BNBUSDT', label: 'BNBUSD' },
		  ];
	}
	onMount(() => {
		items = getPossibleTickers()

		selectedTicker = items.at(0);

		screenWidth = window.innerWidth;

		window.addEventListener('resize', () => {
			screenWidth = window.innerWidth;
		});

	})




</script>


<NavMenu />
<div class="flex items-center flex-col">
	<div
		class="w-auto md:min-w-2/3 bg-zinc-900 md:px-10 pt-4 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[60vh] max-w-full md:max-w-lg shadow-xl shadow-white/10">
		<Select --list-background="#111827" {items} placeholder="Select Ticker" bind:value={selectedTicker}
						containerStyles="
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 0.5rem;
        color: #ffffff;
        width: 100%;
        max-width: 20rem;
        margin: 0 auto;
      "
		/>


		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-1">
			<div class="w-full h-64 md:h-90 lg:h-96 xl:h-106">
				{#key selectedTicker} <!--  To reload widget-->
				<TradingViewWidget class="w-full h-full" symbol={selectedTicker.value} />
					{/key}
			</div>
		</div>



		<div class="flex flex-col max-h-1/5 mt-2 px-2 md:px-4 w-full md:w-3/5 mx-auto">
				<div class="flex-none max-h-full md:max-h-[500px] md:overflow-y-auto ">

				</div>

			</div>

		<button
			class=" mt-5 bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full text-lg transition-colors duration-200 max-w-xs mx-auto">
			Open a Trade
		</button>

	</div>
</div>

<style>
    :global(.foo) {
        background: pink !important;
    }
</style>
