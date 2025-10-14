<script>
	import { createEventDispatcher } from 'svelte';
	import { fly } from 'svelte/transition';
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { csrfToken } from '$lib/stores.js';

	let {
		accountId = '',
		accountName = '',
		initialApiKey = '',
		initialSecretKey = '',
		open = $bindable()
	} = $props();

	const dispatch = createEventDispatcher();

	let apiKey = $state(initialApiKey);
	let secretKey = $state(initialSecretKey);
	let isSubmitting = $state(false);
	let apiKeyInput = $state();

	// Reset values and autofocus when dialog opens
	$effect(() => {
		if (open) {
			apiKey = initialApiKey;
			secretKey = initialSecretKey;
			if (apiKeyInput) {
				setTimeout(() => apiKeyInput.focus(), 100);
			}
		}
	});

	function close() {
		open = false;
	}

	async function handleSave(e) {
		e.preventDefault();

		if (!apiKey.trim() || !secretKey.trim()) {
			showErrorToast('Both API key and Secret key are required');
			return;
		}

		if (isSubmitting) return;
		isSubmitting = true;

		try {
			const response = await fetch(`${API_BASE_URL}/accounts/api/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include',
				body: JSON.stringify({
					account_id: accountId,
					api_key: apiKey,
					secret_key: secretKey
				})
			});

			const data = await response.json();

			console.log(data);

			if (!response.ok) {
				throw new Error(data.detail || data.error || data.errors || 'Failed to update API keys');
			}

			showSuccessToast('API keys updated successfully');

			dispatch('saved', {
				accountId,
				apiKey,
				secretKey
			});

			close();
		} catch (err) {
			showErrorToast(err.message);
		} finally {
			isSubmitting = false;
		}
	}

	function handleBackdropClick(e) {
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
		aria-label="Edit API Keys"
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
				<h2 class="text-xl font-semibold text-white mb-4">Edit API Keys</h2>

				{#if accountName}
					<p class="text-sm text-zinc-400 mb-4">
						Account: <span class="text-white font-medium">{accountName}</span>
					</p>
				{/if}

				<!-- API Key Input -->
				<div class="mb-4">
					<label for="apiKey" class="block text-sm font-medium text-zinc-300 mb-2">
						API Key
					</label>
					<input
						bind:this={apiKeyInput}
						id="apiKey"
						type="text"
						bind:value={apiKey}
						placeholder="Enter API key..."
						disabled={isSubmitting}
						class="w-full bg-zinc-800 text-white rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-60"
					/>
				</div>

				<!-- Secret Key Input -->
				<div class="mb-6">
					<label for="secretKey" class="block text-sm font-medium text-zinc-300 mb-2">
						Secret Key
					</label>
					<input
						id="secretKey"
						type="password"
						bind:value={secretKey}
						placeholder="Enter secret key..."
						disabled={isSubmitting}
						class="w-full bg-zinc-800 text-white rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-60"
					/>
				</div>

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