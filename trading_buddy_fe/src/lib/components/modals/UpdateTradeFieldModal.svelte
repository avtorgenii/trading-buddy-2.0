<script>
	import BaseEditDialog from './BaseEditDialog.svelte';
	import { createEventDispatcher } from 'svelte';

	let {
		positionId,
		fieldName,
		initialValue,
		open = $bindable(),
		inputType = 'textarea',
		options = [],
		apiEndpoint = undefined,
	} = $props();

	const dispatch = createEventDispatcher();

	function handleSaved(e) {
		dispatch('saved', e.detail);
	}
</script>

<BaseEditDialog
	{positionId}
	{fieldName}
	{initialValue}
	bind:open
	{inputType}
	{options}
	apiEndpoint={apiEndpoint ?? `/journal/trades/${positionId}/`}
	rows="2"
	on:saved={handleSaved}
/>