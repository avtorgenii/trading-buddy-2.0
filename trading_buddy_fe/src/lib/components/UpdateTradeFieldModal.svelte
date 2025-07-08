<script>
	// Currently is used only for updating description field of trade, while it is current
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { csrfToken } from '$lib/stores.js';
	import { fly } from 'svelte/transition';
	import { createEventDispatcher } from 'svelte';

	let { positionId, fieldName, initialValue, open = $bindable() } = $props();

	let value = $state(initialValue);
	let isSubmitting = $state(false);
	let textareaEl = $state();

	const dispatch = createEventDispatcher();

	// Autofocus textarea when modal opens
	$effect(() => {
		if (open && textareaEl) {
			// Use setTimeout to ensure the modal is fully rendered
			setTimeout(() => textareaEl.focus(), 100);
		}
	});

	function close() {
		open = false;
	}

	async function handleSave(e) {
		e.preventDefault();
		if (isSubmitting) return;

		isSubmitting = true;
		try {
			const res = await fetch(
				`${API_BASE_URL}/journal/trades/${positionId}/`,
				{
					method: 'PUT',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': $csrfToken
					},
					credentials: 'include',
					body: JSON.stringify({ [fieldName]: value })
				}
			);

			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `Failed to update trade ${fieldName}.`);
			}

			showSuccessToast(`Position ${fieldName} updated.`);

			// Dispatch saved event to parent component
			dispatch('saved', { fieldName, value });
			close();
		} catch (err) {
			showErrorToast(err.message);
		} finally {
			isSubmitting = false;
		}
	}

	function handleBackdropClick(e) {
		// Close modal when clicking on backdrop
		if (e.target === e.currentTarget) {
			close();
		}
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') {
			close();
		}
	}
</script>

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
		onmousedown={handleBackdropClick}
		onkeydown={handleKeydown}
		role="dialog"
		aria-modal="true"
		aria-label={`Edit ${fieldName}`}
		tabindex="-1"
	>
		<!-- Modal Content -->
		<div
			class="bg-zinc-900 w-full max-w-lg mx-4 rounded-2xl shadow-xl shadow-white/10 p-6"
			in:fly={{y: 100, duration: 300, opacity: 0}}
			out:fly={{y: -100, duration: 200, opacity: 0}}
			role="document"
		>
			<form onsubmit={handleSave}>
				<h2 class="text-xl font-semibold text-white mb-4 capitalize">Edit {fieldName}</h2>

				<textarea
					bind:this={textareaEl}
					bind:value={value}
					rows="2"
					class="w-full bg-zinc-800 text-white rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-blue-600 resize-y"
					placeholder={`Enter ${fieldName}...`}
				></textarea>

				<div class="flex justify-end mt-6 space-x-4">
					<button
						type="button"
						class="py-2 px-4 rounded-xl border-2 border-zinc-600 hover:bg-zinc-800 transition-colors"
						onclick={close}
						disabled={isSubmitting}
					>
						Cancel
					</button>

					<button
						type="submit"
						class="py-2 px-6 rounded-xl bg-blue-800 hover:bg-blue-700 transition-colors disabled:opacity-60"
						disabled={isSubmitting}
					>
						{isSubmitting ? 'Saving...' : 'Save'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}