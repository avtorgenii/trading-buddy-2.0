<script>
	import { onMount } from 'svelte';

	let { symbol = 'BINGX:BTCUSDT.P' } = $props();
	let chartDiv = $state();
	let userTimezone = $state('Europe/Warsaw'); // fallback

	onMount(() => {
		// Get user's current timezone
		try {
			userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
			console.log('Identified timezone for tradingview widget: ' + userTimezone);
		} catch (error) {
			console.warn('Could not detect timezone, using fallback:', error);
			userTimezone = 'Europe/Warsaw';
		}

		chartDiv.innerHTML = '';
		const script = document.createElement('script');
		script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
		script.async = true;
		script.innerHTML = JSON.stringify({
			symbol,
			autosize: true,
			interval: '15',
			timezone: userTimezone,
			theme: 'dark',
			style: '0',
			locale: 'en',
			allow_symbol_change: false,
			save_image: false,
			hide_top_toolbar: false,
			hide_volume: false,
			support_host: 'https://www.tradingview.com'
		});

		chartDiv.appendChild(script);
	});
</script>

<!--Needs to be wrapped with fixed width/height container-->
<div class="tradingview-widget-container w-full h-full" bind:this={chartDiv}></div>