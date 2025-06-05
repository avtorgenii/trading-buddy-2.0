<script>
	import '../app.css';
	import { SvelteToast } from '@zerodevx/svelte-toast'

</script>

<main class="min-h-screen bg-zinc-950 flex  justify-center text-gray-100 p-3">
	<div class="w-full md:w-4/5">
		<slot />
	</div>
</main>
<SvelteToast  />
