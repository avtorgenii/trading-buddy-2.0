<script>
	import { API_BASE_URL } from '$lib/config.js';
	import { showSuccessToast, showErrorToast } from '$lib/toasts.js';
	import { csrfToken } from '$lib/stores.js';

	let {
		order,
		onSaveLevels = ({ toolName, levels }) => {
		},
		onCancel = () => {
		}
	} = $props();


	let showLevelsModal = $state(false);
	let editableLevels = $state(order.cancelLevels);

	function openModal() {
		showLevelsModal = true;
	}

	function closeModal() {
		showLevelsModal = false;
	}

	function handleSaveLevels() {
		onSaveLevels({
			toolName: order.ticker,
			levels: Object.values(editableLevels)
		});
		closeModal();
	}

	function handleKeydown(event) {
		if (event.key === 'Escape' && showLevelsModal) {
			closeModal();
		}
	}

	function getStringAfterColon(inputString) {
		const parts = inputString.split(':');
		return parts.length > 1 ? parts.slice(1).join(':') : inputString;
	}

	async function handleCancel() {
		try {
			console.log(order);
			const res = await fetch(
				`${API_BASE_URL}/trading/positions/cancel/`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-CSRFToken': $csrfToken },
					credentials: 'include',
					body: JSON.stringify({ tool: order.ticker })
				}
			);

			if (!res.ok) {
				const errText = await res.text();
				throw new Error(errText || 'Failed to cancel position.');
			}

			showSuccessToast('Position cancelled.');
			onCancel({ positionId: order.positionId });
		} catch (err) {
			showErrorToast(err.message);
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex-none w-full md:px-2 bg-zinc-800 rounded-2xl p-0.5 md:bg-transparent md:rounded-none md:p-0">
	<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 h-full flex flex-col">
		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-3">
			<p class="text-sm text-zinc-400">Type: {order.orderType}</p>
		</div>

		<div class="p-4 flex-grow flex flex-row">
			<div class="w-1/5 text-start">
				<p
					class="uppercase border-l-4 px-2.5 mb-1
                 {order.side === 'long' ? 'border-l-green-600' : 'border-l-red-600'}">
					{order.side}
				</p>
				<p class="text-sm text-zinc-400">Volume: {order.volume}</p>
			</div>

			<div class="w-3/5 flex flex-col">
				<div class="text-center">
					<p class="font-medium">{getStringAfterColon(order.ticker)}</p>
					<br>
					<div class="flex justify-center text-sm text-zinc-400">
						<div class="mr-2">
							<br>
							<p>Margin: {order.margin}$</p>
							<p>Leverage: {order.leverage}x</p>
						</div>
						<div class="ml-2">
							{#if order.triggerPrice}
								<p>Trigger price: {order.triggerPrice}</p>
							{/if}
							<p>Entry price: {order.entryPrice}</p>
							<p>Stop-loss: {order.stopPrice}</p>
							<p>Take-profits: [{order.takeProfits}]</p>
						</div>
					</div>
				</div>
				<div class="mt-3 text-center">
					<p class="text-sm text-zinc-200">{order.status}</p>
				</div>
			</div>

			<div class="w-1/5 flex flex-col items-end justify-between">
				<button
					class="py-1 px-3 cursor-pointer rounded-xl hover:bg-zinc-700 border-2 border-zinc-600 w-20 transition-colors"
					onclick={handleCancel}
					type="button">
					Cancel
				</button>
				<button
					class="py-1 px-3 cursor-pointer rounded-xl hover:bg-zinc-700 border-2 w-20 transition-colors"
					class:border-green-600={order.overLowBuyLevel && order.takeProfitLevel}
					class:border-red-600={!order.overLowBuyLevel || !order.takeProfitLevel}
					onclick={openModal}
					type="button">
					Levels
				</button>
			</div>
		</div>
	</div>
</div>

{#if showLevelsModal}
	<div class="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
		<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 p-6 w-full max-w-sm">
			<h3 class="text-2xl font-bold mb-6 text-center">Cancel levels</h3>

			<div class="space-y-4">
				<div>
					<label class="block mb-2 text-sm text-zinc-400" for="cancel-level">
						{#if order.side === 'long'} Overlow{:else} Overhigh{/if}
					</label>
					<input
						id="cancel-level"
						bind:value={editableLevels.overLowBuyLevel}
						type="number"
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="Price" />
				</div>

				<div>
					<label class="block mb-2 text-sm text-zinc-400" for="take-profit">Take Profit</label>
					<input
						id="take-profit"
						bind:value={editableLevels.takeProfitLevel}
						type="number"
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="Price" />
				</div>
			</div>

			<div class="flex space-x-4 pt-8">
				<button
					class="py-2 px-4 w-full rounded-xl hover:bg-zinc-700 border-2 border-zinc-600 transition-colors"
					onclick={closeModal}>
					Cancel
				</button>
				<button
					class="py-2 px-4 w-full rounded-xl bg-blue-800 hover:bg-blue-700 transition-colors"
					onclick={handleSaveLevels}>
					Save
				</button>
			</div>
		</div>
	</div>
{/if}