<script>
	// Currently is used only for updating description field of trade, while it is pending or current
	import { API_BASE_URL } from '$lib/config.js';
	import { showErrorToast, showSuccessToast } from '$lib/toasts.js';
	import { csrfToken } from '$lib/stores.js';


	let { positionId, fieldName } = $props();


	async function handleSaveField(value) {
		try {
			const res = await fetch(
				`${API_BASE_URL}/journal/trades/${positionId}/`,

				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': $csrfToken
					},
					credentials: 'include',
					body: JSON.stringify({ fieldName: value })
				}
			);
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `Failed to update position ${fieldName}.`);
			}
			showSuccessToast(`Position ${fieldName} updated.`);
		} catch (err) {
			showErrorToast(err.message);
		}
	}
</script>

<div>
	<h2>Modal</h2>
</div>