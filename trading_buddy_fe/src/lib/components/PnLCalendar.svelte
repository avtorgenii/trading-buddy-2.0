<script>
	export let data = {};

	let currentDate = new Date();
	let currentYear = currentDate.getFullYear();
	let currentMonth = currentDate.getMonth();

	let avgDailyPnl = 0;
	let winningDaysPercent = 0;

	const enDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const enMonths = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

	$: {
		const monthEntries = Object.entries(data).filter(([date]) => {
			const d = new Date(date);
			return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
		});

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
	}

	$: calendarGrid = (() => {
		const grid = [];
		const dayOfWeek = new Date(currentYear, currentMonth, 1).getDay();
		const paddingDays = (dayOfWeek === 0) ? 6 : dayOfWeek - 1;
		const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

		for (let i = 0; i < paddingDays; i++) {
			grid.push(null);
		}

		for (let i = 1; i <= daysInMonth; i++) {
			grid.push(new Date(currentYear, currentMonth, i));
		}
		return grid;
	})();


	function goToPreviousMonth() {
		if (currentMonth === 0) {
			currentMonth = 11;
			currentYear--;
		} else {
			currentMonth--;
		}
	}

	function goToNextMonth() {
		if (currentMonth === 11) {
			currentMonth = 0;
			currentYear++;
		} else {
			currentMonth++;
		}
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
		<button on:click={goToPreviousMonth} class="p-2 rounded-full hover:bg-zinc-700 transition-colors">&lt;</button>
		<div class="font-bold text-lg md:text-2xl text-center">
			{enMonths[currentMonth]} {currentYear}
		</div>
		<button on:click={goToNextMonth} class="p-2 rounded-full hover:bg-zinc-700 transition-colors">&gt;</button>
	</header>

	<div class="grid grid-cols-7 gap-1 md:gap-2">
		{#each enDays as dayName}
			<div class="text-center text-xs md:text-sm font-bold text-zinc-400 py-2">{dayName}</div>
		{/each}

		{#each calendarGrid as day}
			{#if day}
				{@const dateStr = toISODateString(day)}
				{@const pnl = data[dateStr]}

				<div
					class="h-16 md:h-20 flex flex-col items-center justify-center rounded-lg md:rounded-xl transition-colors"
					class:bg-green-600={pnl > 0}
					class:bg-red-600={pnl < 0}
					class:bg-zinc-800={pnl === 0}
					class:text-zinc-400={pnl === 0}
					class:bg-zinc-900={pnl === undefined}
				>
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