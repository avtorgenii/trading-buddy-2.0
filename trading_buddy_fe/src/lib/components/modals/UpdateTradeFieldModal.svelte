<script>
	import BaseEditDialog from './BaseEditDialog.svelte';
	import { createEventDispatcher } from 'svelte';

	let {
		positionId,
		fieldName,
		initialValue,
		open = $bindable()
	} = $props();

	const dispatch = createEventDispatcher();

	function handleSaved(e) {
		// Forward the saved event to parent
		const { fieldName, value } = e.detail;
		dispatch('saved', { fieldName, value });
	}
</script>

<BaseEditDialog
	{positionId}
	{fieldName}
	{initialValue}
	bind:open
	inputType="textarea"
	rows="2"
	on:saved={handleSaved}
/>