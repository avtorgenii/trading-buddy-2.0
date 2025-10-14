<script>
	import PnLCalendar from '$lib/components/PnLCalendar.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { onMount } from 'svelte';
	import Chart from 'chart.js/auto';

	// State variables
	let totalPnl = $state(0);
	let winRate = $state(0);
	let toolsWithWinrates = $state([]);
	let pnlProgression = $state([]);
	let reversedPnlProgression = $derived(pnlProgression.slice().reverse());
	let loading = $state(true);
	let chartError = $state(null);
	let pnlChart;

	// Fetch functions
	async function fetchTotalPnl() {
		const url = `${API_BASE_URL}/stats/pnl/total/`;
		try {
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) throw new Error(`Response error: ${response.status}`);
			const data = await response.json();
			totalPnl = parseFloat(data) || 0;
		} catch (error) {
			console.error('Error fetching total PnL:', error);
		}
	}

	async function fetchWinRate() {
		const url = `${API_BASE_URL}/stats/winrate/`;
		try {
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) throw new Error(`Response error: ${response.status}`);
			const data = await response.json();
			winRate = parseFloat(data) || 0;
		} catch (error) {
			console.error('Error fetching win rate:', error);
		}
	}

	async function fetchToolsWithWinrates() {
		const url = `${API_BASE_URL}/stats/tools/winrates/`;
		try {
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) throw new Error(`Response error: ${response.status}`);
			const data = await response.json();
			toolsWithWinrates = data || [];
		} catch (error) {
			console.error('Error fetching tools winrates:', error);
		}
	}

	async function fetchPnLProgression() {
		const url = `${API_BASE_URL}/stats/pnl/progression/`;
		try {
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) throw new Error(`Response error: ${response.status}`);
			const data = await response.json();
			pnlProgression = data.map(item => ({
				day: item.day,
				daily_pnl: parseFloat(item.daily_pnl),
				cumulative_pnl: parseFloat(item.cumulative_pnl)
			})) || [];
		} catch (error) {
			console.error('Error fetching PnL progression:', error);
		}
	}

	async function fetchAllStats() {
		loading = true;
		await Promise.all([
			fetchTotalPnl(),
			fetchWinRate(),
			fetchToolsWithWinrates(),
			fetchPnLProgression()
		]);
		loading = false;
	}

	function createChart() {
		const ctx = document.getElementById('pnlChart');
		if (!ctx) {
			chartError = 'Canvas element with ID "pnlChart" not found';
			console.error(chartError);
			return;
		}
		if (pnlProgression.length === 0) {
			chartError = 'No PnL progression data available';
			console.error(chartError);
			return;
		}

		if (pnlChart) {
			pnlChart.destroy();
			pnlChart = null;
		}

		const isValidData = pnlProgression.every(
			item => item.day && !isNaN(item.cumulative_pnl) && !isNaN(item.daily_pnl)
		);
		if (!isValidData) {
			chartError = 'Invalid PnL progression data format';
			console.error(chartError, pnlProgression);
			return;
		}

		const values = pnlProgression.map(d => parseFloat(d.cumulative_pnl));
		const max = Math.max(...values, 0);
		const min = Math.min(...values, 0);

		try {
			pnlChart = new Chart(ctx, {
				type: 'line',
				data: {
					labels: pnlProgression.map(d => d.day),
					datasets: [{
						label: 'Cumulative PnL',
						data: values,
						borderColor: values.map(v => v >= 0 ? '#22c55e' : '#ef4444'),
						borderWidth: 3,
						pointBackgroundColor: values.map(v => v >= 0 ? '#22c55e' : '#ef4444'),
						pointBorderColor: '#18181b',
						pointBorderWidth: 2,
						pointRadius: 4,
						fill: {
							target: 'origin',
							above: (context) => {
								const index = context.dataIndex;
								const value = values[index];
								const ctx = context.chart.ctx;
								const chartArea = context.chart.chartArea;
								if (!chartArea) return 'rgba(0,0,0,0)';
								const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
								if (value >= 0) {
									gradient.addColorStop(0, 'rgba(239,68,68,0.3)');
									gradient.addColorStop(1, 'rgba(239,68,68,0)');
								} else {
									gradient.addColorStop(0, 'rgba(34,197,94,0.3)');
									gradient.addColorStop(1, 'rgba(34,197,94,0)');
								}
								return gradient;
							}
						},
						tension: 0
					}]
				},
				options: {
					scales: {
						x: {
							type: 'category',
							title: {
								display: true,
								text: 'Date'
							},
							ticks: {
								callback: function(value, index, ticks) {
									const date = new Date(pnlProgression[index].day);
									return date.toLocaleDateString('en-US', {
										month: 'short',
										day: '2-digit',
										year: 'numeric'
									});
								}
							}
						},
						y: {
							suggestedMin: min,
							suggestedMax: max,
							title: {
								display: true,
								text: 'PnL ($)'
							}
						}
					},
					plugins: {
						filler: {
							propagate: true
						},
						tooltip: {
							callbacks: {
								title: function(tooltipItems) {
									const date = new Date(pnlProgression[tooltipItems[0].dataIndex].day);
									return date.toLocaleDateString('en-US', {
										month: 'short',
										day: '2-digit',
										year: 'numeric'
									});
								},
								label: function(tooltipItem) {
									const index = tooltipItem.dataIndex;
									const dailyPnl = pnlProgression[index].daily_pnl;
									return `Daily PnL: ${dailyPnl >= 0 ? '+' : ''}${dailyPnl.toFixed(2)}`;
								}
							}
						}
					},
					responsive: true,
					maintainAspectRatio: false
				}
			});
			chartError = null;
		} catch (error) {
			chartError = `Failed to create chart: ${error.message}`;
			console.error(chartError);
		}
	}

	onMount(() => {
		fetchAllStats();
		return () => {
			if (pnlChart) {
				pnlChart.destroy();
				pnlChart = null;
			}
		};
	});

	$effect(() => {
		if (!loading && pnlProgression.length > 0) {
			createChart();
		}
	});
</script>

<div class="p-0 mb-10">
	<PnLCalendar />
	<div class="mt-10"></div>

	{#if loading}
		<div class="flex justify-center items-center mt-16">
			<div class="w-8 h-8 border-4 border-zinc-500 border-t-blue-500 rounded-full animate-spin"></div>
		</div>
	{:else}
		<div class="page-wrapper flex flex-col space-y-8">
			<!-- Stats Grid -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto w-full">
				<div class="bg-zinc-800 rounded-lg p-6 text-center">
					<h2 class="text-xl text-zinc-400 mb-2">Total PnL</h2>
					<p class="text-4xl font-bold {totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}">
						{totalPnl < 0 ? `-$${Math.abs(totalPnl).toFixed(2)}` : `$${totalPnl.toFixed(2)}`}
					</p>
				</div>
				<div class="bg-zinc-800 rounded-lg p-6 text-center">
					<h2 class="text-xl text-zinc-400 mb-2">Winrate</h2>
					<p class="text-4xl font-bold text-white">
						{(winRate * 100).toFixed(2)}%
					</p>
				</div>
			</div>

			<!-- Tools with Winrates -->
			<div class="max-w-4xl mx-auto w-full">
				<div class="bg-zinc-800 rounded-lg p-6">
					<h2 class="text-2xl text-white mb-4">Top Tools by Winrate</h2>
					{#if toolsWithWinrates.length > 0}
						<ul class="space-y-2 overflow-y-auto max-h-60">
							{#each toolsWithWinrates as tool}
								<li class="bg-zinc-900 rounded-lg p-4">
									<div class="flex justify-between items-center mb-1">
										<span class="text-white font-semibold">{tool.tool}</span>
										<span class="font-bold {tool.winrate >= 0.5 ? 'text-green-500' : 'text-red-500'}">
											{(tool.winrate * 100).toFixed(0)}%
										</span>
									</div>
									<div class="text-zinc-300 text-sm">
										Total Trades: {tool.total_trades} | Winning Trades: {tool.winning_trades}
									</div>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-zinc-400">No data available</p>
					{/if}
				</div>
			</div>

			<!-- PnL Progression Chart -->
			<div class="max-w-4xl mx-auto w-full">
				<div class="bg-zinc-800 rounded-lg p-6">
					<h2 class="text-2xl text-white mb-4">PnL Progression Over Time</h2>
					{#if pnlProgression.length > 0}
						<div class="bg-zinc-900 rounded-lg p-4 mb-4">
							<canvas id="pnlChart" class="w-full h-64"></canvas>
							{#if chartError}
								<p class="text-red-500 text-center mt-2">{chartError}</p>
							{/if}
						</div>
						<div class="overflow-x-auto max-h-64 overflow-y-auto">
							<table class="w-full text-left">
								<thead class="border-b border-zinc-700 sticky top-0 bg-zinc-800">
								<tr>
									<th class="pb-3 text-zinc-400">Date</th>
									<th class="pb-3 text-zinc-400">Daily PnL</th>
									<th class="pb-3 text-zinc-400">Cumulative PnL</th>
								</tr>
								</thead>
								<tbody>
								{#each reversedPnlProgression as entry}
									<tr class="border-b border-zinc-700">
										<td class="py-3 text-white">{entry.day}</td>
										<td class="py-3 {entry.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}">
											{entry.daily_pnl >= 0 ? '+' : ''}{entry.daily_pnl.toFixed(2)}
										</td>
										<td class="py-3 font-semibold {entry.cumulative_pnl >= 0 ? 'text-green-500' : 'text-red-500'}">
											${entry.cumulative_pnl.toFixed(2)}
										</td>
									</tr>
								{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<p class="text-zinc-400">No data available</p>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
    .page-wrapper {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 1rem;
    }
</style>