<script>
	import UpdateTradeFieldModal from '$lib/components/modals/UpdateTradeFieldModal.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { csrfToken } from '$lib/stores.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { createEventDispatcher } from 'svelte';

	let { trade, isInvesting = false } = $props();

	let screenshotUrl = $derived(
		trade.screenshot_url
			? trade.screenshot_url.startsWith('data:')
				? trade.screenshot_url
				: `${trade.screenshot_url}?t=${Date.now()}`
			: null
	);

	let isSubmitting = $state(false);
	let modalOpen = $state(false);
	let modalField = $state('');
	let modalInputType = $state('textarea');
	let modalOptions = $state([]);

	const dispatch = createEventDispatcher();
	let deleteModalOpen = $state(false);

	const SIDE_OPTIONS = [
		{ value: 'LONG', label: 'Long' },
		{ value: 'SHORT', label: 'Short' }
	];

	const SETUP_OPTIONS = [
		{ value: 'ACC_BORDER_BREAKTHROUGH', label: '(Ре)накопление - Пробой верхней границы' },
		{ value: 'ACC_BORDER_RETEST', label: '(Ре)накопление - Ретест верхней границы' },
		{ value: 'ACC_CREEK_BREAKTHROUGH', label: '(Ре)накопление - Пробой крика' },
		{ value: 'ACC_CREEK_RETEST', label: '(Ре)накопление - Ретест крика' },
		{ value: 'ACC_SPRING', label: '(Ре)накопление - Спринг' },
		{ value: 'DISTR_BORDER_RETEST', label: '(Ре)дистрибьюция - Ретест нижней границы' },
		{ value: 'DISTR_ICE_RETEST', label: '(Ре)дистрибьюция - Ретест льда' },
		{ value: 'DISTR_UPTHRUST', label: '(Ре)дистрибьюция - Аптраст' },
		{ value: 'BEAR_WOLFE', label: 'Медвежий Вульф' },
		{ value: 'BULL_WOLFE', label: 'Бычий Вульф' },
		{ value: 'DOWN_WEDGE_BREAKTHROUGH', label: 'Нисходящий клин - Пробой верхней границы' },
		{ value: 'DOWN_WEDGE_RETEST', label: 'Нисходящий клин - Ретест верхней границы' },
		{ value: 'UP_WEDGE_BREAKTHROUGH', label: 'Восходящий клин - Пробой нижней границы' },
		{ value: 'UP_WEDGE_RETEST', label: 'Восходящий клин - Ретест нижней границы' },
		{ value: 'DOWN_CHANNEL_REBOUND', label: 'Нисходящий канал - Отбой вниз от верхней границы' },
		{ value: 'DOWN_CHANNEL_BREAKTHROUGH', label: 'Нисходящий канал - Пробой верхней границы' },
		{ value: 'DOWN_CHANNEL_RETEST', label: 'Нисходящий канал - Ретест верхней границы' },
		{ value: 'UP_CHANNEL_REBOUND', label: 'Восходящий канал - Пробой нижней границы' },
		{ value: 'UP_CHANNEL_BREAKTHROUGH', label: 'Восходящий канал - Ретест нижней границы' },
		{ value: 'UP_CHANNEL_RETEST', label: 'Восходящий канал - Отбой вверх от нижней границы' },
		{ value: 'SECANT_RETEST', label: 'Ретест секущей в шорт' },
		{ value: 'DOWN_TRENDLINE_REBOUND', label: 'Отбой вниз от нисходящей трендовой' },
		{ value: 'UP_TRENDLINE_REBOUND', label: 'Отбой вверх от восходящей трендовой' }
	];

	const FIELD_CONFIG = {
		timeframe: { inputType: 'text' },
		description: { inputType: 'textarea' },
		result: { inputType: 'textarea' },
		side: { inputType: 'select', options: SIDE_OPTIONS },
		trade_setup: { inputType: 'select', options: SETUP_OPTIONS },
		start_time: { inputType: 'date' },
		end_time: { inputType: 'date' },
		risk_percent: { inputType: 'number' },
		risk_usd: { inputType: 'number' },
		pnl_usd: { inputType: 'number' },
		commission_usd: { inputType: 'number' }
	};

	function openEdit(field) {
		const config = FIELD_CONFIG[field] ?? { inputType: 'textarea' };
		modalField = field;
		modalInputType = config.inputType;
		modalOptions = config.options ?? [];
		modalOpen = true;
	}

	function handleSaved(event) {
		const { fieldName, value } = event.detail;
		trade[fieldName] = value;
	}

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
			const resp = await fetch(`${API_BASE_URL}/journal/trades/${trade.id}/`, {
				method: 'PUT',
				headers: { 'X-CSRFToken': $csrfToken },
				credentials: 'include',
				body: formData
			});
			if (resp.ok) {
				showSuccessToast('Screenshot uploaded.');
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

	function handleDelete() {
		isSubmitting = true;
		dispatch('deleted');
		deleteModalOpen = false;
		isSubmitting = false;
	}

	let sideColor = $derived(trade.side === 'LONG' ? 'text-green-400' : 'text-red-400');
	let sideBg = $derived(trade.side === 'LONG' ? 'bg-green-900/40' : 'bg-red-900/40');
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape' && showImageModal) showImageModal = false; }} />
<div class="bg-zinc-900 p-6 rounded-2xl shadow-lg shadow-white/10 flex flex-col space-y-4 min-h-[420px]">
	<!-- Header row -->
	<div class="flex items-baseline justify-between flex-wrap gap-2">
		<h3 class="text-xl font-bold text-white whitespace-nowrap">
			{trade.trade_number}. {trade.tool_name}
			<button onclick={() => openEdit('timeframe')}>
				<span class="cursor-pointer hover:text-blue-400 transition">{trade.timeframe}</span>
			</button>
		</h3>

		{#if isInvesting}
			<button onclick={() => openEdit('side')}>
				<span
					class={`px-3 py-1 rounded-full text-xs font-semibold uppercase cursor-pointer hover:opacity-70 transition ${sideBg} ${sideColor}`}>{trade.side}</span>
			</button>
		{:else}
			<span class={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${sideBg} ${sideColor}`}>{trade.side}</span>
		{/if}

		<span class="text-sm text-zinc-400 ml-auto">{trade.account_name}</span>
		<button onclick={() => { deleteModalOpen = true; }}>
			<span class="cursor-pointer hover:text-red-400 transition text-2xl">×</span>
		</button>
	</div>

	<!-- Time range -->
	<div class="text-sm text-zinc-400 flex flex-wrap gap-x-1">
		{#if isInvesting}
			<button onclick={() => openEdit('start_time')}
							class="hover:text-blue-400 transition cursor-pointer">{trade.start_time || '—'}</button>
			<span class="mx-1">→</span>
			<button onclick={() => openEdit('end_time')}
							class="hover:text-blue-400 transition cursor-pointer">{trade.end_time || '—'}</button>
		{:else}
			<span>{trade.start_time}</span>
			<span class="mx-1">→</span>
			<span>{trade.end_time}</span>
		{/if}
	</div>

	<!-- Metrics -->
	<div class="grid grid-cols-2 gap-y-1 text-sm">
		<div class="text-zinc-400">Risk:</div>
		{#if isInvesting}
			<div class="flex gap-2">
				<button onclick={() => openEdit('risk_percent')}
								class="text-white hover:text-blue-400 transition cursor-pointer">{trade.risk_percent}%
				</button>
				<span class="text-zinc-600"> = </span>
				<button onclick={() => openEdit('risk_usd')} class="text-white hover:text-blue-400 transition cursor-pointer">
					${trade.risk_usd}</button>
			</div>
		{:else}
			<div class="text-white">{trade.risk_percent}% = ${trade.risk_usd}</div>
		{/if}

		<div class="text-zinc-400">Net PnL:</div>
		{#if isInvesting}
			<button onclick={() => openEdit('pnl_usd')} class="text-left cursor-pointer group">
				{#if parseFloat(trade.pnl_usd) < 0}
					<span
						class="text-white group-hover:text-blue-400 transition">-${Math.abs(parseFloat(trade.pnl_usd)).toFixed(2)}</span>
				{:else}
					<span
						class="text-white group-hover:text-blue-400 transition">${Math.abs(parseFloat(trade.pnl_usd)).toFixed(2)}</span>
				{/if}
			</button>
		{:else}
			{#if parseFloat(trade.pnl_usd) < 0}
				<div class="text-white">-${Math.abs(parseFloat(trade.pnl_usd)).toFixed(2)}</div>
			{:else}
				<div class="text-white">${parseFloat(trade.pnl_usd).toFixed(2)}</div>
			{/if}
		{/if}

		<div class="text-zinc-400">Commissions:</div>
		{#if isInvesting}
			<button onclick={() => openEdit('commission_usd')} class="text-left cursor-pointer group">
				{#if parseFloat(trade.commission_usd) < 0}
					<span
						class="text-white group-hover:text-blue-400 transition">-${Math.abs(parseFloat(trade.commission_usd)).toFixed(2)}</span>
				{:else}
					<span
						class="text-white group-hover:text-blue-400 transition">${parseFloat(trade.commission_usd).toFixed(2)}</span>
				{/if}
			</button>
		{:else}
			{#if parseFloat(trade.commission_usd) < 0}
				<div class="text-white">-${Math.abs(parseFloat(trade.commission_usd)).toFixed(2)}</div>
			{:else}
				<div class="text-white">${parseFloat(trade.commission_usd).toFixed(2)}</div>
			{/if}
		{/if}

		<div class="text-zinc-400">PnL Risk Ratio:</div>
		<div class="text-white">{trade.pnl_risk_ratio}</div>
	</div>


	<div>
		<h4 class="text-zinc-400 text-sm mb-1">Setup</h4>
		<button onclick={() => openEdit('trade_setup')}
						class="text-sm text-white hover:text-blue-400 transition text-left w-full cursor-pointer">
			{SETUP_OPTIONS.find(o => o.value === trade.trade_setup)?.label ?? '—'}
		</button>
	</div>

	<!-- Description / Result -->
	<div class="space-y-3 flex-1">
		<div>
			<h4 class="text-zinc-400 text-sm mb-1">Description</h4>
			<button onclick={() => openEdit('description')}
							class="text-sm text-white whitespace-pre-line min-h-[2.5rem] cursor-pointer hover:text-blue-400 transition text-left w-full">
				{trade.description?.trim() || '—'}
			</button>
		</div>

		<div>
			<h4 class="text-zinc-400 text-sm mb-1">Result</h4>
			<button onclick={() => openEdit('result')}
							class="text-sm text-white whitespace-pre-line min-h-[2.5rem] cursor-pointer hover:text-blue-400 transition text-left w-full">
				{trade.result?.trim() || '—'}
			</button>
		</div>
	</div>

	<!-- Screenshot -->
	{#if screenshotUrl}
		<button onclick={() => showImageModal = true}>
			<img src={screenshotUrl} alt="screenshot"
					 class="w-full h-72 object-cover rounded-lg border border-zinc-700 cursor-pointer transition hover:scale-105 duration-200" />
		</button>
		<div class="flex justify-end my-0">
			<button type="button"
							class="bg-zinc-800 hover:bg-zinc-700 text-sm px-4 py-2 rounded-xl transition-colors"
							onclick={triggerUpload}>
				Replace screenshot
			</button>
		</div>
	{:else}
		<button
			class="w-full h-40 rounded-lg border-2 border-dashed border-zinc-700 flex items-center justify-center text-zinc-500 text-sm cursor-pointer"
			onclick={triggerUpload}>
			No screenshot
		</button>
	{/if}

	<input type="file" accept="image/*" bind:this={fileInput} class="hidden" onchange={handleFileChange} />
</div>

<!-- Fullscreen image modal -->
{#if showImageModal}
	<button onclick={() => showImageModal = false}
					class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center"
					aria-label="Close image modal">
		<img src={screenshotUrl} alt="full screenshot"
				 class="max-w-[90vw] max-h-[90vh] rounded-xl border border-zinc-700 shadow-2xl" />
	</button>
{/if}

{#if modalOpen}
	<UpdateTradeFieldModal
		positionId={trade.id}
		fieldName={modalField}
		initialValue={modalField === 'start_time' ? trade.start_time_raw : modalField === 'end_time' ? trade.end_time_raw : trade[modalField]}
		inputType={modalInputType}
		options={modalOptions}
		apiEndpoint={isInvesting ? `/journal/investments/${trade.id}/` : undefined}
		bind:open={modalOpen}
		on:saved={handleSaved} />
{/if}

{#if deleteModalOpen}
	<div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
			 role="dialog" aria-modal="true" aria-label="Delete trade" tabindex="-1">
		<div class="bg-zinc-900 w-full max-w-lg mx-4 rounded-2xl shadow-xl shadow-white/10 p-6" role="document">
			<form onsubmit={handleDelete}>
				<h2 class="text-xl font-semibold text-white mb-4">Delete trade</h2>
				<p>Are you sure you want to delete this trade?</p>
				<p>This action is irreversible.</p>
				<div class="flex justify-end mt-6 space-x-4">
					<button type="button"
									class="py-2 px-4 rounded-xl border-2 border-zinc-600 hover:bg-zinc-800 transition-colors"
									onclick={() => { deleteModalOpen = false; }} disabled={isSubmitting}>
						Cancel
					</button>
					<button type="submit"
									class="py-2 px-6 rounded-xl bg-red-800 hover:bg-red-700 transition-colors disabled:opacity-60"
									disabled={isSubmitting}>
						{isSubmitting ? 'Deleting...' : 'Delete'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}