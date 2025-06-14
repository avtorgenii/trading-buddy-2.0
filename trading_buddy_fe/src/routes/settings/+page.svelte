<script>
	import { onMount } from 'svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { showSuccessToast, showErrorToast } from '$lib/toasts.js';
	import { csrfToken } from '$lib/stores.js';

	let accounts = [];
	let isLoading = true;

	let settingsSaveStatus = 'idle';
	let view = 'list';
	let currentlyEditingAccount = null;
	const availableExchanges = ['BingX', 'ByBit'];

	async function loadAccounts() {
		isLoading = true;
		try {
			const response = await fetch(`${API_BASE_URL}/accounts/`, {
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error('Could not fetch accounts.');
			}

			const apiAccounts = await response.json();

			accounts = apiAccounts.map((acc, index) => ({
				id: acc.id,
				exchange: acc.exchange,
				name: acc.name,
				risk: parseFloat(acc.risk_percent),
				isMain: index === 0, //TODO: add proper solution
				apiKey: '********',
				secretKey: '********'
			}));

		} catch (error) {
			showErrorToast(error.message);
		} finally {
			isLoading = false;
		}
	}


	onMount(() => {
		loadAccounts();
	});


	function showAddForm() {
		currentlyEditingAccount = {
			id: null,
			exchange: availableExchanges[0],
			name: '',
			apiKey: '',
			secretKey: '',
			risk: 1,
			isMain: accounts.length === 0
		};
		view = 'form';
	}


	function handleCancel() {
		currentlyEditingAccount = null;
		view = 'list';
	}

	async function saveAccount() {
		if (!currentlyEditingAccount) return;

		const payload = {
			name: currentlyEditingAccount.name,
			exchange: currentlyEditingAccount.exchange,
			risk_percent: currentlyEditingAccount.risk,
			api_key: currentlyEditingAccount.apiKey,
			secret_key: currentlyEditingAccount.secretKey
		};

		try {
			const response = await fetch(`${API_BASE_URL}/accounts/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json',
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include',
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				const errorData = await response.json();
				const errorMessage = errorData.detail || Object.values(errorData)[0]?.[0];
				throw new Error(errorMessage);
			}

			showSuccessToast('Account created successfully!');
			handleCancel();
			await loadAccounts();

		} catch (error) {
			showErrorToast(error.message);
		}
	}

	async function deleteAccount(accountId) {
		const accountToDelete = accounts.find(acc => acc.id === accountId);
		if (!accountToDelete) return;

		const accountName = accountToDelete.name;

		try {
			const response = await fetch(`${API_BASE_URL}/accounts/${accountName}/`, {
				method: 'DELETE',
				credentials: 'include',
				headers : {
					'X-CSRFToken': $csrfToken
				}
			});

			if (!response.ok && response.status !== 204) {
				throw new Error('Failed to delete account.');
			}

			showSuccessToast('Account deleted successfully.');
			await loadAccounts();

		} catch (error) {
			showErrorToast(error.message);
		}
	}

	function setMainAccount(accountIdToSet) {
		// TODO: add api
		accounts = accounts.map(acc => ({
			...acc,
			isMain: acc.id === accountIdToSet
		}));
		showSuccessToast('Main account updated!');
	}

	function handleSaveAllSettings(event) {
		event.preventDefault();
		console.log('Saving settings...');
		showSuccessToast('Settings saved!');
		settingsSaveStatus = 'success';
		setTimeout(() => settingsSaveStatus = 'idle', 3000);
	}

</script>


<div class="page-wrapper flex items-center flex-col">
	<div
		class="form-wrapper bg-zinc-900 px-4 md:px-12 pt-8 pb-12 rounded-2xl flex flex-col min-h-[520px] w-full max-w-2xl shadow-xl shadow-white/10">

		{#if view === 'list'}
			<h2 class="text-3xl font-bold mb-6 text-center">Settings</h2>
			<form class="flex flex-col h-full" on:submit={handleSaveAllSettings}>
				<div class="flex-grow">
					<div class="flex justify-between items-center mb-4">
						<h3 class="text-2xl font-semibold">Accounts</h3>
						<button type="button" on:click={showAddForm}
										class="bg-blue-800 hover:bg-blue-700 text-sm px-4 py-2 rounded-xl transition-colors">
							Add new account
						</button>
					</div>

					<div class="space-y-3 mb-8 min-h-[10rem] relative">
						<!-- ZMIANA: Dodano wskaźnik ładowania -->
						{#if isLoading}
							<div class="absolute inset-0 flex items-center justify-center">
								<div class="w-8 h-8 border-4 border-zinc-600 border-t-blue-500 rounded-full animate-spin"></div>
							</div>
						{:else if accounts.length > 0}
							{#each accounts as account (account.id)}
								<div
									class="bg-zinc-800 p-4 rounded-xl flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
									<div class="flex-1 text-center sm:text-left">
										<p class="font-bold">{account.name}</p>
										<p class="text-sm text-zinc-400">{account.exchange} &bull; Risk: {account.risk}%</p>
									</div>
									<div class="flex items-center justify-center gap-2">
										{#if account.isMain}
											<span class="px-3 py-1 text-xs font-bold text-green-300 bg-green-900/50 rounded-full">Main</span>
										{:else}
											<button type="button" on:click={() => setMainAccount(account.id)}
															class="text-xs px-3 py-1 bg-zinc-700 hover:bg-zinc-600 rounded-full transition-colors">Set
												as Main
											</button>
										{/if}

										<button type="button" on:click={() => deleteAccount(account.id)}
														class="py-1 px-3 text-sm cursor-pointer rounded-xl text-red-400 hover:bg-red-900/50 border-2 border-red-900/80 hover:border-red-800 transition-colors">
											Delete
										</button>
									</div>
								</div>
							{/each}
						{:else}
							<p class="text-zinc-500 text-center py-4">No accounts added yet.</p>
						{/if}
					</div>
				</div>

				<button type="submit"
								class="mt-8 py-3 rounded-xl w-full transition-colors duration-1000 {settingsSaveStatus === 'success' ? 'bg-green-600' : 'bg-blue-800 hover:bg-blue-700'}">
					Save Settings
				</button>
			</form>

		{:else}
			<h2 class="text-3xl font-bold mb-10 text-center">New Account</h2>
			<form class="space-y-5" on:submit|preventDefault={saveAccount}>

				<div>
					<label class="block mb-2 text-left" for="exchange-select">Exchange</label>
					<select id="exchange-select" bind:value={currentlyEditingAccount.exchange}
									class="bg-zinc-800 rounded-xl px-4 py-3 w-full">
						{#each availableExchanges as exchange}
							<option value={exchange}>{exchange}</option>
						{/each}
					</select>
				</div>

				<div>
					<label class="block mb-2 text-left" for="account-name">Name</label>
					<input id="account-name" bind:value={currentlyEditingAccount.name}
								 class="bg-zinc-800 rounded-xl px-4 py-3 w-full" placeholder="e.g. My Main Account" required />
				</div>

				<div>
					<label class="block mb-2 text-left" for="account-risk">Risk per trade (%)</label>
					<input id="account-risk" bind:value={currentlyEditingAccount.risk}
								 class="bg-zinc-800 rounded-xl px-4 py-3 w-full" type="number" min="0.1" max="100" step="0.1"
								 required />
				</div>

				<div>
					<label class="block mb-2 text-left" for="api-key">API Key</label>
					<input id="api-key" bind:value={currentlyEditingAccount.apiKey}
								 class="bg-zinc-800 rounded-xl px-4 py-3 w-full" placeholder="API key" required />
				</div>

				<div>
					<label class="block mb-2 text-left" for="secret-key">Secret Key</label>
					<input id="secret-key" bind:value={currentlyEditingAccount.secretKey}
								 class="bg-zinc-800 rounded-xl px-4 py-3 w-full" placeholder="Secret Key" required type="password" />
				</div>

				<div class="flex space-x-4 pt-6">
					<button type="button" on:click={handleCancel}
									class="bg-zinc-700 hover:bg-zinc-600 py-3 rounded-xl w-full transition-colors">
						Cancel
					</button>
					<button type="submit" class="bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full transition-colors">
						Create Account
					</button>
				</div>
			</form>
		{/if}

	</div>
</div>