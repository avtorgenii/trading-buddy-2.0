<script>
	import PnLCalendar from '$lib/components/PnLCalendar.svelte';


	const myProfitLossData = {
		'2025-06-05': -150.75,
		'2025-06-09': 25.10,
		'2025-06-18': 340.50,
		'2025-06-20': -25.00,
		'2025-06-21': 0.00,
	};
</script>


<div class="p-0">

	<PnLCalendar data={myProfitLossData} />



</div>