<!-- src/lib/components/PendingCard.svelte -->
<script>
	import { createEventDispatcher } from 'svelte';

	export let order;

	const dispatch = createEventDispatcher();

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

<div class="flex-none w-full md:px-2bg-zinc-800 rounded-2xl p-0.5 md:bg-transparent md:rounded-none md:p-0">
	<div class="bg-zinc-900 rounded-2xl shadow-xl shadow-white/10 h-full flex flex-col">
		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-3">
			<p class="text-sm text-zinc-400">Type: {order.orderType}</p>
		</div>

		<div class="p-4 flex-grow flex flex-row ">
			<div class="w-1/5 text-start">
				<p class="uppercase border-l-4 px-2.5 mb-1
                  {order.side === 'long' ? 'border-l-green-600' : 'border-l-red-600'}">
					{order.side}
				</p>
				<p class="text-sm text-zinc-400">Qty: {order.quantity}</p>
			</div>

			<div class="w-3/5 flex flex-col justify-between">
				<div class="text-center">
					<p class="font-medium">{getStringAfterColon(order.ticker)}</p>
					<p class="text-sm text-zinc-400">Price: {order.price}$</p>
				</div>
				<div class="mt-3 text-center">
					<p class="text-sm text-zinc-200">
						{order.status}
					</p>
				</div>
			</div>

			<div class="w-1/5 flex flex-col items-end">
				<button
					class="py-1 px-3 cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600"
					on:click={handleCancel}
					tabindex="0"
					type="button">
					Cancel
				</button>
			</div>
		</div>
	</div>
</div>
