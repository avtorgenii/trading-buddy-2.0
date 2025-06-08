<script>
	import { createEventDispatcher } from 'svelte';

	export let order;

	const dispatch = createEventDispatcher();

	let showLevelsModal = false;
	let editableLevels = {};

	function openModal() {
		editableLevels = {
			cancelLevel: order.cancelLevel,
			takeProfit: order.takeProfit
		};
		showLevelsModal = true;
	}

	function closeModal() {
		showLevelsModal = false;
	}

	function handleSaveLevels() {
		dispatch('saveLevels', {
			positionId: order.positionId,
			levels: editableLevels
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
		if (parts.length > 1) {
			return parts.slice(1).join(':');
		}
		return inputString;
	}

	function handleCancel() {
		dispatch('cancel', { positionId: order.positionId });
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="flex-none w-full md:px-2 bg-zinc-800 rounded-2xl p-0.5 md:bg-transparent md:rounded-none md:p-0">
	<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 h-full flex flex-col">
		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-3">
			<p class="text-sm text-zinc-400">Type: {order.orderType}</p>
		</div>

		<div class="p-4 flex-grow flex flex-row">
			<div class="w-1/5 text-start">
				<p class="uppercase border-l-4 px-2.5 mb-1 {order.side === 'long' ? 'border-l-green-600' : 'border-l-red-600'}">
					{order.side}
				</p>
				<p class="text-sm text-zinc-400">Qty: {order.quantity}</p>
			</div>

			<div class="w-3/5 flex flex-col justify-between">
				<div class="text-center">
					<p class="font-medium">{getStringAfterColon(order.ticker)}</p>
					<p class="text-sm text-zinc-400">Margin: {order.margin}$</p>
					<p class="text-sm text-zinc-400">Leverage: {order.leverage}x</p>
				</div>
				<div class="mt-3 text-center">
					<p class="text-sm text-zinc-200">{order.status}</p>
				</div>
			</div>

			<div class="w-1/5 flex flex-col items-end justify-between">
				<button
					class="py-1 px-3 cursor-pointer rounded-xl hover:bg-zinc-700 border-2 border-zinc-600 w-20 transition-colors"
					on:click={handleCancel}
					tabindex="0"
					type="button">
					Cancel
				</button>
				<button
					class="py-1 px-3 cursor-pointer rounded-xl hover:bg-zinc-700 border-2  w-20 transition-colors"
					class:border-red-600={!order.cancelLevel || !order.takeProfit }
					class:border-green-600={order.cancelLevel && order.takeProfit }
					on:click={openModal}
					tabindex="0"
					type="button">
					Levels
				</button>
			</div>
		</div>
	</div>
</div>

{#if showLevelsModal}
	<div
		class="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm"
	>
		<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 p-6 w-full max-w-sm">
			<h3 class="text-2xl font-bold mb-6 text-center">Cancel levels</h3>

			<div class="space-y-4">
				<div>
					<label class="block mb-2 text-sm text-zinc-400" for="cancel-level">
						{#if order.side === 'long'}
							Overlow
						{:else}
							Overhigh
						{/if}
					</label>
					<input
						id="cancel-level"
						bind:value={editableLevels.cancelLevel}
						type="number"
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="Price"
					/>
				</div>

				<div>
					<label class="block mb-2 text-sm text-zinc-400" for="take-profit">Take Profit</label>
					<input
						id="take-profit"
						bind:value={editableLevels.takeProfit}
						type="number"
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="Price"
					/>
				</div>
			</div>

			<div class="flex space-x-4 pt-8">
				<button
					class="py-2 px-4 w-full rounded-xl hover:bg-zinc-700 border-2 border-zinc-600 transition-colors"
					on:click={closeModal}
				>
					Cancel
				</button>
				<button
					class="py-2 px-4 w-full rounded-xl bg-blue-800 hover:bg-blue-700 transition-colors"
					on:click={handleSaveLevels}
				>
					Save
				</button>
			</div>
		</div>
	</div>
{/if}