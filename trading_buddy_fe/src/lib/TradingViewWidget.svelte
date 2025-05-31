<script>
	import { onMount } from "svelte";
	export let symbol = "BYBIT:BTCUSDT.P";
	let chartDiv;

	onMount(() => {
		chartDiv.innerHTML = "";

		const script = document.createElement("script");
		script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
		script.async = true;
		script.innerHTML = JSON.stringify({
			autosize: true,
			symbol,
			interval: "60",
			timezone: "Europe/Warsaw",
			theme: "dark",
			style: "1",
			locale: "en",
			allow_symbol_change: false,
			support_host: "https://www.tradingview.com"
		});

		chartDiv.appendChild(script);
	});
</script>

<!--Needs to be wrapped with fixed width/height container-->
<div class="tradingview-widget-container" bind:this={chartDiv} ></div>
