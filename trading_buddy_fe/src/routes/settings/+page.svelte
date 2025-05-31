<script>
	let bybitCredentials = { api: '', secret: '' };
	let bingxCredentials = { api: '', secret: '' };
	let riskPerTrade = 0;
	let settingsSaveStatus = 'idle';

	function handleSettingsChange(event) {
		event.preventDefault();


		alert(`handleSettingsChange: `);
		settingsSaveStatus = 'success';
		setTimeout(() => settingsSaveStatus = 'idle', 5000);


	}

</script>
<div class="page-wrapper flex items-center flex-col ">
	<h1 class="text-4xl font-bold mb-16">Trading buddy</h1>
	<div
		class="form-wrapper bg-zinc-900 px-2 md:px-12 pt-8 pb-12 rounded-2xl flex flex-col justify-between min-h-[520px] max-w-xs md:max-w-lg shadow-xl shadow-white/10 ">
		<h2 class="text-3xl font-bold mb-10 text-center">Settings</h2>
		<div>
			<form class="space-y-5 w-auto md:w-96" on:submit={handleSettingsChange}>
				<p class="text-3xl font-semibold">API Keys</p>
				<div class="space-y-2">
					<p>ByBit</p>
					<input
						bind:value={bybitCredentials.api}
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="API key"
						required
						type="text"
					/>
					<input
						bind:value={bybitCredentials.secret}
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="Secret Key"
						required
						type="text"
					/>
				</div>
				<div class="space-y-2">
					<p>BingX</p>
					<input
						bind:value={bingxCredentials.api}
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="API key"
						required
						type="text"
					/>
					<input
						bind:value={bingxCredentials.secret}
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						placeholder="Secret Key"
						required
						type="text"
					/>
				</div>
				<p class="text-3xl font-semibold">Trade Settings</p>
				<div class="space-y-2">
					<p>Risk per trade (%)</p>
					<input
						bind:value={riskPerTrade}
						class="bg-zinc-800 rounded-xl px-4 py-3 w-full"
						inputmode="numeric"
						max="99"
						min="0"
						pattern="[0-9]*"
						placeholder="Percent"
						required
						type="number"

					/>


				</div>
				<button
					class="py-3 rounded-xl w-full transition-colors duration-1000 {settingsSaveStatus === 'success' ? 'bg-green-600' : settingsSaveStatus === 'error' ? 'bg-red-600' : 'bg-blue-800'}"
					type="submit">
					{settingsSaveStatus === 'success' ? 'Settings Saved!' : settingsSaveStatus === 'Error Saving Settings' ? 'bg-red-600' : 'Save'}</button>
			</form>
		</div>
	</div>
</div>


<style>
    input[type="number"]::-webkit-outer-spin-button,
    input[type="number"]::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    input[type="number"] {
        -moz-appearance: textfield;
    }
</style>
