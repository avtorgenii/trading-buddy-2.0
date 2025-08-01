<script>
	import UpdateTradeFieldModal from '$lib/components/UpdateTradeFieldModal.svelte';

	let { trade } = $props();
	// To mitigate browsers aggressive caching
	let screenshotUrl = $derived(trade.screenshot_url ? `${trade.screenshot_url}?t=${Date.now()}` : null);

	// Editable fields
	let modalOpen = $state(false);
	let modalField = $state(''); // 'timeframe' | 'description' | 'result'

	function openEdit(field) {
		modalField = field;
		modalOpen = true;
	}

	function handleSaved(event) {
		const { fieldName, value } = event.detail;
		trade[fieldName] = value;         // keep UI in sync without re‑fetching
	}

	// Screenshot handling
	let showImageModal = $state(false);
	let fileInput;

	function triggerUpload() {
		fileInput.click();
	}

	function handleFileChange(e) {
		const file = e.target.files[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => (trade.screenshot_url = reader.result);
		reader.readAsDataURL(file);
	}

	function openImageModal() {
		showImageModal = true;
	}

	function closeImageModal() {
		showImageModal = false;
	}

	const sideColor = trade.side === 'LONG' ? 'text-green-400' : 'text-red-400';
	const sideBg = trade.side === 'LONG' ? 'bg-green-900/40' : 'bg-red-900/40';
</script>

<div class="bg-zinc-900 p-6 rounded-2xl shadow-lg shadow-white/10 flex flex-col space-y-4 min-h-[420px]">
	<!-- Header row -->
	<div class="flex items-baseline justify-between flex-wrap gap-2">
		<h3 class="text-xl font-bold text-white whitespace-nowrap">
			{trade.id}. {trade.tool_name}
			<button onclick={() => openEdit('timeframe')}><span
				class="cursor-pointer hover:text-blue-400 transition">
			{trade.timeframe}
		</span></button>

		</h3>
		<span class={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${sideBg} ${sideColor}`}>{trade.side}</span>
		<span class="text-sm text-zinc-400 ml-auto">{trade.account_name}</span>
	</div>

	<!-- Time range -->
	<div class="text-sm text-zinc-400 flex flex-wrap gap-x-1">
		<span>{trade.start_time}</span>
		<span class="mx-1">→</span>
		<span>{trade.end_time}</span>
	</div>

	<!-- Metrics -->
	<div class="grid grid-cols-2 gap-y-1 text-sm">
		<div class="text-zinc-400">Risk:</div>
		<div class="text-white">{trade.risk_percent}%</div>

		<div class="text-zinc-400">Net PnL:</div>
		<div class="text-white">
			{trade.pnl_usd < 0 ? `-$${Math.abs(trade.pnl_usd)}` : `$${trade.pnl_usd}`}
		</div>


		<div class="text-zinc-400">Commissions:</div>
		<div class="text-white">
			{trade.commission_usd < 0 ? `-$${Math.abs(trade.commission_usd)}` : `$${trade.commission_usd}`}
		</div>


		<div class="text-zinc-400">PnL Risk Ratio:</div>
		<div class="text-white">{trade.pnl_risk_ratio}</div>
	</div>

	<!-- Description / Result -->
	<div class="space-y-3 flex-1">
		<div>
			<h4 class="text-zinc-400 text-sm mb-1">Description</h4>
			<button
				onclick={() => openEdit('description')}
				class="text-sm text-white whitespace-pre-line min-h-[2.5rem] cursor-pointer hover:text-blue-400 transition text-left w-full"
			>
				{trade.description?.trim() || '—'}
			</button>

		</div>

		<div>
			<h4 class="text-zinc-400 text-sm mb-1">Result</h4>
			<button
				onclick={() => openEdit('result')}
				class="text-sm text-white whitespace-pre-line min-h-[2.5rem] cursor-pointer hover:text-blue-400 transition text-left w-full"
			>
				{trade.result?.trim() || '—'}
			</button>

		</div>
	</div>

	<!-- Screenshot placeholder -->
	{#if screenshotUrl}
		<button onclick={openImageModal}>
			<img
				src={screenshotUrl}
				alt="screenshot"
				class="w-full h-72 object-cover rounded-lg border border-zinc-700 cursor-pointer transition hover:scale-105 duration-200"
			/>
		</button>
	{:else}
		<button
			class="w-full h-40 rounded-lg border-2 border-dashed border-zinc-700 flex items-center justify-center text-zinc-500 text-sm cursor-pointer"
			onclick={triggerUpload}>
			No screenshot
		</button>
	{/if}

	<input type="file" accept="image/*" bind:this={fileInput} class="hidden" onchange={handleFileChange} />

</div>

<!-- Fullscreen Modal -->
{#if showImageModal}
	<button
		onclick={closeImageModal}
		class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center transition-opacity duration-300"
		aria-label="Close image modal"
	>
		<img
			src={screenshotUrl}
			alt="full screenshot"
			class="max-w-[90vw] max-h-[90vh] rounded-xl border border-zinc-700 shadow-2xl transition-transform duration-300 scale-100"
		/>
	</button>
{/if}

{#if modalOpen}
	<UpdateTradeFieldModal
		positionId={trade.id}
		fieldName={modalField}
		initialValue={trade[modalField]}
		bind:open={modalOpen}
		on:saved={handleSaved} />
{/if}