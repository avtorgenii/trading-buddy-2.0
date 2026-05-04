<script>
	import { API_BASE_URL } from '$lib/config.js';
	import { csrfToken } from '$lib/stores.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { createEventDispatcher } from 'svelte';

	let { open = $bindable(), accounts = [] } = $props();
	const dispatch = createEventDispatcher();

	const TRADE_SETUPS = [
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
		{ value: 'DOWN_WEDGE_BREAKTHROUGH', label: 'Нисходящий клин - пробой верхней границы' },
		{ value: 'DOWN_WEDGE_RETEST', label: 'Нисходящий клин - ретест верхней границы' },
		{ value: 'UP_WEDGE_BREAKTHROUGH', label: 'Восходящий клин - пробой нижней границы' },
		{ value: 'UP_WEDGE_RETEST', label: 'Восходящий клин - ретест нижней границы' },
		{ value: 'DOWN_CHANNEL_REBOUND', label: 'Нисходящий канал - отбой вниз от верхней границы' },
		{ value: 'DOWN_CHANNEL_BREAKTHROUGH', label: 'Нисходящий канал - пробой верхней границы' },
		{ value: 'DOWN_CHANNEL_RETEST', label: 'Нисходящий канал - ретест верхней границы' },
		{ value: 'UP_CHANNEL_REBOUND', label: 'Восходящий канал - пробой нижней границы' },
		{ value: 'UP_CHANNEL_BREAKTHROUGH', label: 'Восходящий канал - ретест нижней границы' },
		{ value: 'UP_CHANNEL_RETEST', label: 'Восходящий канал - отбой вверх от нижней границы' },
		{ value: 'SECANT_RETEST', label: 'Ретест секущей в шорт' },
		{ value: 'DOWN_TRENDLINE_REBOUND', label: 'Отбой вниз от нисходящей трендовой' },
		{ value: 'UP_TRENDLINE_REBOUND', label: 'Отбой вверх от восходящей трендовой' }
	];

	const TIMEFRAMES = ['H4', 'D', 'W'];

	let isSubmitting = $state(false);
	let form = $state({
		tool_name: '',
		account_id: accounts[0]?.id ?? '',
		side: 'LONG',
		start_time: '',
		end_time: '',
		risk_percent: '',
		risk_usd: '',
		pnl_usd: '',
		commission_usd: '',
		timeframe: 'D',
		description: '',
		result: '',
		trade_setup: '',
		tags: []
	});

	async function submit() {
		isSubmitting = true;
		try {
			const resp = await fetch(`${API_BASE_URL}/journal/investments/create/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include',
				body: JSON.stringify({
					...form,
					risk_percent: form.risk_percent || 0,
					risk_usd: form.risk_usd || 0,
					pnl_usd: form.pnl_usd || 0,
					commission_usd: form.commission_usd || 0,
					trade_setup: form.trade_setup || null,
					start_time: form.start_time || null,
					end_time: form.end_time || null
				})
			});

			if (!resp.ok) {
				const err = await resp.json();
				showErrorToast(JSON.stringify(err.error));
			} else {
				showSuccessToast('Investment added.');
				dispatch('created');
				open = false;
			}
		} catch (err) {
			showErrorToast(err.message);
		}
		isSubmitting = false;
	}

	const inputClass = 'bg-zinc-800 border border-zinc-700 text-white rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:border-zinc-500';
	const labelClass = 'text-xs text-zinc-400 mb-1 block';
</script>

{#if open}
	<div
		class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 overflow-y-auto py-8"
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<div class="bg-zinc-900 w-full max-w-2xl mx-4 rounded-2xl shadow-xl shadow-white/10 p-6 flex flex-col gap-4">
			<h2 class="text-xl font-semibold text-white">Add Investment</h2>

			<div class="grid grid-cols-2 gap-3">
				<div>
					<label for="ai-tool" class={labelClass}>Instrument</label>
					<input id="ai-tool" type="text" bind:value={form.tool_name} placeholder="AAPL" class={inputClass} />
				</div>

				<div>
					<label for="ai-account" class={labelClass}>Account</label>
					<select id="ai-account" bind:value={form.account_id} class={inputClass}>
						{#each accounts as acc}
							<option value={acc.id}>{acc.name}</option>
						{/each}
					</select>
				</div>

				<div>
					<label for="ai-side" class={labelClass}>Side</label>
					<select id="ai-side" bind:value={form.side} class={inputClass}>
						<option value="LONG">Long</option>
						<option value="SHORT">Short</option>
					</select>
				</div>

				<div>
					<label for="ai-timeframe" class={labelClass}>Timeframe</label>
					<select id="ai-timeframe" bind:value={form.timeframe} class={inputClass}>
						{#each TIMEFRAMES as tf}
							<option value={tf}>{tf}</option>
						{/each}
					</select>
				</div>

				<input id="ai-start" type="date" bind:value={form.start_time} class={inputClass} />
				<input id="ai-end" type="date" bind:value={form.end_time} class={inputClass} />

				<div>
					<label for="ai-risk-pct" class={labelClass}>Risk %</label>
					<input id="ai-risk-pct" type="number" step="0.01" bind:value={form.risk_percent} class={inputClass} />
				</div>

				<div>
					<label for="ai-risk-usd" class={labelClass}>Risk $</label>
					<input id="ai-risk-usd" type="number" step="0.01" bind:value={form.risk_usd} class={inputClass} />
				</div>

				<div>
					<label for="ai-pnl" class={labelClass}>Net PnL $</label>
					<input id="ai-pnl" type="number" step="0.01" bind:value={form.pnl_usd} class={inputClass} />
				</div>

				<div>
					<label for="ai-commission" class={labelClass}>Commission $</label>
					<input id="ai-commission" type="number" step="0.01" bind:value={form.commission_usd} class={inputClass} />
				</div>
			</div>

			<div>
				<label for="ai-setup" class={labelClass}>Setup</label>
				<select id="ai-setup" bind:value={form.trade_setup} class={inputClass}>
					<option value="">— None —</option>
					{#each TRADE_SETUPS as setup}
						<option value={setup.value}>{setup.label}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="ai-description" class={labelClass}>Description</label>
				<textarea id="ai-description" bind:value={form.description} rows="3" class={inputClass}></textarea>
			</div>

			<div>
				<label for="ai-result" class={labelClass}>Result</label>
				<textarea id="ai-result" bind:value={form.result} rows="3" class={inputClass}></textarea>
			</div>

			<div class="flex gap-3 justify-end pt-2">
				<button
					onclick={() => open = false}
					class="px-5 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-semibold transition-all">
					Cancel
				</button>
				<button
					onclick={submit}
					disabled={isSubmitting || !form.tool_name || !form.account_id}
					class="px-5 py-2 rounded-lg bg-blue-700 hover:bg-blue-600 text-white text-sm font-semibold transition-all disabled:opacity-50">
					{isSubmitting ? 'Saving...' : 'Save'}
				</button>
			</div>
		</div>
	</div>
{/if}