import { toast } from '@zerodevx/svelte-toast';

const BASE_OPTIONS = {
	duration: 4000,
	dismissable: true
};

export function showErrorToast(msg, duration = BASE_OPTIONS.duration) {
	toast.push(msg, {
		...BASE_OPTIONS,
		duration,
		theme: {
			'--toastColor': 'white',
			'--toastBackground': 'rgba(220, 38, 38, 0.9)',
			'--toastBarBackground': '#861515'
		}
	});
}

export function showSuccessToast(msg, duration = BASE_OPTIONS.duration) {
	toast.push(msg, {
		...BASE_OPTIONS,
		duration,
		theme: {
			'--toastColor': 'mintcream',
			'--toastBackground': 'rgba(72,187,120,0.9)',
			'--toastBarBackground': '#2F855A'
		}
	});
}
	export function showNormalToast(msg, duration = BASE_OPTIONS.duration) {
	toast.push(msg, {
		...BASE_OPTIONS,
		duration,
		// theme: {
		// 	'--toastColor': 'mintcream',
		// 	'--toastBackground': 'rgba(72,187,120,0.9)',
		// 	'--toastBarBackground': '#2F855A'
		// }
	});
}
