<script>
	import BaseEditDialog from './BaseEditDialog.svelte';
	import { createEventDispatcher } from 'svelte';

	let {
		accountName = '',
		initialValue = '',
		open = $bindable()
	} = $props();

	const dispatch = createEventDispatcher();

	function handleSaved(e) {
		// Forward the saved event to parent
		const { fieldName, value } = e.detail;
		dispatch('saved', { accountName, value });
	}
</script>

<BaseEditDialog
	fieldName="risk_percent"
	{initialValue}
	bind:open
	inputType="input"
	placeholder="Enter risk assessment..."
	title="Edit Risk"
	successMessage="Account risk updated."
	on:saved={handleSaved}
	apiEndpoint={`/accounts/${accountName}/risk-percent/`}
/>