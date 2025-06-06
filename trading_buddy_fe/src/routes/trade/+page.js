/** @type {import('./$types').PageLoad} */
export async function load({ fetch }) {
	// fetch z backendu lub zewnętrznego API:
	// const res = await fetch('/api/tickers');
	// const data = await res.json();

	// dla przykładu: statyczna tablica
	const data = [
		{ value: 'BYBIT:BTCUSDT', label: 'BTCUSD' },
		{ value: 'BYBIT:ETHUSDT', label: 'ETHUSD' },
		{ value: 'BYBIT:SOLUSDT', label: 'SOLUSD' },
		{ value: 'BYBIT:ADAUSDT', label: 'ADAUSD' },
		{ value: 'BYBIT:XRPUSDT', label: 'XRPUSD' },
		{ value: 'BYBIT:DOGEUSDT', label: 'DOGEUSD' },
		{ value: 'BYBIT:BNBUSDT', label: 'BNBUSD' }
	];

	return { allTickers: data };
}
