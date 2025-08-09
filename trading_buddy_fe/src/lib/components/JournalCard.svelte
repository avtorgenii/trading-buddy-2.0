<script>
	import UpdateTradeFieldModal from '$lib/components/modals/UpdateTradeFieldModal.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { csrfToken } from '$lib/stores.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { createEventDispatcher } from 'svelte';

	let { trade } = $props();
	// To mitigate browsers aggressive caching
	let screenshotUrl = $derived(
		trade.screenshot_url
			? trade.screenshot_url.startsWith('data:')
				? trade.screenshot_url // Keep base64 data URL as-is
				: `${trade.screenshot_url}?t=${Date.now()}` // Append timestamp to regular URL
			: null
	);


	let isSubmitting = $state(false);

	// Editable fields
	let modalOpen = $state(false);
	let modalField = $state(''); // 'timeframe' | 'description' | 'result'

	// Delete modal
	const dispatch = createEventDispatcher();
	let deleteModalOpen = $state(false);


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

	async function uploadScreenshot(file) {
		const formData = new FormData();
		formData.append('screenshot', file);

		isSubmitting = true;
		try {
			const url = `${API_BASE_URL}/journal/trades/${trade.id}/`;
			const resp = await fetch(url, {
				method: 'PUT',
				headers: {
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include',
				body: formData
			});

			if (resp.ok) {
				showSuccessToast(`Screenshot uploaded.`);
			} else {
				const error = await resp.json();
				showErrorToast(error.message);
			}
		} catch (err) {
			showErrorToast(err.message);
		}

		isSubmitting = false;
	}


	function handleFileChange(e) {
		const file = e.target.files[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			trade.screenshot_url = reader.result;
			uploadScreenshot(file);
		};
		reader.readAsDataURL(file);
	}

	function openImageModal() {
		showImageModal = true;
	}

	function closeImageModal() {
		showImageModal = false;
	}


	function handleDelete() {
		isSubmitting = true;
		dispatch('deleted');
		deleteModalOpen = false;
		isSubmitting = false;
	}

	const sideColor = trade.side === 'LONG' ? 'text-green-400' : 'text-red-400';
	const sideBg = trade.side === 'LONG' ? 'bg-green-900/40' : 'bg-red-900/40';
</script>

<div class="bg-zinc-900 p-6 rounded-2xl shadow-lg shadow-white/10 flex flex-col space-y-4 min-h-[420px]">
	<!-- Header row -->
	<div class="flex items-baseline justify-between flex-wrap gap-2">
		<h3 class="text-xl font-bold text-white whitespace-nowrap">
			{trade.tradeNumber}. {trade.tool_name}
			<button onclick={() => openEdit('timeframe')}><span
				class="cursor-pointer hover:text-blue-400 transition">
			{trade.timeframe}
		</span></button>

		</h3>
		<span class={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${sideBg} ${sideColor}`}>{trade.side}</span>
		<span class="text-sm text-zinc-400 ml-auto">{trade.account_name}</span>
		<button onclick={() => {
			deleteModalOpen = true;
		}}><span
			class="cursor-pointer hover:text-red-400 transition text-2xl">
			×
		</span></button>
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
		<div class="text-white">{trade.risk_percent}% = ${trade.risk_usd}</div>

		<div class="text-zinc-400">Net PnL:</div>
		<div class="text-white">
			{trade.pnl_usd < 0 ? `-$${Math.abs(trade.pnl_usd).toFixed(2)}` : `$${trade.pnl_usd}`}
		</div>


		<div class="text-zinc-400">Commissions:</div>
		<div class="text-white">
			{trade.commission_usd < 0 ? `-$${Math.abs(trade.commission_usd).toFixed(2)}` : `$${Math.abs(trade.commission_usd).toFixed(2)}`}
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

{#if deleteModalOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
		role="dialog"
		aria-modal="true"
		aria-label="Delete trade"
		tabindex="-1"
	>
		<!-- Modal Content -->
		<div
			class="bg-zinc-900 w-full max-w-lg mx-4 rounded-2xl shadow-xl shadow-white/10 p-6"
			role="document"
		>
			<form onsubmit={handleDelete}>
				<h2 class="text-xl font-semibold text-white mb-4 capitalize">Delete trade</h2>
				<p>Are you sure you want to delete this trade?</p>
				<p>This action is irreversible.</p>
				<div class="flex justify-end mt-6 space-x-4">
					<button
						type="button"
						class="py-2 px-4 rounded-xl border-2 border-zinc-600 hover:bg-zinc-800 transition-colors"
						onclick={() => {deleteModalOpen = false}}
						disabled={isSubmitting}
					>
						Cancel
					</button>
					<button
						type="submit"
						class="py-2 px-6 rounded-xl bg-red-800 hover:bg-red-700 transition-colors disabled:opacity-60"
						disabled={isSubmitting}
					>
						{isSubmitting ? 'Deleting...' : 'Delete'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}