<script>
	import { onMount } from "svelte";

	let { symbol = "BYBIT:BTCUSDT.P" } = $props();
	let chartDiv = $state();
	let isMobile = $state(false);

	onMount(() => {
		chartDiv.innerHTML = "";
		isMobile = window.innerWidth < 768;
		const script = document.createElement("script");
		script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
		script.async = true;
		script.innerHTML = JSON.stringify({
			symbol,
			autosize: true,
			interval: "15",
			timezone: "Europe/Warsaw",
			theme: "dark",
			style: "1",
			locale: "en",
			allow_symbol_change: false,
			save_image: false,
			hide_top_toolbar: isMobile,
			hide_volume: isMobile,
			support_host: "https://www.tradingview.com"
		});

		chartDiv.appendChild(script);
	});
</script>

<!--Needs to be wrapped with fixed width/height container-->
<div class="tradingview-widget-container" bind:this={chartDiv} ></div>