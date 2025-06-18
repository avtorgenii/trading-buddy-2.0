<script>
	import { onMount } from 'svelte';
	import Select from 'svelte-select';
	import TradingViewWidget from '$lib/components/TradingViewWidget.svelte';
	import { API_BASE_URL } from '$lib/config.js';
	import { csrfToken } from '$lib/stores.js';
	import { goto } from '$app/navigation';
	import { showSuccessToast, showErrorToast } from '$lib/toasts.js';


	let items = [];

	let selectedTicker = { value: null, label: null, exchangeFormat: null };
	let screenWidth = 0;
	$: isMobile = screenWidth < 768;

	let accountBalance = 0;
	let riskPercent = 0;

	let leverage = 1;
	let entryPrice = null;
	let triggerLevel = null;
	let stopLoss = null;
	let leverageLimits = { max_long_leverage: 100, max_short_leverage: 100 };

	let takeProfits = [
		{ price: null }
	];

	let moveSLToBEIndex = 0;

	let positionSize = null;
	let requiredMargin = null;
	let potentialLoss = null;
	let potentialProfit = null;
	let riskRewardRatio = null;

	let debounceTimeout;
	let isSubmitting = false;

	let mainAcc = null;

	async function getMainAccount() {
		try {
			const response = await fetch(`${API_BASE_URL}/auth/status/`, {
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error('Could not fetch main account.');
			}

			const data = await response.json();

			let mainAccName;
			if (data.current_account !== null) {
				mainAccName = data.current_account.name;
			} else {
				mainAccName = '';
				throw new Error('Main account is not set');
			}
			return mainAccName


		} catch (error) {
			showErrorToast('Failed to get main account');

			console.log('Failed to get main account', error);
		}
	}
	async function loadAccountDetails() {
		try {
			const response = await fetch(`${API_BASE_URL}/account/details/`, {
				credentials: 'include'
			});
			if (!response.ok) {
				throw new Error('Could not fetch account details.');
			}
			const data = await response.json();

			accountBalance = parseFloat(data.available_margin).toFixed(2);
			riskPercent = parseFloat(data.risk_percent);

		} catch (error) {
			showErrorToast(error.message);
			console.error('Failed to get account details', error);
		}
	}


	async function loadTradableTickers() {
		try {
			const response = await fetch(`${API_BASE_URL}/trading/tools/`, {
				credentials: 'include'
			});


			if (!response.ok) {
				throw new Error('Could not fetch tradable tickers.');
			}

			const apiTools = await response.json();

			console.log(apiTools);

			return apiTools.map(tool => ({
				label: tool.label,
				value: tool.trading_view_format,
				exchangeFormat: tool.exchange_format

			}));

		} catch (error) {
			showErrorToast(error.message);
			console.error(error);
			return [];
		}
	}

	async function fetchLeverageLimits(ticker) {
		if (!ticker || !ticker.exchangeFormat) return;
		try {
			const url = `${API_BASE_URL}/trading/tools/${ticker.exchangeFormat}/leverages`;
			const response = await fetch(url, { credentials: 'include' });
			if (!response.ok) throw new Error('Could not fetch leverage limits.');

			leverageLimits = await response.json();

			leverage = leverageLimits.max_long_leverage;

			console.log('Updated leverage limits:', leverageLimits);
		} catch (error) {
			showErrorToast(error.message);
			leverageLimits = { max_long_leverage: 100, max_short_leverage: 100 };
		}
	}

	$: if (selectedTicker) {
		fetchLeverageLimits(selectedTicker);
	}



	$: isLong = entryPrice && stopLoss ? entryPrice > stopLoss : null;



	function addTakeProfit() {
		takeProfits = [...takeProfits, { price: null }];
	}

	function removeTakeProfit(indexToRemove) {
		takeProfits = takeProfits.filter((_, index) => index !== indexToRemove);

		if (moveSLToBEIndex >= indexToRemove && moveSLToBEIndex > 0) {
			moveSLToBEIndex = moveSLToBEIndex - 1;
		}
	}

	async function processPositionData() {
		if (!mainAcc || !selectedTicker || !entryPrice || !stopLoss || !leverage) {
			return;
		}


		const payload = {
			account_name: mainAcc,
			tool: selectedTicker.exchangeFormat,
			trigger_p: triggerLevel,
			entry_p: entryPrice,
			stop_p: stopLoss,
			take_profits: takeProfits.map(tp => tp.price).filter(p => p > 0),
			move_stop_after: moveSLToBEIndex +1 || 0,
			leverage: leverage,
			volume: positionSize
		};

		try {
			const response = await fetch(`${API_BASE_URL}/trading/positions/process/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include',
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				console.error('API processing error:', await response.json());
				return;
			}

			const results = await response.json();

			requiredMargin = parseFloat(results.margin);
			potentialLoss = parseFloat(results.potential_loss);
			potentialProfit = parseFloat(results.potential_profit);

			if (potentialProfit > 0 && potentialLoss > 0) {
				riskRewardRatio = potentialProfit / potentialLoss;
			} else {
				riskRewardRatio = null;
			}

		} catch (error) {
			console.error('Failed to process position data:', error);
		}
	}

	async function handleOpenTrade() {
		isSubmitting = true;

		if (!mainAcc || !selectedTicker || !entryPrice || !stopLoss || !leverage || !takeProfits[0]?.price) {
			showErrorToast('Please fill all required fields.');
			isSubmitting = false;
			return;
		}

		const payload = {
			account_name: mainAcc,
			tool: selectedTicker.exchangeFormat,
			trigger_p: triggerLevel,
			entry_p: entryPrice,
			stop_p: stopLoss,
			take_profits: takeProfits.map(tp => tp.price).filter(p => p > 0),
			move_stop_after: moveSLToBEIndex +1,
			leverage: leverage,
			volume: positionSize
		};

		try {
			const response = await fetch(`${API_BASE_URL}/trading/positions/place/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': $csrfToken
				},
				credentials: 'include',
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.error || 'Failed to place position.');
			}

			showSuccessToast('Position placed successfully!');


			setTimeout(async () => {
				await goto("/positions");
			}, 1000);
		} catch (error) {
			showErrorToast(error.message);
		} finally {
			isSubmitting = false;
		}
	}

	$: if (entryPrice, stopLoss, leverage, positionSize, takeProfits, selectedTicker, mainAcc) {
		clearTimeout(debounceTimeout);
		debounceTimeout = setTimeout(processPositionData, 500);
	}



	onMount(async () => {
		items = await loadTradableTickers();
		selectedTicker = items.at(0);
		mainAcc = await getMainAccount();
		if (mainAcc) await loadAccountDetails();
		screenWidth = window.innerWidth;
		window.addEventListener('resize', () => {
			screenWidth = window.innerWidth;
		});
	});

</script>


<div class="flex items-center flex-col">
	<div
		class="w-auto md:min-w-2/3 bg-zinc-900 md:px-10 pt-4 pb-12 rounded-2xl text-center flex flex-col justify-between min-h-[60vh] max-w-full md:max-w-lg shadow-xl shadow-white/10">
		<Select --item-hover-bg="#52525b" --list-background="#27272a" bind:value={selectedTicker} containerStyles="
        background-color: #27272a;
        border: 1px solid #374151;
        border-radius: 0.5rem;
        color: #ffffff;a
        width: 100%;
        max-width: 20rem;
        margin: 0 auto;
      "
						{items}
						placeholder="Select Ticker"
		/>


		<div class="bg-zinc-800 rounded-t-2xl flex items-center justify-center p-1 mt-3">
			<div class="w-full h-64 md:h-90 lg:h-96 xl:h-106 ">
				{#key selectedTicker}
					<TradingViewWidget class="w-full h-full" symbol={selectedTicker.value} />
				{/key}
			</div>
		</div>

		<div class="w-full max-w-md mx-auto mt-6 px-4">

			<div class="flex justify-center space-x-6 bg-zinc-800 p-2 rounded-xl mb-6 text-sm">
				<div>
					<span class="text-zinc-400">Balance: </span>
					<span class="font-mono text-white">${accountBalance.toLocaleString('en-US')}</span>
				</div>
				<div>
					<span class="text-zinc-400">Risk per Trade: </span>
					<span class="font-mono text-white">{riskPercent}%</span>
				</div>
			</div>


			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Leverage:</span>
				<input
					bind:value={leverage}
					class="bg-zinc-800   text-center w-24 rounded-xl px-4 py-2  focus:outline-none focus:ring-2 focus:ring-blue-600"
					max="100"
					min="1"
					step="1"
					type="number"
				/>
				<span class="">x</span>

				<div class="flex-1 flex justify-end">
					<p class="uppercase border-r-4 px-2.5 mb-1 text-lg"
						 class:border-r-green-600={isLong}
						 class:border-r-red-600={!isLong}>
						{isLong ? 'Long' : 'Short'}
					</p>
				</div>
			</div>
			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Entry:</span>
				<input
					bind:value={entryPrice}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Limit Entry Price"
					type="number"
				/>
			</div>

			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Trigger:</span>
				<input
					bind:value={triggerLevel}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Trigger Level (Optional)"
					type="number"
				/>
			</div>

			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Stop Loss:</span>
				<input
					bind:value={stopLoss}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Stop Loss"
					type="number"
				/>
			</div>
			<div class="flex items-center space-x-2 mb-4">
				<span class="text-zinc-400 w-24 text-start">Size:</span>
				<input
					bind:value={positionSize}
					class="bg-zinc-800  w-full rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
					placeholder="Position Size (Optional)"
					type="number"
				/>
			</div>

			<p class="text-zinc-400 w-full text-left mb-2">Move SL to BE after:</p>

			{#each takeProfits as tp, index (index)}
				<div class="flex items-center gap-2 mb-4 flex-wrap">

					<input
						type="radio"
						id="tp-be-{index}"
						name="sl_be_after_tp"
						class="form-radio h-4 w-4 bg-zinc-700 border-zinc-600 text-blue-600 focus:ring-blue-500"
						bind:group={moveSLToBEIndex}
						value={index}
					/>
					<label for="tp-be-{index}" class="text-zinc-400 w-16 text-start text-nowrap">TP {index + 1}:</label>

					<div class="flex-1 flex gap-2 min-w-[200px]">
						<input
							type="number"
							bind:value={tp.price}
							placeholder="Price"
							class="bg-zinc-800 flex-1 min-w-0 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm"
						/>
					</div>

					<button
						class="py-1 px-3  cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed "
						on:click={() => removeTakeProfit(index)}
						disabled={takeProfits.length <= 1}
						tabindex="0"
						type="button">
						Remove
					</button>
				</div>
			{/each}
			<button
				class="py-1 px-3  cursor-pointer rounded-xl hover:bg-zinc-800 border-2 border-zinc-600 mb-4 disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={takeProfits.length >= 5}
				on:click={addTakeProfit}
				tabindex="0"
				type="button">
				Add Take Profit
			</button>

			<div class="space-y-2 bg-zinc-800 rounded-xl p-4 mb-4">
				<!--				<div class="flex justify-between">-->
				<!--					<span class="text-zinc-400">Pos. size:</span>-->
				<!--					<span class="text-white">{positionSize ? `$${positionSize.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '-'}</span>-->
				<!--				</div>-->
				<div class="flex justify-between">
					<span class="text-zinc-400">Required margin:</span>
					<span class="text-white">{requiredMargin ? `$${requiredMargin.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Potential loss:</span>
					<span class="text-red-500">{potentialLoss ? `$${potentialLoss.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Potential profit:</span>
					<span class="text-green-500">{potentialProfit ? `$${potentialProfit.toFixed(2)}` : '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-zinc-400">Risk reward ratio:</span>
					<span class="text-white">{riskRewardRatio ? `1 : ${riskRewardRatio.toFixed(0)}` : '-'}</span>
				</div>
			</div>

			<button
				class="mt-5 bg-blue-800 hover:bg-blue-700 py-3 rounded-xl w-full text-lg
            transition-colors duration-200 max-w-xs mx-auto"
				disabled={isSubmitting}
				on:click={handleOpenTrade()}
			>
				Open {isLong ? 'Long' : "Short"}
			</button>
		</div>
	</div>
</div>

<style>
    input[type="number"]::-webkit-inner-spin-button,
    input[type="number"]::-webkit-outer-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    input[type="number"] {
        -moz-appearance: textfield;
    }
</style>