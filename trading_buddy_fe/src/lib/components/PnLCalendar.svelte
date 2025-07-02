<script>
	import { onMount } from 'svelte';
	import { API_BASE_URL } from '$lib/config.js';

	let monthlyData = $state({});
	let isLoading = $state(true);

	let currentDate = new Date();
	let currentYear = $state(currentDate.getFullYear());
	let currentMonth = $state(currentDate.getMonth());

	let avgDailyPnl = $state(0);
	let winningDaysPercent = $state(0);

	const enDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const enMonths = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

	async function fetchMonthlyData(year, month) {
		isLoading = true;
		const apiMonth = month + 1;
		const url = `${API_BASE_URL}/stats/pnl-calendar/all/${year}/${apiMonth}/`;


		try {
			const response = await fetch(url, {
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`Response error: ${response.status}`);
			}

			const responseData = await response.json();
			const parsedData = {};

			if (responseData && responseData.pnl_by_day) {
				for (const [date, pnl] of Object.entries(responseData.pnl_by_day)) {
					parsedData[date] = parseFloat(pnl);
				}
			}
			monthlyData = parsedData;

		} catch (error) {
			console.error("Error Downloading data:", error);
			monthlyData = {};
		} finally {
			isLoading = false;
		}
	}

	$effect(() => {
		if (currentYear !== undefined && currentMonth !== undefined) {
			fetchMonthlyData(currentYear, currentMonth);
		}
	});

	$effect(() => {
		const monthEntries = Object.entries(monthlyData);
		const tradeCount = monthEntries.length;

		if (tradeCount > 0) {
			const winningDaysCount = monthEntries.filter(([_, pnl]) => pnl > 0).length;
			const totalPnL = monthEntries.reduce((sum, [_, pnl]) => sum + pnl, 0);

			avgDailyPnl = totalPnL / tradeCount;
			winningDaysPercent = (winningDaysCount / tradeCount) * 100;
		} else {
			avgDailyPnl = 0;
			winningDaysPercent = 0;
		}
	});

	let calendarGrid = $derived.by(() => {
		const grid = [];
		const dayOfWeek = new Date(currentYear, currentMonth, 1).getDay();
		const paddingDays = (dayOfWeek === 0) ? 6 : dayOfWeek - 1;
		const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

		for (let i = 0; i < paddingDays; i++) { grid.push(null); }
		for (let i = 1; i <= daysInMonth; i++) { grid.push(new Date(currentYear, currentMonth, i)); }
		return grid;
	});

	function goToPreviousMonth() {
		if (currentMonth === 0) { currentMonth = 11; currentYear--; } else { currentMonth--; }
	}

	function goToNextMonth() {
		if (currentMonth === 11) { currentMonth = 0; currentYear++; } else { currentMonth++; }
	}

	function toISODateString(date) {
		const year = date.getFullYear();
		const month = String(date.getMonth() + 1).padStart(2, '0');
		const day = String(date.getDate()).padStart(2, '0');
		return `${year}-${month}-${day}`;
	}
</script>
<div class="bg-zinc-900 text-white p-2 md:p-6 rounded-2xl max-w-full md:max-w-lg mx-auto shadow-lg">

	<header class="flex items-center justify-between mb-4 md:mb-6">
		<button onclick={goToPreviousMonth} class="p-2 rounded-full hover:bg-zinc-700 transition-colors" disabled={isLoading}>&lt;</button>
		<div class="font-bold text-lg md:text-2xl text-center w-48">
			{#if isLoading}
				<span class="text-zinc-500 animate-pulse">Loading...</span>
			{:else}
				{enMonths[currentMonth]} {currentYear}
			{/if}
		</div>
		<button onclick={goToNextMonth} class="p-2 rounded-full hover:bg-zinc-700 transition-colors" disabled={isLoading}>&gt;</button>
	</header>

	<div class="relative">
		{#if isLoading}
			<div class="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm flex items-center justify-center rounded-xl z-10">
				<div class="w-8 h-8 border-4 border-zinc-500 border-t-blue-500 rounded-full animate-spin"></div>
			</div>
		{/if}

		<div class="grid grid-cols-7 gap-1 md:gap-2">
			{#each enDays as dayName}
				<div class="text-center text-xs md:text-sm font-bold text-zinc-400 py-2">{dayName}</div>
			{/each}

			{#each calendarGrid as day}
				{#if day}
					{@const dateStr = toISODateString(day)}
					{@const pnl = monthlyData[dateStr]}

					<div
						class="h-16 md:h-20 flex flex-col items-center justify-center rounded-lg md:rounded-xl transition-colors"
						class:bg-green-600={pnl > 0}
						class:bg-red-600={pnl < 0}
						class:bg-zinc-800={pnl === 0}
						class:text-zinc-400={pnl === 0}
						class:bg-zinc-900={pnl === undefined}>
						<div class="text-base md:text-xl font-medium">{day.getDate()}</div>
						{#if pnl !== undefined}
							<div class="text-xs md:text-sm font-mono mt-1 md:mt-2 text-wrap">
								{pnl > 0 ? `+${pnl.toFixed(2)}` : pnl.toFixed(2)}
							</div>
						{/if}
					</div>
				{:else}
					<div></div>
				{/if}
			{/each}
		</div>
	</div>

	<div class="space-y-2 bg-zinc-800 rounded-xl p-4 my-4">
		<div class="flex justify-between">
			<span class="text-zinc-400 text-lg md:text-xl">Avg Daily PnL</span>
			<span class="text-white text-lg md:text-xl font-mono"
						class:text-green-500={avgDailyPnl > 0}
						class:text-red-500={avgDailyPnl < 0}>
        ${avgDailyPnl.toFixed(2)}
      </span>
		</div>
		<div class="flex justify-between">
			<span class="text-zinc-400 text-lg md:text-xl">Winning Days %</span>
			<span class="text-white text-lg md:text-xl font-mono">
        {winningDaysPercent.toFixed(0)}%
      </span>
		</div>
	</div>
</div>