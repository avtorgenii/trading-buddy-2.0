<script>
	import PnLCalendar from '$lib/components/PnLCalendar.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { onMount } from 'svelte';

	let totalPnl = $state(0);

	async function fetchTotalPnl() {
		const url = `${API_BASE_URL}/stats/total-pnl/all/`;

		try {
			const response = await fetch(url, {
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`Response error: ${response.status}`);
			}

			const responseData = await response.json();

			totalPnl = responseData?.pnl;

			console.log(responseData);
		} catch (error) {
			console.error('Error Downloading data:', error);
		}

		return { totalPnl };
	}

	onMount(() => {
		fetchTotalPnl();
	});

</script>


<div class="p-0">
	<PnLCalendar />
	<div class="page-wrapper flex items-center flex-col my-10">
		<div class="text-center">
			<h2 class="text-2xl text-white mb-2">Total PnL</h2>
			<p class="text-4xl {totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}">{totalPnl < 0 ? `-$${Math.abs(totalPnl).toFixed(2)}` : `$${totalPnl.toFixed(2)}`}</p>
		</div>
	</div>
</div>